#!/usr/bin/env python3
"""Create a CIPH candidate record with trace and score scaffolding."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

try:
    from scripts.verify_manifest import load_manifest
except ModuleNotFoundError:  # pragma: no cover - exercised by direct script execution.
    from verify_manifest import load_manifest


CANDIDATE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


@dataclass(frozen=True)
class CandidateResult:
    parent_task_id: str
    candidate_id: str
    candidate_dir: Path
    score_path: Path


def initialize_candidate(
    manifest_path: Path | str,
    candidate_id: str,
    root: Path | str = ".",
    changed_modules: list[str] | None = None,
    parent_ids: list[str] | None = None,
    change_class: str = "policy",
    source_paths: list[str] | None = None,
    force: bool = False,
) -> CandidateResult:
    validate_candidate_id(candidate_id)
    root_path = Path(root)
    manifest_path = Path(manifest_path)
    if not manifest_path.is_absolute():
        manifest_path = root_path / manifest_path
    manifest = load_manifest(manifest_path)
    task_id = manifest.get("task_id")
    if not isinstance(task_id, str) or not task_id.strip():
        raise ValueError("Parent manifest must include a non-empty task_id")

    run_dir = manifest_path.parent
    candidate_dir = run_dir / "candidates" / candidate_id
    if candidate_dir.exists() and not force:
        raise FileExistsError(f"Candidate already exists: {_display_path(candidate_dir, root_path)}")

    policy_dir = candidate_dir / "policy"
    source_dir = candidate_dir / "source"
    artifacts_dir = candidate_dir / "artifacts"
    trace_dir = candidate_dir / "trace"
    trace_dir.mkdir(parents=True, exist_ok=True)
    policy_dir.mkdir(parents=True, exist_ok=True)
    source_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (candidate_dir / "patch.diff").write_text("", encoding="utf-8")
    (candidate_dir / "NOTES.md").write_text(_render_notes(candidate_id), encoding="utf-8")
    (candidate_dir / "TRACE.jsonl").write_text("", encoding="utf-8")
    (policy_dir / "README.md").write_text(_render_policy_readme(candidate_id), encoding="utf-8")
    (source_dir / "README.md").write_text(_render_source_readme(candidate_id), encoding="utf-8")
    (artifacts_dir / ".gitkeep").write_text("", encoding="utf-8")
    (trace_dir / "prompts.jsonl").write_text("", encoding="utf-8")
    (trace_dir / "tools.jsonl").write_text("", encoding="utf-8")
    (trace_dir / "failures.md").write_text("# Candidate Failures\n\n- None recorded.\n", encoding="utf-8")

    display_root = _display_path(candidate_dir, root_path)
    source_snapshot_paths = source_paths or []
    if change_class == "source" and not source_snapshot_paths:
        source_snapshot_paths = [f"{display_root}/source/README.md"]
    score_path = candidate_dir / "score.json"
    score_path.write_text(
        json.dumps(
            {
                "schema_version": "ciph.candidate.v1",
                "candidate_id": candidate_id,
                "hypothesis": "State what this candidate is testing.",
                "parent_ids": parent_ids or [],
                "lineage": {
                    "parents": parent_ids or [],
                    "generation": 0,
                },
                "changed_modules": changed_modules or [],
                "ablation": {
                    "changed_class": change_class,
                    "changed_dimensions": _changed_dimensions(change_class, changed_modules or []),
                },
                "policy_provenance": _policy_provenance(root_path, changed_modules or []),
                "source_provenance": _source_provenance(root_path, source_snapshot_paths),
                "search_scores": {
                    "task_success": None,
                    "audit_completeness": None,
                    "cost_tokens": None,
                    "wall_minutes": None,
                    "defect_escape_rate": None,
                },
                "candidate_trace": f"{display_root}/TRACE.jsonl",
                "trace_paths": [
                    f"{display_root}/TRACE.jsonl",
                    f"{display_root}/trace/prompts.jsonl",
                    f"{display_root}/trace/tools.jsonl",
                    f"{display_root}/trace/failures.md",
                ],
                "artifact_paths": [
                    f"{display_root}/policy/README.md",
                    f"{display_root}/source/README.md",
                    f"{display_root}/artifacts/.gitkeep",
                    f"{display_root}/patch.diff",
                    f"{display_root}/NOTES.md",
                ],
                "mechanism_metrics": {},
                "pareto_status": "unscored",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return CandidateResult(task_id, candidate_id, candidate_dir, score_path)


def validate_candidate_id(candidate_id: str) -> None:
    if not CANDIDATE_ID_PATTERN.match(candidate_id):
        raise ValueError(
            "Candidate id must start with an alphanumeric character and contain only letters, "
            "numbers, dots, underscores, or hyphens."
        )


def _render_notes(candidate_id: str) -> str:
    return f"""# CIPH Candidate: {candidate_id}

