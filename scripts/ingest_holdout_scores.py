#!/usr/bin/env python3
"""Ingest CIPH holdout score records after holdout release."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from scripts.html_report import render_html_document
    from scripts.validate_evaluation import HOLDOUT_SCORE_SCHEMA_VERSION, OBJECTIVE_METRICS, validate_evaluation
except ModuleNotFoundError:  # pragma: no cover - exercised by direct script execution.
    from html_report import render_html_document
    from validate_evaluation import HOLDOUT_SCORE_SCHEMA_VERSION, OBJECTIVE_METRICS, validate_evaluation


@dataclass
class HoldoutIngestResult:
    messages: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    updated: bool = False
    score_path: str | None = None

    @property
    def ok(self) -> bool:
        return not self.errors


def ingest_holdout_scores(
    run_dir: Path | str,
    score_path: Path | str,
    root: Path | str = ".",
) -> HoldoutIngestResult:
    run_path = Path(run_dir)
    root_path = Path(root)
    result = HoldoutIngestResult()
    evaluation_path = run_path / "EVALUATION.json"

    evaluation = _load_json_object(evaluation_path, result, "EVALUATION.json")
    if evaluation is None:
        return result
    score = _load_json_object(Path(score_path), result, "holdout score")
    if score is None:
        return result

    if evaluation.get("phase") != "holdout_released":
        result.errors.append("phase must be holdout_released before ingesting holdout scores")
        return result

    existing_validation = validate_evaluation(run_path, root=root_path)
    if not existing_validation.ok:
        result.errors.extend(f"evaluation {error}" for error in existing_validation.errors)
        return result

    candidate_id = score.get("candidate_id")
    score_errors = _validate_score_shape(score, evaluation)
    if score_errors:
        result.errors.extend(score_errors)
        return result
    assert isinstance(candidate_id, str)
    release_index = score["release_index"]
    assert isinstance(release_index, int)

    release_candidates = _release_candidates(evaluation, release_index)
    if candidate_id not in release_candidates:
        result.errors.append(f"candidate {candidate_id} was not in holdout release {release_index} frontier")
        return result

    candidate = _candidate_record(evaluation, candidate_id)
    if candidate is None:
        result.errors.append(f"candidate must be listed: {candidate_id}")
        return result

    canonical = run_path / "holdout_scores" / f"{candidate_id}.json"
    canonical_display = _display_path(canonical, root_path)
    result.score_path = canonical_display
    rendered_score = json.dumps(score, indent=2) + "\n"
    desired_candidate = dict(candidate)
    desired_candidate["evaluation_phase"] = "holdout"
    desired_candidate["holdout_score_path"] = canonical_display
    desired_candidate["holdout_score_ingested_at"] = score["scored_at"]

    already_written = canonical.is_file() and _load_json_silent(canonical) == score
    already_linked = candidate == desired_candidate
    if already_written and already_linked:
        result.messages.append(f"PASS holdout score already ingested {candidate_id}")
        return result
    if canonical.is_file() and not already_written:
        result.errors.append(f"canonical holdout score already exists with different content: {canonical_display}")
        return result

    original_evaluation = evaluation_path.read_text(encoding="utf-8")
    canonical.parent.mkdir(parents=True, exist_ok=True)
    canonical.write_text(rendered_score, encoding="utf-8")
    _replace_candidate_record(evaluation, candidate_id, desired_candidate)
    evaluation_path.write_text(json.dumps(evaluation, indent=2) + "\n", encoding="utf-8")

    post_validation = validate_evaluation(run_path, root=root_path)
    if not post_validation.ok:
        evaluation_path.write_text(original_evaluation, encoding="utf-8")
        if not already_written and canonical.is_file():
            canonical.unlink()
        result.errors.extend(f"post-ingest evaluation {error}" for error in post_validation.errors)
        return result

    result.updated = True
    result.messages.extend(post_validation.messages)
    result.messages.append(f"PASS ingested holdout score {candidate_id}")
    return result


def render_holdout_ingest_report(run_dir: Path | str, result: HoldoutIngestResult) -> str:
    status = "PASS" if result.ok else "FAIL"
    return render_html_document(
        title="CIPH Holdout Ingest",
        heading="CIPH Holdout Ingest",
        report_kind="holdout-ingest",
        summary_items=[
            ("Run", str(run_dir)),
            ("Status", status),
            ("Updated", str(result.updated).lower()),
            ("Score Path", result.score_path or "-"),
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


def render_holdout_ingest_text(run_dir: Path | str, result: HoldoutIngestResult) -> str:
    status = "PASS" if result.ok else "FAIL"
    lines = [f"{status} holdout ingest {run_dir}"]
    lines.extend(result.messages)
    lines.extend(f"ERROR {error}" for error in result.errors)
    return "\n".join(lines) + "\n"


def _validate_score_shape(score: dict[str, Any], evaluation: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if score.get("schema_version") != HOLDOUT_SCORE_SCHEMA_VERSION:
        errors.append(f"schema_version must be {HOLDOUT_SCORE_SCHEMA_VERSION}")
    if not _non_empty_string(score.get("candidate_id")):
        errors.append("candidate_id must be a non-empty string")
    if not isinstance(score.get("release_index"), int) or score.get("release_index") <= 0:
        errors.append("release_index must be a positive integer")
    if not _non_empty_string(score.get("scored_at")):
        errors.append("scored_at must be a non-empty string")

    holdout_ids = _holdout_ids(evaluation)
    scenario_ids = _string_list(score.get("scenario_ids"))
    if not scenario_ids:
        errors.append("scenario_ids must contain at least one scenario id")
    else:
        invalid = sorted(set(scenario_ids) - holdout_ids)
        if invalid:
            errors.append(f"scenario_ids must be within holdout_set: {', '.join(invalid)}")

    holdout_scores = score.get("holdout_scores")
    if not isinstance(holdout_scores, dict):
        errors.append("holdout_scores must be an object")
        return errors
    for metric in OBJECTIVE_METRICS:
        if not isinstance(holdout_scores.get(metric), (int, float)):
            errors.append(f"holdout_scores.{metric} must be numeric")
    return errors


def _release_candidates(evaluation: dict[str, Any], release_index: int) -> set[str]:
    releases = evaluation.get("holdout_releases")
    if not isinstance(releases, list):
        return set()
    for release in releases:
        if not isinstance(release, dict):
            continue
        if release.get("release_index") == release_index:
            return set(_string_list(release.get("frontier_candidate_ids")))
    return set()


def _candidate_record(evaluation: dict[str, Any], candidate_id: str) -> dict[str, Any] | None:
    candidates = evaluation.get("candidates")
    if not isinstance(candidates, list):
        return None
    for candidate in candidates:
        if isinstance(candidate, dict) and candidate.get("candidate_id") == candidate_id:
            return candidate
    return None


def _replace_candidate_record(evaluation: dict[str, Any], candidate_id: str, replacement: dict[str, Any]) -> None:
    candidates = evaluation.get("candidates")
    if not isinstance(candidates, list):
        return
    for index, candidate in enumerate(candidates):
        if isinstance(candidate, dict) and candidate.get("candidate_id") == candidate_id:
            candidates[index] = replacement
            return


def _holdout_ids(evaluation: dict[str, Any]) -> set[str]:
    holdout_set = evaluation.get("holdout_set")
    if not isinstance(holdout_set, dict):
        return set()
    return set(_string_list(holdout_set.get("scenario_ids")))


def _load_json_object(path: Path, result: HoldoutIngestResult, label: str) -> dict[str, Any] | None:
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


def _load_json_silent(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _display_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest a CIPH holdout score record after holdout release.")
    parser.add_argument("run_dir", type=Path, help="Path to run directory")
    parser.add_argument("score", type=Path, help="Path to incoming holdout score JSON")
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root for protocol references")
    parser.add_argument("--output", type=Path, default=None, help="Write ingestion report to this path")
    args = parser.parse_args(argv)

    result = ingest_holdout_scores(args.run_dir, args.score, root=args.root)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if args.output.suffix == ".html":
            args.output.write_text(render_holdout_ingest_report(args.run_dir, result), encoding="utf-8")
        else:
            args.output.write_text(render_holdout_ingest_text(args.run_dir, result), encoding="utf-8")
        print(f"Wrote CIPH holdout ingest report: {args.output}")

    print(render_holdout_ingest_text(args.run_dir, result), end="")
    for error in result.errors:
        print(f"ERROR {error}", file=sys.stderr)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
