#!/usr/bin/env python3
"""Validate CIPH evaluation protocol files."""

from __future__ import annotations

import argparse
import json
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


EVALUATION_SCHEMA_VERSION = "ciph.evaluation.v1"
VALID_PHASES = {"search", "holdout_released"}


@dataclass
class EvaluationValidationResult:
    messages: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_evaluation(run_dir: Path | str, root: Path | str = ".") -> EvaluationValidationResult:
    run_path = Path(run_dir)
    root_path = Path(root)
    result = EvaluationValidationResult()

    evaluation_path = run_path / "EVALUATION.json"
    payload = _load_json_object(evaluation_path, result, "EVALUATION.json")
    if payload is None:
        return result

    _validate_shape(payload, run_path, result)
    candidate_records = _candidate_records(payload, result)
    _validate_splits(payload, result)
    _validate_budget(payload, result)
    _validate_candidates(payload, candidate_records, run_path, root_path, result)
    _validate_phase_rules(payload, candidate_records, root_path, result)
    return result


def write_evaluation_report(run_dir: Path | str, output_path: Path | str, root: Path | str = ".") -> Path:
    result = validate_evaluation(run_dir, root=root)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix == ".html":
        output.write_text(render_evaluation_report(run_dir, result), encoding="utf-8")
    else:
        output.write_text(render_evaluation_text(run_dir, result), encoding="utf-8")
    return output


