#!/usr/bin/env python3
"""Validate CIPH evaluator replay readiness metadata."""

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


EVALUATOR_REPLAY_SCHEMA_VERSION = "ciph.evaluator-replay.v1"
SCORE_PROVENANCE_SCHEMA_VERSION = "ciph.score-provenance.v1"
SUPPORTED_REPLAY_MODE = "metadata-only"
SUPPORTED_EFFECT_POLICY = "local-only"
SHA256_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass
class EvaluatorReplayValidationResult:
    messages: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_evaluator_replay(run_dir: Path | str, root: Path | str = ".") -> EvaluatorReplayValidationResult:
    run_path = Path(run_dir)
    root_path = Path(root)
    result = EvaluatorReplayValidationResult()
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
            _validate_score_replay(
                candidate_id=str(candidate_id),
                phase="search",
                score_path=str(score_path),
                root_path=root_path,
                result=result,
            )
        holdout_score_path = candidate.get("holdout_score_path")
        if _non_empty_string(holdout_score_path):
            _validate_score_replay(
                candidate_id=str(candidate_id),
                phase="holdout",
                score_path=str(holdout_score_path),
                root_path=root_path,
                result=result,
            )
    return result


def write_evaluator_replay_report(
    run_dir: Path | str,
    output_path: Path | str,
    root: Path | str = ".",
) -> Path:
    result = validate_evaluator_replay(run_dir, root=root)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix == ".html":
        output.write_text(render_evaluator_replay_report(run_dir, result), encoding="utf-8")
    else:
        output.write_text(render_evaluator_replay_text(run_dir, result), encoding="utf-8")
    return output


