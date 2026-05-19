#!/usr/bin/env python3
"""Release a CIPH holdout set after search-phase validation."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.html_report import render_html_document
    from scripts.validate_candidate import validate_candidate
    from scripts.validate_evaluation import validate_evaluation
except ModuleNotFoundError:  # pragma: no cover - exercised by direct script execution.
    from html_report import render_html_document
    from validate_candidate import validate_candidate
    from validate_evaluation import validate_evaluation


@dataclass
class HoldoutReleaseResult:
    messages: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    updated: bool = False

    @property
    def ok(self) -> bool:
        return not self.errors


def release_holdout(
    run_dir: Path | str,
    root: Path | str = ".",
    released_at: str | None = None,
) -> HoldoutReleaseResult:
    run_path = Path(run_dir)
    root_path = Path(root)
    result = HoldoutReleaseResult()
    evaluation_path = run_path / "EVALUATION.json"
    payload = _load_json_object(evaluation_path, result, "EVALUATION.json")
    if payload is None:
        return result

    phase = payload.get("phase")
    if phase == "holdout_released":
        validation = validate_evaluation(run_path, root=root_path)
        result.messages.extend(validation.messages)
        result.errors.extend(f"evaluation {error}" for error in validation.errors)
        if validation.ok:
            result.messages.append("PASS holdout already released")
        return result

    if phase != "search":
        result.errors.append("phase must be search or holdout_released before release")
        return result

    validation = validate_evaluation(run_path, root=root_path)
    result.messages.extend(validation.messages)
    if not validation.ok:
        result.errors.extend(f"evaluation {error}" for error in validation.errors)
        return result

    frontier_ids = _string_list(payload.get("frontier_candidate_ids"))
    if not frontier_ids:
        result.errors.append("frontier_candidate_ids must contain at least one candidate before holdout release")
        return result

    candidate_records = _candidate_records(payload)
    for frontier_id in frontier_ids:
        if frontier_id not in candidate_records:
            result.errors.append(f"frontier candidate must be listed: {frontier_id}")
            return result

    releases = payload.get("holdout_releases", [])
    if not isinstance(releases, list):
        result.errors.append("holdout_releases must be a list when present")
        return result

    max_releases = _max_holdout_releases(payload)
    if max_releases is None:
        result.errors.append("budget.max_holdout_releases must be a positive integer")
        return result
    if len(releases) >= max_releases:
        result.errors.append(f"holdout release budget exhausted: {len(releases)}/{max_releases}")
        return result

    for frontier_id in frontier_ids:
        candidate_result = validate_candidate(run_path / "candidates" / frontier_id, root=root_path)
        result.messages.extend(f"candidate {frontier_id} {message}" for message in candidate_result.messages)
        if not candidate_result.ok:
            result.errors.extend(f"candidate {frontier_id} {error}" for error in candidate_result.errors)
            return result

    released_at_value = released_at or _utc_now()
    next_release = {
        "release_index": len(releases) + 1,
        "released_at": released_at_value,
        "frontier_candidate_ids": frontier_ids,
    }
    updated_payload = dict(payload)
    updated_payload["phase"] = "holdout_released"
    updated_payload["holdout_set"] = dict(payload.get("holdout_set", {}))
    updated_payload["holdout_set"]["sealed"] = False
    updated_payload["holdout_releases"] = [*releases, next_release]

    original_text = evaluation_path.read_text(encoding="utf-8")
    evaluation_path.write_text(json.dumps(updated_payload, indent=2) + "\n", encoding="utf-8")
    post_validation = validate_evaluation(run_path, root=root_path)
    if not post_validation.ok:
        evaluation_path.write_text(original_text, encoding="utf-8")
        result.errors.extend(f"post-release evaluation {error}" for error in post_validation.errors)
        return result

    result.updated = True
    result.messages.extend(post_validation.messages)
    result.messages.append(f"PASS released holdout index {next_release['release_index']}")
    return result


def write_holdout_release_report(
    run_dir: Path | str,
    output_path: Path | str,
    root: Path | str = ".",
    released_at: str | None = None,
) -> Path:
    result = release_holdout(run_dir, root=root, released_at=released_at)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix == ".html":
        output.write_text(render_holdout_release_report(run_dir, result), encoding="utf-8")
    else:
        output.write_text(render_holdout_release_text(run_dir, result), encoding="utf-8")
    return output


def render_holdout_release_report(run_dir: Path | str, result: HoldoutReleaseResult) -> str:
    status = "PASS" if result.ok else "FAIL"
    return render_html_document(
        title="CIPH Holdout Release",
        heading="CIPH Holdout Release",
        report_kind="holdout-release",
        summary_items=[
            ("Run", str(run_dir)),
            ("Status", status),
            ("Updated", str(result.updated).lower()),
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


def render_holdout_release_text(run_dir: Path | str, result: HoldoutReleaseResult) -> str:
    status = "PASS" if result.ok else "FAIL"
    lines = [f"{status} holdout release {run_dir}"]
    lines.extend(result.messages)
    lines.extend(f"ERROR {error}" for error in result.errors)
    return "\n".join(lines) + "\n"


def _load_json_object(path: Path, result: HoldoutReleaseResult, label: str) -> dict[str, Any] | None:
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


def _candidate_records(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        return {}
    records: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        candidate_id = candidate.get("candidate_id")
        if isinstance(candidate_id, str) and candidate_id.strip():
            records[candidate_id] = candidate
    return records


def _max_holdout_releases(payload: dict[str, Any]) -> int | None:
    budget = payload.get("budget")
    if not isinstance(budget, dict):
        return None
    max_releases = budget.get("max_holdout_releases")
    if isinstance(max_releases, int) and max_releases > 0:
        return max_releases
    return None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Release a CIPH holdout set after search-phase validation.")
    parser.add_argument("run_dir", type=Path, help="Path to run directory")
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root for protocol references")
    parser.add_argument("--released-at", default=None, help="UTC release timestamp to record")
    parser.add_argument("--output", type=Path, default=None, help="Write holdout release report to this path")
    args = parser.parse_args(argv)

    result = release_holdout(args.run_dir, root=args.root, released_at=args.released_at)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if args.output.suffix == ".html":
            args.output.write_text(render_holdout_release_report(args.run_dir, result), encoding="utf-8")
        else:
            args.output.write_text(render_holdout_release_text(args.run_dir, result), encoding="utf-8")
        print(f"Wrote CIPH holdout release report: {args.output}")

    print(render_holdout_release_text(args.run_dir, result), end="")
    for error in result.errors:
        print(f"ERROR {error}", file=sys.stderr)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