def render_evaluation_report(run_dir: Path | str, result: EvaluationValidationResult) -> str:
    status = "PASS" if result.ok else "FAIL"
    return render_html_document(
        title="CIPH Evaluation Protocol",
        heading="CIPH Evaluation Protocol",
        report_kind="evaluation-protocol",
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


def render_evaluation_text(run_dir: Path | str, result: EvaluationValidationResult) -> str:
    status = "PASS" if result.ok else "FAIL"
    lines = [f"{status} evaluation {run_dir}"]
    lines.extend(result.messages)
    lines.extend(f"ERROR {error}" for error in result.errors)
    return "\n".join(lines) + "\n"


def _validate_shape(payload: dict[str, Any], run_path: Path, result: EvaluationValidationResult) -> None:
    if payload.get("schema_version") != EVALUATION_SCHEMA_VERSION:
        result.errors.append(f"schema_version must be {EVALUATION_SCHEMA_VERSION}")

    run_id = payload.get("run_id")
    if run_id != run_path.name:
        result.errors.append(f"run_id must match run directory name: {run_path.name}")

    phase = payload.get("phase")
    if phase not in VALID_PHASES:
        result.errors.append("phase must be one of: holdout_released, search")
    else:
        result.messages.append(f"PASS phase {phase}")

    if not _non_empty_string(payload.get("baseline_candidate_id")):
        result.errors.append("baseline_candidate_id must be a non-empty string")

    if not isinstance(payload.get("frontier_candidate_ids"), list):
        result.errors.append("frontier_candidate_ids must be a list")


def _validate_splits(payload: dict[str, Any], result: EvaluationValidationResult) -> None:
    search_ids = _scenario_ids(payload.get("search_set"), "search_set", result)
    holdout_ids = _scenario_ids(payload.get("holdout_set"), "holdout_set", result)
    if not search_ids or not holdout_ids:
        return

    overlap = sorted(search_ids & holdout_ids)
    if overlap:
        result.errors.append(f"search_set and holdout_set scenario_ids must be disjoint: {', '.join(overlap)}")
    else:
        result.messages.append("PASS search/holdout split separation")

    phase = payload.get("phase")
    holdout_set = payload.get("holdout_set")
    if not isinstance(holdout_set, dict):
        return
    holdout_sealed = holdout_set.get("sealed")
    if phase == "search":
        if holdout_sealed is True:
            result.messages.append("PASS holdout sealed")
        else:
            result.errors.append("holdout_set.sealed must be true during search")
    elif phase == "holdout_released":
        if holdout_sealed is False:
            result.messages.append("PASS holdout released")
        else:
            result.errors.append("holdout_set.sealed must be false after holdout release")


def _validate_budget(payload: dict[str, Any], result: EvaluationValidationResult) -> None:
    budget = payload.get("budget")
    if not isinstance(budget, dict):
        result.errors.append("budget must be an object")
        return
    for field_name in ["max_candidates", "max_holdout_releases"]:
        value = budget.get(field_name)
        if isinstance(value, int) and value > 0:
            result.messages.append(f"PASS budget {field_name}={value}")
        else:
            result.errors.append(f"budget.{field_name} must be a positive integer")


def _validate_candidates(
    payload: dict[str, Any],
    candidate_records: dict[str, dict[str, Any]],
    run_path: Path,
    root_path: Path,
    result: EvaluationValidationResult,
) -> None:
    baseline_id = payload.get("baseline_candidate_id")
    if isinstance(baseline_id, str) and baseline_id in candidate_records:
        result.messages.append(f"PASS baseline candidate {baseline_id}")
    elif isinstance(baseline_id, str):
        result.errors.append(f"baseline candidate must be listed: {baseline_id}")

    for candidate_id, record in candidate_records.items():
        score_path = record.get("score_path")
        if not _non_empty_string(score_path):
            result.errors.append(f"candidate {candidate_id} score_path must be a non-empty string")
            continue
        if not path_exists(root_path, score_path):
            result.errors.append(f"candidate {candidate_id} score_path does not exist: {score_path}")
            continue

        score = _load_json_object(root_path / score_path, result, str(score_path))
        if score is None:
            continue
        if score.get("candidate_id") != candidate_id:
            result.errors.append(f"candidate {candidate_id} score_path candidate_id mismatch")
        else:
            result.messages.append(f"PASS candidate score {candidate_id}")

        candidate_dir = run_path / "candidates" / candidate_id
        if not candidate_dir.is_dir():
            result.errors.append(f"candidate directory does not exist: {candidate_dir}")


def _validate_phase_rules(
    payload: dict[str, Any],
    candidate_records: dict[str, dict[str, Any]],
    root_path: Path,
    result: EvaluationValidationResult,
) -> None:
    phase = payload.get("phase")
    frontier_ids = _string_list(payload.get("frontier_candidate_ids"))
    known_ids = set(candidate_records)

    for frontier_id in frontier_ids:
        if frontier_id not in known_ids:
            result.errors.append(f"frontier candidate must be listed: {frontier_id}")

    if phase == "holdout_released" and not frontier_ids:
        result.errors.append("holdout_released phase requires at least one frontier candidate")
    if phase == "holdout_released":
        _validate_holdout_releases(payload, frontier_ids, result)

    if phase != "search":
        return

    for candidate_id, record in candidate_records.items():
        if record.get("evaluation_phase") == "holdout":
            result.errors.append(f"search phase forbids holdout evaluation_phase for {candidate_id}")
        holdout_score_path = record.get("holdout_score_path")
        if _non_empty_string(holdout_score_path):
            result.errors.append(f"search phase forbids holdout_score_path for {candidate_id}")

        score_path = record.get("score_path")
        if not _non_empty_string(score_path) or not path_exists(root_path, score_path):
            continue
        score = _load_json_object(root_path / score_path, result, str(score_path))
        if isinstance(score, dict) and "holdout_scores" in score:
            result.errors.append(f"search phase forbids holdout_scores in {score_path}")


def _validate_holdout_releases(
    payload: dict[str, Any],
    frontier_ids: list[str],
    result: EvaluationValidationResult,
) -> None:
    releases = payload.get("holdout_releases")
    if not isinstance(releases, list) or not releases:
        result.errors.append("holdout_releases must contain at least one release after holdout release")
        return

    budget = payload.get("budget")
    max_releases = None
    if isinstance(budget, dict) and isinstance(budget.get("max_holdout_releases"), int):
        max_releases = budget["max_holdout_releases"]
    if isinstance(max_releases, int) and max_releases > 0 and len(releases) > max_releases:
        result.errors.append(
            f"holdout_releases count exceeds budget.max_holdout_releases: {len(releases)}/{max_releases}"
        )

    known_frontier_ids = set(frontier_ids)
    for index, release in enumerate(releases):
        label = f"holdout_releases[{index}]"
        if not isinstance(release, dict):
            result.errors.append(f"{label} must be an object")
            continue

        release_index = release.get("release_index")
        if not isinstance(release_index, int) or release_index <= 0:
            result.errors.append(f"{label}.release_index must be a positive integer")
        if not _non_empty_string(release.get("released_at")):
            result.errors.append(f"{label}.released_at must be a non-empty string")

        release_frontier_ids = _string_list(release.get("frontier_candidate_ids"))
        if not release_frontier_ids:
            result.errors.append(f"{label}.frontier_candidate_ids must contain at least one candidate")
        for candidate_id in release_frontier_ids:
            if candidate_id not in known_frontier_ids:
                result.errors.append(f"{label}.frontier_candidate_ids includes unlisted frontier candidate: {candidate_id}")

        if isinstance(release_index, int) and release_index > 0 and release_frontier_ids:
            result.messages.append(f"PASS holdout release {release_index}")


def _candidate_records(payload: dict[str, Any], result: EvaluationValidationResult) -> dict[str, dict[str, Any]]:
    candidates = payload.get("candidates")
    records: dict[str, dict[str, Any]] = {}
    if not isinstance(candidates, list):
        result.errors.append("candidates must be a list")
        return records

    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            result.errors.append(f"candidates[{index}] must be an object")
            continue
        candidate_id = candidate.get("candidate_id")
        if not _non_empty_string(candidate_id):
            result.errors.append(f"candidates[{index}].candidate_id must be a non-empty string")
            continue
        if candidate_id in records:
            result.errors.append(f"candidate_id must be unique: {candidate_id}")
            continue
        records[str(candidate_id)] = candidate
    return records


def _scenario_ids(value: Any, field_name: str, result: EvaluationValidationResult) -> set[str]:
    if not isinstance(value, dict):
        result.errors.append(f"{field_name} must be an object")
        return set()
    scenario_ids = value.get("scenario_ids")
    ids = _string_list(scenario_ids)
    if not ids:
        result.errors.append(f"{field_name}.scenario_ids must contain at least one scenario id")
        return set()
    return set(ids)


def _load_json_object(path: Path, result: EvaluationValidationResult, label: str) -> dict[str, Any] | None:
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
    parser = argparse.ArgumentParser(description="Validate a CIPH evaluation protocol.")
    parser.add_argument("run_dir", type=Path, help="Path to run directory")
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root for protocol references")
    parser.add_argument("--output", type=Path, default=None, help="Write validation report to this path")
    args = parser.parse_args(argv)

    result = validate_evaluation(args.run_dir, root=args.root)
    if args.output is not None:
        path = write_evaluation_report(args.run_dir, args.output, root=args.root)
        print(f"Wrote CIPH evaluation report: {path}")

    print(render_evaluation_text(args.run_dir, result), end="")
    for error in result.errors:
        print(f"ERROR {error}", file=sys.stderr)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
