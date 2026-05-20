#!/usr/bin/env python3
"""Suggest repairs for CIPH traces that fail strict linting."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

try:
    from scripts.html_report import render_html_document, render_table
except ModuleNotFoundError:  # pragma: no cover - exercised by direct script execution.
    from html_report import render_html_document, render_table


SCHEMA_VERSION = "ciph.trace-repair-plan.v1"


def build_trace_repair_plan(report_path: Path | str) -> dict[str, Any]:
    report = _load_json_object(Path(report_path))
    runs = report.get("runs", []) if isinstance(report.get("runs"), list) else []
    repairs = [_repair_run(record) for record in runs if isinstance(record, dict)]
    repairs = [repair for repair in repairs if repair["suggestions"] or repair["unhandled_errors"] or repair["unhandled_warnings"]]
    suggestion_count = sum(len(repair["suggestions"]) for repair in repairs)
    return {
        "schema_version": SCHEMA_VERSION,
        "source_report_path": str(report_path),
        "summary": {
            "runs_with_repairs": len(repairs),
            "suggestions": suggestion_count,
            "unhandled_errors": sum(len(repair["unhandled_errors"]) for repair in repairs),
            "unhandled_warnings": sum(len(repair["unhandled_warnings"]) for repair in repairs),
        },
        "repairs": repairs,
    }


def write_trace_repair_plan(payload: dict[str, Any], output: Path | str, report_format: str) -> None:
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if report_format == "html":
        output_path.write_text(render_trace_repair_html(payload), encoding="utf-8")
    else:
        output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def render_trace_repair_html(payload: dict[str, Any]) -> str:
    summary = payload.get("summary", {})
    rows: list[list[str]] = []
    for repair in payload.get("repairs", []):
        if not isinstance(repair, dict):
            continue
        for suggestion in repair.get("suggestions", []):
            if not isinstance(suggestion, dict):
                continue
            rows.append(
                [
                    repair.get("run_id", ""),
                    suggestion.get("kind", ""),
                    suggestion.get("line", ""),
                    suggestion.get("action", ""),
                    suggestion.get("event_type", ""),
                    suggestion.get("rationale", ""),
                ]
            )
    return render_html_document(
        title="CIPH Trace Repair Plan",
        heading="CIPH Trace Repair Plan",
        report_kind="trace-repair-plan",
        summary_items=[
            ("Runs", str(summary.get("runs_with_repairs", 0))),
            ("Suggestions", str(summary.get("suggestions", 0))),
            ("Unhandled Errors", str(summary.get("unhandled_errors", 0))),
            ("Unhandled Warnings", str(summary.get("unhandled_warnings", 0))),
        ],
        sections=[
            {
                "id": "suggestions",
                "title": "Repair Suggestions",
                "body_html": render_table(
                    ["Run", "Kind", "Line", "Action", "Event Type", "Rationale"],
                    rows,
                ),
            }
        ],
    )


def _repair_run(record: dict[str, Any]) -> dict[str, Any]:
    suggestions: list[dict[str, Any]] = []
    unhandled_errors: list[str] = []
    unhandled_warnings: list[str] = []
    for error in _string_list(record.get("errors")):
        suggestion = _suggest_from_message(error)
        if suggestion is None:
            unhandled_errors.append(error)
        else:
            suggestions.append(suggestion)
    for warning in _string_list(record.get("warnings")):
        suggestion = _suggest_from_message(warning)
        if suggestion is None:
            unhandled_warnings.append(warning)
        else:
            suggestions.append(suggestion)
    return {
        "run_id": record.get("run_id", ""),
        "trace_path": record.get("trace_path"),
        "strict_status": record.get("strict_status"),
        "suggestions": suggestions,
        "unhandled_errors": unhandled_errors,
        "unhandled_warnings": unhandled_warnings,
    }


def _suggest_from_message(message: str) -> dict[str, Any] | None:
    candidate = re.search(r"line (?P<line>\d+) candidate scored before creation: (?P<candidate_id>.+)$", message)
    if candidate:
        candidate_id = candidate.group("candidate_id")
        return {
            "kind": "insert-event-before-line",
            "line": int(candidate.group("line")),
            "action": "insert candidate.created before candidate.scored",
            "event_type": "candidate.created",
            "event_fields": {"candidate_id": candidate_id},
            "rationale": f"Strict lint requires candidate.created before scoring {candidate_id}.",
            "apply_mode": "manual",
        }

    validation = re.search(r"line (?P<line>\d+) validation completed without validation\.started: (?P<check_name>.+)$", message)
    if validation:
        check_name = validation.group("check_name")
        return {
            "kind": "insert-event-before-line",
            "line": int(validation.group("line")),
            "action": "insert validation.started before validation.completed",
            "event_type": "validation.started",
            "event_fields": {"check_name": check_name},
            "rationale": f"Strict lint prefers validation.started before completing {check_name}.",
            "apply_mode": "manual",
        }

    path = re.search(r"line (?P<line>\d+) (?P<field>[A-Za-z0-9_]+) must be a local path under the root: (?P<value>.+)$", message)
    if path:
        return {
            "kind": "edit-field",
            "line": int(path.group("line")),
            "action": "replace unsafe local reference with a repo-root-relative path",
            "event_type": "unknown",
            "event_fields": {path.group("field"): path.group("value")},
            "rationale": "Strict lint requires local references to remain inside the repository root.",
            "apply_mode": "manual",
        }

    missing = re.search(r"line (?P<line>\d+) (?P<field>[A-Za-z0-9_]+) does not exist: (?P<value>.+)$", message)
    if missing:
        return {
            "kind": "review-reference",
            "line": int(missing.group("line")),
            "action": "create the referenced artifact or update the trace reference",
            "event_type": "unknown",
            "event_fields": {missing.group("field"): missing.group("value")},
            "rationale": "Strict lint found a repo-local reference that does not exist on disk.",
            "apply_mode": "manual",
        }

    return None


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to read JSON object from {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"JSON must contain an object: {path}")
    return payload


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Suggest repairs for CIPH traces that fail strict linting.")
    parser.add_argument("strictness_report", type=Path, help="Path to trace strictness JSON report")
    parser.add_argument("--format", choices=["json", "html"], default="json", help="Output format")
    parser.add_argument("--output", type=Path, default=None, help="Write repair plan to this path")
    args = parser.parse_args(argv)

    try:
        payload = build_trace_repair_plan(args.strictness_report)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    if args.output is not None:
        write_trace_repair_plan(payload, args.output, args.format)
        print(f"Wrote CIPH trace repair plan: {args.output}")
    elif args.format == "html":
        print(render_trace_repair_html(payload), end="")
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
