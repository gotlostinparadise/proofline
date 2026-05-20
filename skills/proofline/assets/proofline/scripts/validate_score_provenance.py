#!/usr/bin/env python3
"""Validate CIPH score provenance and evaluator manifests."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from scripts.html_report import render_html_document
    from scripts.validate_evaluation import OBJECTIVE_METRICS
    from scripts.verify_manifest import path_exists
except ModuleNotFoundError:  # pragma: no cover - exercised by direct script execution.
    from html_report import render_html_document
    from validate_evaluation import OBJECTIVE_METRICS
    from verify_manifest import path_exists


EVALUATOR_MANIFEST_SCHEMA_VERSION = "ciph.evaluator-manifest.v1"
SCORE_PROVENANCE_SCHEMA_VERSION = "ciph.score-provenance.v1"


@dataclass
class ScoreProvenanceValidationResult:
    messages: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_score_provenance(run_dir: Path | str, root: Path | str = ".") -> ScoreProvenanceValidationResult:
    run_path = Path(run_dir)
    root_path = Path(root)
    result = ScoreProvenanceValidationResult()
    evaluation = _load_json_object(run_path / "EVALUATION.json", result, "EVALUATION.json")
    if evaluation is None:
        return result

    candidates = evaluation.get("candidates")
    if not isinstance(candidates, list):
        result.errors.append("EVALUATION.json candidates must be a list")
        return result

    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        candidate_id = candidate.get("candidate_id")
        if not _non_empty_string(candidate_id):
            continue
        score_path = candidate.get("score_path")
        if _non_empty_string(score_path):
            _validate_score_file(
                candidate_id=str(candidate_id),
                phase="search",
                score_path=str(score_path),
                root_path=root_path,
                result=result,
            )
        holdout_score_path = candidate.get("holdout_score_path")
        if _non_empty_string(holdout_score_path):
            _validate_score_file(
                candidate_id=str(candidate_id),
                phase="holdout",
                score_path=str(holdout_score_path),
                root_path=root_path,
                result=result,
            )
    return result


def write_score_provenance_report(
    run_dir: Path | str,
    output_path: Path | str,
    root: Path | str = ".",
) -> Path:
    result = validate_score_provenance(run_dir, root=root)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix == ".html":
        output.write_text(render_score_provenance_report(run_dir, result), encoding="utf-8")
    else:
        output.write_text(render_score_provenance_text(run_dir, result), encoding="utf-8")
    return output


def render_score_provenance_report(run_dir: Path | str, result: ScoreProvenanceValidationResult) -> str:
    status = "PASS" if result.ok else "FAIL"
    return render_html_document(
        title="CIPH Score Provenance",
        heading="CIPH Score Provenance",
        report_kind="score-provenance",
        summary_items=[
            ("Run", str(run_dir)),
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


def render_score_provenance_text(run_dir: Path | str, result: ScoreProvenanceValidationResult) -> str:
    status = "PASS" if result.ok else "FAIL"
    lines = [f"{status} score provenance {run_dir}"]
    lines.extend(result.messages)
    lines.extend(f"ERROR {error}" for error in result.errors)
    return "\n".join(lines) + "\n"


def _validate_score_file(
    *,
    candidate_id: str,
    phase: str,
    score_path: str,
    root_path: Path,
    result: ScoreProvenanceValidationResult,
) -> None:
    if not path_exists(root_path, score_path):
        result.errors.append(f"{candidate_id} {phase} score path does not exist: {score_path}")
        return
    score = _load_json_object(root_path / score_path, result, score_path)
    if score is None:
        return
    provenance = score.get("score_provenance")
    if not isinstance(provenance, dict):
        result.errors.append(f"{candidate_id} {phase} score_provenance must be an object")
        return

    provenance_errors_before = len(result.errors)
    _validate_provenance_shape(candidate_id, phase, provenance, root_path, result)
    manifest_path = provenance.get("evaluator_manifest_path")
    if not _non_empty_string(manifest_path) or not path_exists(root_path, str(manifest_path)):
        if _non_empty_string(manifest_path):
            result.errors.append(f"{candidate_id} {phase} evaluator_manifest_path does not exist: {manifest_path}")
        return

    manifest = _load_json_object(root_path / str(manifest_path), result, str(manifest_path))
    if manifest is None:
        return
    _validate_evaluator_manifest(candidate_id, phase, score_path, provenance, manifest, root_path, result)

    if len(result.errors) == provenance_errors_before:
        result.messages.append(f"PASS score provenance {candidate_id} {phase}")


def _validate_provenance_shape(
    candidate_id: str,
    phase: str,
    provenance: dict[str, Any],
    root_path: Path,
    result: ScoreProvenanceValidationResult,
) -> None:
    if provenance.get("schema_version") != SCORE_PROVENANCE_SCHEMA_VERSION:
        result.errors.append(f"{candidate_id} {phase} score_provenance schema_version must be {SCORE_PROVENANCE_SCHEMA_VERSION}")
    if not _non_empty_string(provenance.get("evaluator_id")):
        result.errors.append(f"{candidate_id} {phase} score_provenance.evaluator_id must be a non-empty string")
    if not _non_empty_string(provenance.get("evaluator_manifest_path")):
        result.errors.append(f"{candidate_id} {phase} score_provenance.evaluator_manifest_path must be a non-empty string")
    if provenance.get("evaluation_phase") != phase:
        result.errors.append(f"{candidate_id} {phase} score_provenance evaluation_phase mismatch: {provenance.get('evaluation_phase')}")
    if not _non_empty_string(provenance.get("produced_at")):
        result.errors.append(f"{candidate_id} {phase} score_provenance.produced_at must be a non-empty string")
    _validate_path_list(candidate_id, phase, "score_provenance.input_paths", provenance.get("input_paths"), root_path, result)
    _validate_path_list(candidate_id, phase, "score_provenance.evidence_paths", provenance.get("evidence_paths"), root_path, result)


def _validate_evaluator_manifest(
    candidate_id: str,
    phase: str,
    score_path: str,
    provenance: dict[str, Any],
    manifest: dict[str, Any],
    root_path: Path,
    result: ScoreProvenanceValidationResult,
) -> None:
    evaluator_id = provenance.get("evaluator_id")
    if manifest.get("schema_version") != EVALUATOR_MANIFEST_SCHEMA_VERSION:
        result.errors.append(f"evaluator {evaluator_id} schema_version must be {EVALUATOR_MANIFEST_SCHEMA_VERSION}")
    if manifest.get("evaluator_id") != evaluator_id:
        result.errors.append(f"{candidate_id} {phase} evaluator_id mismatch: {manifest.get('evaluator_id')}")
    manifest_phase = manifest.get("evaluation_phase")
    if manifest_phase != phase:
        result.errors.append(f"{candidate_id} {phase} evaluator phase mismatch: {manifest_phase}")
    if not _non_empty_string(manifest.get("command")):
        result.errors.append(f"evaluator {evaluator_id} command must be a non-empty string")

    _validate_path_list("evaluator", str(evaluator_id), "input path", manifest.get("input_paths"), root_path, result)
    _validate_path_list("evaluator", str(evaluator_id), "evidence path", manifest.get("evidence_paths"), root_path, result)

    output_paths = _string_list(manifest.get("output_paths"))
    if score_path not in output_paths:
        result.errors.append(f"evaluator {evaluator_id} output_paths must include score path: {score_path}")
    for output_path in output_paths:
        if path_exists(root_path, output_path):
            result.messages.append(f"PASS evaluator {evaluator_id} output path {output_path}")
        else:
            result.errors.append(f"evaluator {evaluator_id} output path does not exist: {output_path}")

    metric_keys = _string_list(manifest.get("metric_keys"))
    missing_metrics = [metric for metric in OBJECTIVE_METRICS if metric not in metric_keys]
    if missing_metrics:
        result.errors.append(f"evaluator {evaluator_id} metric_keys missing: {', '.join(missing_metrics)}")

    if not any(error.startswith(f"evaluator {evaluator_id}") or error.startswith(f"{candidate_id} {phase}") for error in result.errors):
        result.messages.append(f"PASS evaluator manifest {evaluator_id}")


def _validate_path_list(
    subject: str,
    context: str,
    field_name: str,
    value: Any,
    root_path: Path,
    result: ScoreProvenanceValidationResult,
) -> None:
    paths = _string_list(value)
    if not paths:
        result.errors.append(f"{subject} {context} {field_name} must contain at least one path")
        return
    for path in paths:
        if path_exists(root_path, path):
            result.messages.append(f"PASS {subject} {context} {field_name} {path}")
        else:
            result.errors.append(f"{subject} {context} {field_name} does not exist: {path}")


def _load_json_object(path: Path, result: ScoreProvenanceValidationResult, label: str) -> dict[str, Any] | None:
    if not path.is_file():
        result.errors.append(f"{label} does not exist")
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        result.errors.append(f"{label} invalid JSON: {exc.msg}")
        return None
    if not isinstance(payload, dict):
        result.errors.append(f"{label} must contain a JSON object")
        return None
    return payload


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate CIPH score provenance and evaluator manifests.")
    parser.add_argument("run_dir", type=Path, help="Path to run directory")
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root for path references")
    parser.add_argument("--output", type=Path, default=None, help="Write provenance report to this path")
    args = parser.parse_args(argv)

    result = validate_score_provenance(args.run_dir, root=args.root)
    if args.output is not None:
        path = write_score_provenance_report(args.run_dir, args.output, root=args.root)
        print(f"Wrote CIPH score provenance report: {path}")

    print(render_score_provenance_text(args.run_dir, result), end="")
    for error in result.errors:
        print(f"ERROR {error}", file=sys.stderr)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
