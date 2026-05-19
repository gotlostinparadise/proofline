#!/usr/bin/env python3
"""Lint CIPH trace ledgers for schema and event-contract errors."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


TRACE_SCHEMA_VERSION = "ciph.trace.v1"
REQUIRED_FIELDS = {
    "stage.started": ["stage"],
    "stage.completed": ["stage", "status"],
    "state.written": ["path"],
    "state.loaded": ["path"],
    "model.call": ["role", "input_ref"],
    "model.result": ["role", "output_ref"],
    "tool.call": ["tool", "command"],
    "tool.result": ["tool", "exit_code"],
    "handoff.created": ["child_id", "task_path"],
    "handoff.returned": ["child_id", "response_path"],
    "handoff.reviewed": ["child_id", "status"],
    "validation.started": ["check_name"],
    "validation.completed": ["check_name", "status", "evidence_path"],
    "candidate.created": ["candidate_id"],
    "candidate.scored": ["candidate_id", "score_path"],
    "failure.classified": ["failure_type"],
    "recovery.attempted": ["strategy", "status"],
    "budget.updated": ["budget_type", "remaining"],
    "closeout.completed": ["status"],
}


@dataclass
class TraceLintResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def lint_trace(trace_path: Path | str, root: Path | str | None = None) -> TraceLintResult:
    trace_path = Path(trace_path)
    Path(root) if root is not None else trace_path.parent
    result = TraceLintResult()

    if not trace_path.is_file():
        result.errors.append(f"trace file does not exist: {trace_path}")
        return result

    for line_number, line in enumerate(trace_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            result.errors.append(f"line {line_number} invalid JSON: {exc.msg}")
            continue
        if not isinstance(event, dict):
            result.errors.append(f"line {line_number} event must be a JSON object")
            continue
        _lint_event(event, line_number, result)

    return result


def _lint_event(event: dict[str, Any], line_number: int, result: TraceLintResult) -> None:
    if event.get("schema_version") != TRACE_SCHEMA_VERSION:
        result.errors.append(f"line {line_number} schema_version must be {TRACE_SCHEMA_VERSION}")

    for field_name in ["event_id", "occurred_at", "event_type"]:
        if not _non_empty_string(event.get(field_name)):
            result.errors.append(f"line {line_number} {field_name} must be a non-empty string")

    event_type = event.get("event_type")
    if not isinstance(event_type, str) or not event_type.strip():
        return
    if event_type not in REQUIRED_FIELDS:
        result.errors.append(f"line {line_number} event_type is unknown: {event_type}")
        return

    for field_name in REQUIRED_FIELDS[event_type]:
        if field_name not in event:
            result.errors.append(f"line {line_number} {event_type}.{field_name} must be present")


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lint a CIPH TRACE.jsonl ledger.")
    parser.add_argument("trace", type=Path, help="Path to TRACE.jsonl")
    parser.add_argument("--root", type=Path, default=None, help="Repository root for future path-aware checks")
    args = parser.parse_args(argv)

    result = lint_trace(args.trace, args.root)
    for error in result.errors:
        print(f"ERROR {error}", file=sys.stderr)
    for warning in result.warnings:
        print(f"WARN {warning}")

    if result.errors:
        print(f"FAIL trace {args.trace}", file=sys.stderr)
        return 1

    print(f"PASS trace {args.trace}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
