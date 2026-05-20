#!/usr/bin/env python3
"""Validate CIPH Meta-Harness candidate records."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from scripts.html_report import render_html_document
    from scripts.lint_trace import lint_trace
    from scripts.verify_manifest import path_exists
except ModuleNotFoundError:  # pragma: no cover - exercised by direct script execution.
    from html_report import render_html_document
    from lint_trace import lint_trace
    from verify_manifest import path_exists


CANDIDATE_SCHEMA_VERSION = "ciph.candidate.v1"
REQUIRED_FILES = [
    "score.json",
    "NOTES.md",
    "patch.diff",
    "TRACE.jsonl",
    "policy/README.md",
    "source/README.md",
    "artifacts/.gitkeep",
    "trace/prompts.jsonl",
    "trace/tools.jsonl",
    "trace/failures.md",
]


@dataclass
class CandidateValidationResult:
    messages: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_candidate(candidate_dir: Path | str, root: Path | str = ".") -> CandidateValidationResult:
    root_path = Path(root)
    candidate_path = Path(candidate_dir)
    result = CandidateValidationResult()

    if not candidate_path.is_dir():
        result.errors.append(f"candidate directory does not exist: {candidate_path}")
        return result

    for required_file in REQUIRED_FILES:
        if (candidate_path / required_file).is_file():
            result.messages.append(f"PASS required file {required_file}")
        else:
            result.errors.append(f"missing required file: {required_file}")

    score = _load_score(candidate_path / "score.json", result)
    if score is None:
        return result

    _validate_score_shape(score, candidate_path, root_path, result)
    _validate_declared_paths(score, root_path, result)
    _validate_candidate_trace(candidate_path / "TRACE.jsonl", root_path, result)
    return result


def render_candidate_validation(candidate_dir: Path | str, result: CandidateValidationResult) -> str:
    status = "PASS" if result.ok else "FAIL"
    return render_html_document(
        title="CIPH Candidate Validation",
        heading="CIPH Candidate Validation",
        report_kind="candidate-validation",
        summary_items=[
            ("Candidate", str(candidate_dir)),
            ("Status", status),
            ("Errors", str(len(result.errors))),
        ],
        sections=[
            {
                "id": "messages",
                "title": "Messages",
                "items": result.messages,
            },
            {
                "id": "errors",
                "title": "Errors",
                "items": result.errors,
            },
        ],
    )


def write_candidate_validation(candidate_dir: Path | str, output_path: Path | str, root: Path | str = ".") -> Path:
    result = validate_candidate(candidate_dir, root=root)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix == ".html":
        output.write_text(render_candidate_validation(candidate_dir, result), encoding="utf-8")
    else:
        output.write_text(render_candidate_validation_text(candidate_dir, result), encoding="utf-8")
    return output


def render_candidate_validation_text(candidate_dir: Path | str, result: CandidateValidationResult) -> str:
    status = "PASS" if result.ok else "FAIL"
    lines = [f"{status} candidate {candidate_dir}"]
    lines.extend(result.messages)
    lines.extend(f"ERROR {error}" for error in result.errors)
    return "\n".join(lines) + "\n"


def _load_score(score_path: Path, result: CandidateValidationResult) -> dict[str, Any] | None:
    if not score_path.is_file():
        return None
    try:
        payload = json.loads(score_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        result.errors.append(f"score.json invalid JSON: {exc.msg}")
        return None
    if not isinstance(payload, dict):
        result.errors.append("score.json must contain a JSON object")
        return None
    return payload


def _validate_score_shape(
    score: dict[str, Any],
    candidate_path: Path,
    root_path: Path,
    result: CandidateValidationResult,
) -> None:
    candidate_id = score.get("candidate_id")
    if candidate_id != candidate_path.name:
        result.errors.append(f"score candidate_id must match directory name: {candidate_path.name}")
    else:
        result.messages.append(f"PASS candidate_id {candidate_path.name}")

    if score.get("schema_version") != CANDIDATE_SCHEMA_VERSION:
        result.errors.append(f"score schema_version must be {CANDIDATE_SCHEMA_VERSION}")

    if not _non_empty_string(score.get("hypothesis")):
        result.errors.append("score hypothesis must be a non-empty string")

    if not isinstance(score.get("lineage"), dict):
        result.errors.append("score lineage must be an object")
    elif not isinstance(score["lineage"].get("parents"), list):
        result.errors.append("score lineage.parents must be a list")
    elif isinstance(score.get("parent_ids"), list) and score["lineage"].get("parents") != score.get("parent_ids"):
        result.errors.append("score lineage.parents must match parent_ids")

    for field_name in ["parent_ids", "changed_modules", "trace_paths", "artifact_paths"]:
        if not isinstance(score.get(field_name), list):
            result.errors.append(f"score {field_name} must be a list")

    for field_name in ["search_scores", "mechanism_metrics"]:
        if not isinstance(score.get(field_name), dict):
            result.errors.append(f"score {field_name} must be an object")

    _validate_ablation(score, result)
    _validate_policy_provenance(score, root_path, result)
    _validate_source_provenance(score, root_path, result)

    candidate_trace = score.get("candidate_trace")
    if not _non_empty_string(candidate_trace):
        result.errors.append("score candidate_trace must be a non-empty string")
    elif not path_exists(root_path, candidate_trace):
        result.errors.append(f"candidate_trace does not exist: {candidate_trace}")


def _validate_ablation(score: dict[str, Any], result: CandidateValidationResult) -> None:
    ablation = score.get("ablation")
    if not isinstance(ablation, dict):
        result.errors.append("score ablation must be an object")
        return
    changed_class = ablation.get("changed_class")
    if changed_class not in {"policy", "source", "config", "evaluator", "baseline"}:
        result.errors.append("score ablation.changed_class must be one of: baseline, config, evaluator, policy, source")
    dimensions = ablation.get("changed_dimensions")
    if not isinstance(dimensions, list) or not all(isinstance(item, str) and item.strip() for item in dimensions):
        result.errors.append("score ablation.changed_dimensions must be a list of non-empty strings")
    elif len({item.split(":", 1)[0] for item in dimensions}) > 1:
        result.errors.append("score ablation.changed_dimensions must describe one changed class")
    else:
        result.messages.append("PASS ablation metadata")


def _validate_policy_provenance(score: dict[str, Any], root_path: Path, result: CandidateValidationResult) -> None:
    snapshots = score.get("policy_provenance")
    if not isinstance(snapshots, list):
        result.errors.append("score policy_provenance must be a list")
        return
    for index, snapshot in enumerate(snapshots):
        if not isinstance(snapshot, dict):
            result.errors.append(f"score policy_provenance[{index}] must be an object")
            continue
        if not _non_empty_string(snapshot.get("module")):
            result.errors.append(f"score policy_provenance[{index}].module must be a non-empty string")
        path = snapshot.get("path")
        digest = snapshot.get("sha256")
        if path is not None and not _non_empty_string(path):
            result.errors.append(f"score policy_provenance[{index}].path must be a non-empty string when present")
        elif isinstance(path, str) and not path_exists(root_path, path):
            result.errors.append(f"score policy_provenance[{index}].path does not exist: {path}")
        if digest is not None and (not isinstance(digest, str) or not digest.startswith("sha256:")):
            result.errors.append(f"score policy_provenance[{index}].sha256 must use sha256:<hex>")
        if not _non_empty_string(snapshot.get("loaded_at")):
            result.errors.append(f"score policy_provenance[{index}].loaded_at must be a non-empty string")


def _validate_source_provenance(score: dict[str, Any], root_path: Path, result: CandidateValidationResult) -> None:
    snapshots = score.get("source_provenance")
    if not isinstance(snapshots, list):
        result.errors.append("score source_provenance must be a list")
        return

    existing_snapshots = 0
    for index, snapshot in enumerate(snapshots):
        if not isinstance(snapshot, dict):
            result.errors.append(f"score source_provenance[{index}] must be an object")
            continue
        path = snapshot.get("path")
        if not _non_empty_string(path):
            result.errors.append(f"score source_provenance[{index}].path must be a non-empty string")
        exists = snapshot.get("exists")
        if not isinstance(exists, bool):
            result.errors.append(f"score source_provenance[{index}].exists must be a boolean")
        elif exists is True and isinstance(path, str) and path_exists(root_path, path):
            existing_snapshots += 1
        elif exists is True and isinstance(path, str):
            result.errors.append(f"score source_provenance[{index}].path does not exist: {path}")
        digest = snapshot.get("sha256")
        if digest is not None and (not isinstance(digest, str) or not digest.startswith("sha256:")):
            result.errors.append(f"score source_provenance[{index}].sha256 must use sha256:<hex>")
        if not _non_empty_string(snapshot.get("loaded_at")):
            result.errors.append(f"score source_provenance[{index}].loaded_at must be a non-empty string")

    if _score_changed_class(score) == "source" and existing_snapshots == 0:
        result.errors.append("score source_provenance must include at least one existing source snapshot for source ablations")
    else:
        result.messages.append("PASS source provenance metadata")


def _validate_declared_paths(score: dict[str, Any], root_path: Path, result: CandidateValidationResult) -> None:
    for trace_path in _string_list(score.get("trace_paths")):
        if path_exists(root_path, trace_path):
            result.messages.append(f"PASS trace path {trace_path}")
        else:
            result.errors.append(f"declared trace path does not exist: {trace_path}")

    for artifact_path in _string_list(score.get("artifact_paths")):
        if path_exists(root_path, artifact_path):
            result.messages.append(f"PASS artifact path {artifact_path}")
        else:
            result.errors.append(f"declared artifact path does not exist: {artifact_path}")


def _validate_candidate_trace(trace_path: Path, root_path: Path, result: CandidateValidationResult) -> None:
    trace_result = lint_trace(trace_path, root=root_path)
    if trace_result.ok:
        result.messages.append(f"PASS candidate trace {trace_path}")
        return
    for error in trace_result.errors:
        result.errors.append(f"candidate trace {error}")


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _score_changed_class(score: dict[str, Any]) -> str | None:
    ablation = score.get("ablation")
    if not isinstance(ablation, dict):
        return None
    changed_class = ablation.get("changed_class")
    return changed_class if isinstance(changed_class, str) else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a CIPH candidate record.")
    parser.add_argument("candidate_dir", type=Path, help="Path to a candidate directory")
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root for candidate path references")
    parser.add_argument("--output", type=Path, default=None, help="Write validation report to this path")
    args = parser.parse_args(argv)

    result = validate_candidate(args.candidate_dir, root=args.root)
    if args.output is not None:
        path = write_candidate_validation(args.candidate_dir, args.output, root=args.root)
        print(f"Wrote CIPH candidate validation: {path}")

    print(render_candidate_validation_text(args.candidate_dir, result), end="")
    for error in result.errors:
        print(f"ERROR {error}", file=sys.stderr)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
