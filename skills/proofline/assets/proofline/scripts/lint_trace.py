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


def lint_trace(trace_path: Path | str, root: Path | str | None = None, strict: bool = False) -> TraceLintResult:
    trace_path = Path(trace_path)
    root_path = Path(root) if root is not None else trace_path.parent
    result = TraceLintResult()

    if not trace_path.is_file():
        result.errors.append(f"trace file does not exist: {trace_path}")
        return result

    events: list[tuple[int, dict[str, Any]]] = []
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
        events.append((line_number, event))
        _lint_event(event, line_number, result)

    if strict:
        _lint_strict(events, root_path, result)

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


def _lint_strict(events: list[tuple[int, dict[str, Any]]], root: Path, result: TraceLintResult) -> None:
    seen_event_ids: dict[str, int] = {}
    started_stages: dict[str, int] = {}
    completed_stages: set[str] = set()
    validation_started: dict[str, int] = {}
    handoffs_created: dict[str, int] = {}
    candidates_created: dict[str, int] = {}
    model_calls: dict[tuple[str, str], int] = {}
    tool_calls: dict[str, int] = {}

    for line_number, event in events:
        event_id = event.get("event_id")
        if isinstance(event_id, str) and event_id.strip():
            if event_id in seen_event_ids:
                result.errors.append(f"line {line_number} event_id duplicates line {seen_event_ids[event_id]}: {event_id}")
            else:
                seen_event_ids[event_id] = line_number

        _lint_safe_refs(event, line_number, root, result)
        event_type = event.get("event_type")

        if event_type == "stage.started" and _non_empty_string(event.get("stage")):
            stage = str(event["stage"])
            if stage in started_stages and stage not in completed_stages:
                result.errors.append(f"line {line_number} stage started before previous completion: {stage}")
            started_stages[stage] = line_number
        elif event_type == "stage.completed" and _non_empty_string(event.get("stage")):
            stage = str(event["stage"])
            if stage not in started_stages:
                result.errors.append(f"line {line_number} stage completed before start: {stage}")
            completed_stages.add(stage)
        elif event_type == "validation.started" and _non_empty_string(event.get("check_name")):
            validation_started[str(event["check_name"])] = line_number
        elif event_type == "validation.completed" and _non_empty_string(event.get("check_name")):
            check_name = str(event["check_name"])
            if check_name not in validation_started:
                result.warnings.append(f"line {line_number} validation completed without validation.started: {check_name}")
        elif event_type == "handoff.created" and _non_empty_string(event.get("child_id")):
            handoffs_created[str(event["child_id"])] = line_number
        elif event_type in {"handoff.returned", "handoff.reviewed"} and _non_empty_string(event.get("child_id")):
            child_id = str(event["child_id"])
            if child_id not in handoffs_created:
                result.errors.append(f"line {line_number} {event_type} without handoff.created: {child_id}")
        elif event_type == "candidate.created" and _non_empty_string(event.get("candidate_id")):
            candidates_created[str(event["candidate_id"])] = line_number
        elif event_type == "candidate.scored" and _non_empty_string(event.get("candidate_id")):
            candidate_id = str(event["candidate_id"])
            if candidate_id not in candidates_created:
                result.errors.append(f"line {line_number} candidate scored before creation: {candidate_id}")
        elif event_type == "model.call":
            role = event.get("role")
            input_ref = event.get("input_ref")
            if isinstance(role, str) and isinstance(input_ref, str):
                model_calls[(role, input_ref)] = line_number
        elif event_type == "model.result":
            role = event.get("role")
            input_ref = event.get("input_ref")
            if isinstance(role, str) and isinstance(input_ref, str) and (role, input_ref) not in model_calls:
                result.warnings.append(f"line {line_number} model.result without matching model.call: {role}/{input_ref}")
        elif event_type == "tool.call":
            command = event.get("command")
            if isinstance(command, str):
                tool_calls[command] = line_number
        elif event_type == "tool.result":
            command = event.get("command")
            if isinstance(command, str) and command not in tool_calls:
                result.warnings.append(f"line {line_number} tool.result without matching tool.call command: {command}")


def _lint_safe_refs(event: dict[str, Any], line_number: int, root: Path, result: TraceLintResult) -> None:
    for field_name in ["path", "input_ref", "output_ref", "task_path", "response_path", "evidence_path", "score_path"]:
        value = event.get(field_name)
        if not isinstance(value, str) or not value.strip() or _is_external_reference(value):
            continue
        if not _is_safe_local_reference(root, value):
            result.errors.append(f"line {line_number} {field_name} must be a local path under the root: {value}")
        elif field_name in {"path", "task_path", "response_path", "evidence_path", "score_path", "input_ref", "output_ref"}:
            if not (root / value).exists():
                result.warnings.append(f"line {line_number} {field_name} does not exist: {value}")


def _is_external_reference(reference: str) -> bool:
    return reference.startswith(("http://", "https://", "source:"))


def _is_safe_local_reference(root: Path, reference: str) -> bool:
    candidate = Path(reference)
    if candidate.is_absolute():
        return False
    try:
        (root / candidate).resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lint a CIPH TRACE.jsonl ledger.")
    parser.add_argument("trace", type=Path, help="Path to TRACE.jsonl")
    parser.add_argument("--root", type=Path, default=None, help="Repository root for path-aware checks")
    parser.add_argument("--strict", action="store_true", help="Enable cross-event and safe-reference checks")
    args = parser.parse_args(argv)

    result = lint_trace(args.trace, args.root, strict=args.strict)
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
