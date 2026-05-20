#!/usr/bin/env python3
"""Validate CIPH score integrity hashes in evaluator manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from scripts.html_report import render_html_document
    from scripts.verify_manifest import path_exists
except ModuleNotFoundError:  # pragma: no cover - exercised by direct script execution.
    from html_report import render_html_document
    from verify_manifest import path_exists


EVALUATOR_INTEGRITY_SCHEMA_VERSION = "ciph.evaluator-integrity.v1"
SCORE_PROVENANCE_SCHEMA_VERSION = "ciph.score-provenance.v1"
SUPPORTED_ALGORITHM = "sha256"
SHA256_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass
class ScoreIntegrityValidationResult:
    messages: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_score_integrity(run_dir: Path | str, root: Path | str = ".") -> ScoreIntegrityValidationResult:
    run_path = Path(run_dir)
    root_path = Path(root)
    result = ScoreIntegrityValidationResult()
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


def write_score_integrity_report(
    run_dir: Path | str,
    output_path: Path | str,
    root: Path | str = ".",
) -> Path:
    result = validate_score_integrity(run_dir, root=root)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix == ".html":
        output.write_text(render_score_integrity_report(run_dir, result), encoding="utf-8")
    else:
        output.write_text(render_score_integrity_text(run_dir, result), encoding="utf-8")
    return output


def render_score_integrity_report(run_dir: Path | str, result: ScoreIntegrityValidationResult) -> str:
    status = "PASS" if result.ok else "FAIL"
    return render_html_document(
        title="CIPH Score Integrity",
        heading="CIPH Score Integrity",
        report_kind="score-integrity",
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


def render_score_integrity_text(run_dir: Path | str, result: ScoreIntegrityValidationResult) -> str:
    status = "PASS" if result.ok else "FAIL"
    lines = [f"{status} score integrity {run_dir}"]
    lines.extend(result.messages)
    lines.extend(f"ERROR {error}" for error in result.errors)
    return "\n".join(lines) + "\n"


def _validate_score_file(
    *,
    candidate_id: str,
    phase: str,
    score_path: str,
    root_path: Path,
    result: ScoreIntegrityValidationResult,
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
    if provenance.get("schema_version") != SCORE_PROVENANCE_SCHEMA_VERSION:
        result.errors.append(f"{candidate_id} {phase} score_provenance schema_version must be {SCORE_PROVENANCE_SCHEMA_VERSION}")
    if provenance.get("evaluation_phase") != phase:
        result.errors.append(f"{candidate_id} {phase} score_provenance evaluation_phase mismatch: {provenance.get('evaluation_phase')}")

    evaluator_id = provenance.get("evaluator_id")
    manifest_path = provenance.get("evaluator_manifest_path")
    if not _non_empty_string(evaluator_id):
        result.errors.append(f"{candidate_id} {phase} score_provenance.evaluator_id must be a non-empty string")
        return
    if not _non_empty_string(manifest_path):
        result.errors.append(f"{candidate_id} {phase} score_provenance.evaluator_manifest_path must be a non-empty string")
        return
    if not path_exists(root_path, str(manifest_path)):
        result.errors.append(f"{candidate_id} {phase} evaluator_manifest_path does not exist: {manifest_path}")
        return

    manifest = _load_json_object(root_path / str(manifest_path), result, str(manifest_path))
    if manifest is None:
        return

    errors_before = len(result.errors)
    _validate_evaluator_integrity(str(evaluator_id), phase, score_path, manifest, root_path, result)
    if len(result.errors) == errors_before:
        result.messages.append(f"PASS score integrity {candidate_id} {phase}")


def _validate_evaluator_integrity(
    evaluator_id: str,
    phase: str,
    score_path: str,
    manifest: dict[str, Any],
    root_path: Path,
    result: ScoreIntegrityValidationResult,
) -> None:
    errors_before = len(result.errors)
    if manifest.get("evaluator_id") != evaluator_id:
        result.errors.append(f"evaluator {evaluator_id} evaluator_id mismatch: {manifest.get('evaluator_id')}")
    if manifest.get("evaluation_phase") != phase:
        result.errors.append(f"evaluator {evaluator_id} phase mismatch: {manifest.get('evaluation_phase')}")

    output_paths = _string_list(manifest.get("output_paths"))
    if score_path not in output_paths:
        result.errors.append(f"evaluator {evaluator_id} output_paths must include score path: {score_path}")

    integrity = manifest.get("integrity")
    if not isinstance(integrity, dict):
        result.errors.append(f"evaluator {evaluator_id} integrity must be an object")
        return
    if integrity.get("schema_version") != EVALUATOR_INTEGRITY_SCHEMA_VERSION:
        result.errors.append(f"evaluator {evaluator_id} integrity.schema_version must be {EVALUATOR_INTEGRITY_SCHEMA_VERSION}")
    if integrity.get("algorithm") != SUPPORTED_ALGORITHM:
        result.errors.append(f"evaluator {evaluator_id} integrity.algorithm must be {SUPPORTED_ALGORITHM}")

    _validate_hash_map(evaluator_id, "integrity.input_hashes", integrity.get("input_hashes"), _string_list(manifest.get("input_paths")), root_path, result)
    _validate_hash_map(
        evaluator_id,
        "integrity.evidence_hashes",
        integrity.get("evidence_hashes"),
        _string_list(manifest.get("evidence_paths")),
        root_path,
        result,
    )
    _validate_hash_map(evaluator_id, "integrity.output_hashes", integrity.get("output_hashes"), output_paths, root_path, result)

    if len(result.errors) == errors_before:
        result.messages.append(f"PASS evaluator integrity {evaluator_id}")


def _validate_hash_map(
    evaluator_id: str,
    field_name: str,
    value: Any,
    required_paths: list[str],
    root_path: Path,
    result: ScoreIntegrityValidationResult,
) -> None:
    if not isinstance(value, dict):
        result.errors.append(f"evaluator {evaluator_id} {field_name} must be an object")
        return
    for reference in required_paths:
        digest = value.get(reference)
        if not isinstance(digest, str):
            result.errors.append(f"evaluator {evaluator_id} {field_name} missing: {reference}")
            continue
        if not SHA256_DIGEST_PATTERN.match(digest):
            result.errors.append(f"evaluator {evaluator_id} {field_name} invalid digest for {reference}")
            continue
        if not path_exists(root_path, reference):
            result.errors.append(f"evaluator {evaluator_id} {field_name} path does not exist: {reference}")
            continue
        actual = _sha256_digest(root_path / reference)
        if actual != digest:
            result.errors.append(f"evaluator {evaluator_id} {field_name} mismatch for {reference}")
        else:
            result.messages.append(f"PASS evaluator {evaluator_id} {field_name} {reference}")


def _sha256_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json_object(path: Path, result: ScoreIntegrityValidationResult, label: str) -> dict[str, Any] | None:
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
    parser = argparse.ArgumentParser(description="Validate CIPH score integrity hashes in evaluator manifests.")
    parser.add_argument("run_dir", type=Path, help="Path to run directory")
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root for path references")
    parser.add_argument("--output", type=Path, default=None, help="Write integrity report to this path")
    args = parser.parse_args(argv)

    result = validate_score_integrity(args.run_dir, root=args.root)
    if args.output is not None:
        path = write_score_integrity_report(args.run_dir, args.output, root=args.root)
        print(f"Wrote CIPH score integrity report: {path}")

    print(render_score_integrity_text(args.run_dir, result), end="")
    for error in result.errors:
        print(f"ERROR {error}", file=sys.stderr)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