def render_evaluator_replay_report(run_dir: Path | str, result: EvaluatorReplayValidationResult) -> str:
    status = "PASS" if result.ok else "FAIL"
    return render_html_document(
        title="CIPH Evaluator Replay",
        heading="CIPH Evaluator Replay",
        report_kind="evaluator-replay",
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


def render_evaluator_replay_text(run_dir: Path | str, result: EvaluatorReplayValidationResult) -> str:
    status = "PASS" if result.ok else "FAIL"
    lines = [f"{status} evaluator replay {run_dir}"]
    lines.extend(result.messages)
    lines.extend(f"ERROR {error}" for error in result.errors)
    return "\n".join(lines) + "\n"


def _validate_score_replay(
    *,
    candidate_id: str,
    phase: str,
    score_path: str,
    root_path: Path,
    result: EvaluatorReplayValidationResult,
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
    _validate_evaluator_replay(str(evaluator_id), phase, score_path, manifest, root_path, result)
    if len(result.errors) == errors_before:
        result.messages.append(f"PASS score replay {candidate_id} {phase}")


def _validate_evaluator_replay(
    evaluator_id: str,
    phase: str,
    score_path: str,
    manifest: dict[str, Any],
    root_path: Path,
    result: EvaluatorReplayValidationResult,
) -> None:
    errors_before = len(result.errors)
    if manifest.get("evaluator_id") != evaluator_id:
        result.errors.append(f"evaluator {evaluator_id} evaluator_id mismatch: {manifest.get('evaluator_id')}")
    if manifest.get("evaluation_phase") != phase:
        result.errors.append(f"evaluator {evaluator_id} phase mismatch: {manifest.get('evaluation_phase')}")

    output_paths = _string_list(manifest.get("output_paths"))
    if score_path not in output_paths:
        result.errors.append(f"evaluator {evaluator_id} output_paths must include score path: {score_path}")

    replay = manifest.get("replay")
    if not isinstance(replay, dict):
        result.errors.append(f"evaluator {evaluator_id} replay must be an object")
        return
    if replay.get("schema_version") != EVALUATOR_REPLAY_SCHEMA_VERSION:
        result.errors.append(f"evaluator {evaluator_id} replay.schema_version must be {EVALUATOR_REPLAY_SCHEMA_VERSION}")
    if replay.get("mode") != SUPPORTED_REPLAY_MODE:
        result.errors.append(f"evaluator {evaluator_id} replay.mode must be {SUPPORTED_REPLAY_MODE}")
    if replay.get("external_effect_policy") != SUPPORTED_EFFECT_POLICY:
        result.errors.append(f"evaluator {evaluator_id} replay.external_effect_policy must be {SUPPORTED_EFFECT_POLICY}")

    _validate_working_directory(evaluator_id, replay.get("working_directory"), root_path, result)
    _validate_command_metadata(evaluator_id, replay.get("command_metadata"), result)
    _validate_env_allowlist(evaluator_id, replay.get("env_allowlist"), result)
    _validate_expected_output_hashes(
        evaluator_id=evaluator_id,
        expected_hashes=replay.get("expected_output_hashes"),
        output_paths=output_paths,
        integrity=manifest.get("integrity"),
        root_path=root_path,
        result=result,
    )

    if len(result.errors) == errors_before:
        result.messages.append(f"PASS evaluator replay {evaluator_id}")


def _validate_working_directory(
    evaluator_id: str,
    value: Any,
    root_path: Path,
    result: EvaluatorReplayValidationResult,
) -> None:
    if not _non_empty_string(value):
        result.errors.append(f"evaluator {evaluator_id} replay.working_directory must be a non-empty string")
        return
    if not _is_safe_local_reference(root_path, str(value)):
        result.errors.append(f"evaluator {evaluator_id} replay.working_directory must be a local path under root: {value}")
        return
    if not (root_path / str(value)).is_dir():
        result.errors.append(f"evaluator {evaluator_id} replay.working_directory does not exist: {value}")


def _validate_command_metadata(evaluator_id: str, value: Any, result: EvaluatorReplayValidationResult) -> None:
    if not isinstance(value, dict):
        result.errors.append(f"evaluator {evaluator_id} replay.command_metadata must be an object")
        return
    if value.get("shell") is not False:
        result.errors.append(f"evaluator {evaluator_id} replay.command_metadata.shell must be false")
    argv = value.get("argv")
    if not _list_of_non_empty_strings(argv):
        result.errors.append(f"evaluator {evaluator_id} replay.command_metadata.argv must contain at least one non-empty string")


def _validate_env_allowlist(evaluator_id: str, value: Any, result: EvaluatorReplayValidationResult) -> None:
    if not isinstance(value, list):
        result.errors.append(f"evaluator {evaluator_id} replay.env_allowlist must contain unique non-empty strings")
        return
    names = [item for item in value if isinstance(item, str) and item.strip() and "=" not in item]
    if len(names) != len(value) or len(set(names)) != len(names):
        result.errors.append(f"evaluator {evaluator_id} replay.env_allowlist must contain unique non-empty strings")


def _validate_expected_output_hashes(
    *,
    evaluator_id: str,
    expected_hashes: Any,
    output_paths: list[str],
    integrity: Any,
    root_path: Path,
    result: EvaluatorReplayValidationResult,
) -> None:
    if not isinstance(expected_hashes, dict):
        result.errors.append(f"evaluator {evaluator_id} replay.expected_output_hashes must be an object")
        return
    integrity_hashes = integrity.get("output_hashes") if isinstance(integrity, dict) else None
    for output_path in output_paths:
        digest = expected_hashes.get(output_path)
        if not isinstance(digest, str):
            result.errors.append(f"evaluator {evaluator_id} replay.expected_output_hashes missing: {output_path}")
            continue
        if not SHA256_DIGEST_PATTERN.match(digest):
            result.errors.append(f"evaluator {evaluator_id} replay.expected_output_hashes invalid digest for {output_path}")
            continue
        if isinstance(integrity_hashes, dict) and integrity_hashes.get(output_path) != digest:
            result.errors.append(
                f"evaluator {evaluator_id} replay.expected_output_hashes disagrees with integrity.output_hashes for {output_path}"
            )
            continue
        if not path_exists(root_path, output_path):
            result.errors.append(f"evaluator {evaluator_id} replay.expected_output_hashes path does not exist: {output_path}")
            continue
        actual = _sha256_digest(root_path / output_path)
        if actual != digest:
            result.errors.append(f"evaluator {evaluator_id} replay.expected_output_hashes mismatch for {output_path}")
        else:
            result.messages.append(f"PASS evaluator {evaluator_id} replay.expected_output_hashes {output_path}")


def _sha256_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json_object(path: Path, result: EvaluatorReplayValidationResult, label: str) -> dict[str, Any] | None:
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


def _list_of_non_empty_strings(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(item, str) and item.strip() for item in value)


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_safe_local_reference(root: Path, reference: str) -> bool:
    candidate = Path(reference)
    if candidate.is_absolute():
        return False
    try:
        (root / candidate).resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate CIPH evaluator replay readiness metadata.")
    parser.add_argument("run_dir", type=Path, help="Path to run directory")
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root for path references")
    parser.add_argument("--output", type=Path, default=None, help="Write replay readiness report to this path")
    args = parser.parse_args(argv)

    result = validate_evaluator_replay(args.run_dir, root=args.root)
    if args.output is not None:
        path = write_evaluator_replay_report(args.run_dir, args.output, root=args.root)
        print(f"Wrote CIPH evaluator replay report: {path}")

    print(render_evaluator_replay_text(args.run_dir, result), end="")
    for error in result.errors:
        print(f"ERROR {error}", file=sys.stderr)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
