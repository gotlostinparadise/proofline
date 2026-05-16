#!/usr/bin/env python3
"""Create a CIPH candidate record with trace and score scaffolding."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
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
    force: bool = False,
) -> CandidateResult:
    validate_candidate_id(candidate_id)
    root_path = Path(root)
    manifest = load_manifest(Path(manifest_path))
    task_id = manifest.get("task_id")
    if not isinstance(task_id, str) or not task_id.strip():
        raise ValueError("Parent manifest must include a non-empty task_id")

    candidate_dir = root_path / "runs" / task_id / "candidates" / candidate_id
    if candidate_dir.exists() and not force:
        raise FileExistsError(f"Candidate already exists: runs/{task_id}/candidates/{candidate_id}")

    trace_dir = candidate_dir / "trace"
    trace_dir.mkdir(parents=True, exist_ok=True)
    (candidate_dir / "patch.diff").write_text("", encoding="utf-8")
    (candidate_dir / "NOTES.md").write_text(_render_notes(candidate_id), encoding="utf-8")
    (trace_dir / "prompts.jsonl").write_text("", encoding="utf-8")
    (trace_dir / "tools.jsonl").write_text("", encoding="utf-8")
    (trace_dir / "failures.md").write_text("# Candidate Failures\n\n- None recorded.\n", encoding="utf-8")

    score_path = candidate_dir / "score.json"
    score_path.write_text(
        json.dumps(
            {
                "candidate_id": candidate_id,
                "parent_ids": parent_ids or [],
                "changed_modules": changed_modules or [],
                "search_scores": {
                    "task_success": None,
                    "audit_completeness": None,
                    "cost_tokens": None,
                    "wall_minutes": None,
                    "defect_escape_rate": None,
                },
                "trace_paths": [
                    f"runs/{task_id}/candidates/{candidate_id}/trace/prompts.jsonl",
                    f"runs/{task_id}/candidates/{candidate_id}/trace/tools.jsonl",
                    f"runs/{task_id}/candidates/{candidate_id}/trace/failures.md",
                ],
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a CIPH candidate record.")
    parser.add_argument("manifest", type=Path, help="Path to parent MANIFEST.json")
    parser.add_argument("candidate_id", help="Candidate id using letters, numbers, dots, underscores, or hyphens")
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root")
    parser.add_argument("--changed-module", action="append", default=[], help="Changed module name; repeatable")
    parser.add_argument("--parent", action="append", default=[], help="Parent candidate id; repeatable")
    parser.add_argument("--force", action="store_true", help="Overwrite generated candidate files")
    args = parser.parse_args(argv)

    try:
        result = initialize_candidate(
            args.manifest,
            args.candidate_id,
            root=args.root,
            changed_modules=args.changed_module,
            parent_ids=args.parent,
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