## Hypothesis

State what this candidate is testing.

## Changes

- None yet.

## Evidence

- None yet.

## Result

Unscored.
"""


def _render_policy_readme(candidate_id: str) -> str:
    return f"""# Candidate Policy Snapshot: {candidate_id}

Copy or describe changed policy modules here. Keep one candidate focused on one hypothesis or ablation.
"""


def _render_source_readme(candidate_id: str) -> str:
    return f"""# Candidate Source Snapshot: {candidate_id}

Record source files, prompt variants, config fragments, or patch references that define this candidate.
"""


def _policy_provenance(root: Path, changed_modules: list[str]) -> list[dict[str, str | None]]:
    loaded_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    snapshots: list[dict[str, str | None]] = []
    for module in changed_modules:
        candidates = [
            root / module,
            root / "harness" / "policies" / f"{module}.md",
            root / "harness" / "policies" / module,
        ]
        policy_path = next((path for path in candidates if path.is_file()), None)
        snapshots.append(
            {
                "module": module,
                "path": _display_path(policy_path, root) if policy_path else None,
                "sha256": _sha256(policy_path) if policy_path else None,
                "loaded_at": loaded_at,
            }
        )
    return snapshots


def _source_provenance(root: Path, source_paths: list[str]) -> list[dict[str, str | bool | None]]:
    loaded_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    snapshots: list[dict[str, str | bool | None]] = []
    for source_path in source_paths:
        path = Path(source_path)
        resolved = path if path.is_absolute() else root / path
        exists = resolved.is_file()
        snapshots.append(
            {
                "path": _display_path(resolved, root),
                "sha256": _sha256(resolved) if exists else None,
                "loaded_at": loaded_at,
                "exists": exists,
            }
        )
    return snapshots


def _changed_dimensions(change_class: str, changed_modules: list[str]) -> list[str]:
    return [f"{change_class}:{module}" for module in changed_modules] or [change_class]


def _sha256(path: Path | None) -> str | None:
    if path is None:
        return None
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _display_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a CIPH candidate record.")
    parser.add_argument("manifest", type=Path, help="Path to parent MANIFEST.json")
    parser.add_argument("candidate_id", help="Candidate id using letters, numbers, dots, underscores, or hyphens")
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root")
    parser.add_argument("--changed-module", action="append", default=[], help="Changed module name; repeatable")
    parser.add_argument("--parent", action="append", default=[], help="Parent candidate id; repeatable")
    parser.add_argument("--source-path", action="append", default=[], help="Source snapshot path; repeatable")
    parser.add_argument(
        "--change-class",
        choices=["policy", "source", "config", "evaluator", "baseline"],
        default="policy",
        help="Single ablation class this candidate changes",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite generated candidate files")
    args = parser.parse_args(argv)

    try:
        result = initialize_candidate(
            args.manifest,
            args.candidate_id,
            root=args.root,
            changed_modules=args.changed_module,
            parent_ids=args.parent,
            change_class=args.change_class,
            source_paths=args.source_path,
            force=args.force,
        )
    except (FileExistsError, ValueError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}")
        return 1

    display_path = Path("runs") / result.parent_task_id / "candidates" / result.candidate_id
    print(f"Created CIPH candidate: {display_path}")
    print(f"- Score: {result.score_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
