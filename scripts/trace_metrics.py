#!/usr/bin/env python3
"""Calculate CIPH mechanism metrics from a manifest and trace ledger."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from scripts.verify_manifest import load_manifest, path_exists
except ModuleNotFoundError:  # pragma: no cover - exercised by direct script execution.
    from verify_manifest import load_manifest, path_exists


def calculate_metrics(
    manifest_path: Path | str,
    trace_path: Path | str | None = None,
    root: Path | str | None = None,
) -> dict[str, float]:
    manifest_path = Path(manifest_path)
    root_path = Path(root) if root is not None else manifest_path.parent
    manifest = load_manifest(manifest_path)
    trace_reference = trace_path or _trace_path_from_manifest(manifest)
    events = _load_trace(root_path, trace_reference) if trace_reference is not None else []

    return {
        "artifact_contract_compliance": _artifact_contract_compliance(manifest, root_path),
        "stage_coverage": _stage_coverage(events),
        "ordered_workflow_compliance": _ordered_workflow_compliance(events),
        "tool_call_success": _tool_call_success(events),
        "failed_tool_continuation": _failed_tool_continuation(events),
        "handoff_recall": _handoff_recall(events),
        "validation_coverage": _validation_coverage(manifest, events),
        "recovery_completion": _recovery_completion(events),
    }


def _trace_path_from_manifest(manifest: dict[str, Any]) -> str | None:
    trace = manifest.get("trace")
    if not isinstance(trace, dict):
        return None
    path = trace.get("path")
    return path if isinstance(path, str) and path.strip() else None


def _load_trace(root: Path, trace_path: Path | str) -> list[dict[str, Any]]:
    path = Path(trace_path)
    if not path.is_absolute():
        path = root / path
    if not path.is_file():
        return []

    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            events.append(payload)
    return events


def _artifact_contract_compliance(manifest: dict[str, Any], root: Path) -> float:
    deliverables = manifest.get("deliverables", [])
    if not isinstance(deliverables, list) or not deliverables:
        return 1.0

    covered = 0
    total = 0
    for deliverable in deliverables:
        if not isinstance(deliverable, dict):
            continue
        total += 1
        artifacts = _string_list(deliverable.get("artifact_paths", []))
        evidence = _string_list(deliverable.get("evidence_paths", []))
        if artifacts and evidence and all(path_exists(root, path) for path in [*artifacts, *evidence]):
            covered += 1
    return _ratio(covered, total)


def _stage_coverage(events: list[dict[str, Any]]) -> float:
    started = _unique_field(events, "stage.started", "stage")
    completed = _unique_field(events, "stage.completed", "stage")
    if not started:
        return 1.0 if not completed else 0.0
    return _ratio(len(started & completed), len(started))


def _ordered_workflow_compliance(events: list[dict[str, Any]]) -> float:
    started_positions: dict[str, int] = {}
    completed_order: list[tuple[str, int]] = []
    for index, event in enumerate(events):
        event_type = event.get("event_type")
        stage = event.get("stage")
        if not isinstance(stage, str):
            continue
        if event_type == "stage.started" and stage not in started_positions:
            started_positions[stage] = index
        elif event_type == "stage.completed":
            completed_order.append((stage, index))

    last_start_position = -1
    for stage, completed_position in completed_order:
        started_position = started_positions.get(stage)
        if started_position is None or completed_position < started_position:
            return 0.0
        if started_position < last_start_position:
            return 0.0
        last_start_position = started_position
    return 1.0


def _tool_call_success(events: list[dict[str, Any]]) -> float:
    results = [event for event in events if event.get("event_type") == "tool.result"]
    if not results:
        return 1.0
    passed = sum(1 for event in results if event.get("exit_code") == 0)
    return _ratio(passed, len(results))


def _failed_tool_continuation(events: list[dict[str, Any]]) -> float:
    failed_positions = [
        index
        for index, event in enumerate(events)
        if event.get("event_type") == "tool.result" and event.get("exit_code") != 0
    ]
    if not failed_positions:
        return 1.0
    continued = sum(1 for index in failed_positions if index < len(events) - 1)
    return _ratio(continued, len(failed_positions))


def _handoff_recall(events: list[dict[str, Any]]) -> float:
    created = _unique_field(events, "handoff.created", "child_id")
    reviewed = _unique_field(events, "handoff.reviewed", "child_id")
    if not created:
        return 1.0
    return _ratio(len(created & reviewed), len(created))


def _validation_coverage(manifest: dict[str, Any], events: list[dict[str, Any]]) -> float:
    checks = manifest.get("checks", [])
    if not isinstance(checks, list):
        return 1.0
    required = {
        str(check.get("name"))
        for check in checks
        if isinstance(check, dict) and check.get("required", False) is True and isinstance(check.get("name"), str)
    }
    if not required:
        return 1.0
    completed = {
        str(event.get("check_name"))
        for event in events
        if event.get("event_type") == "validation.completed"
        and event.get("status") == "PASS"
        and isinstance(event.get("check_name"), str)
    }
    return _ratio(len(required & completed), len(required))


def _recovery_completion(events: list[dict[str, Any]]) -> float:
    attempts = [event for event in events if event.get("event_type") == "recovery.attempted"]
    if not attempts:
        return 1.0
    completed_statuses = {"PASS", "passed", "completed", "success", "resolved"}
    completed = sum(1 for event in attempts if event.get("status") in completed_statuses)
    return _ratio(completed, len(attempts))


def _unique_field(events: list[dict[str, Any]], event_type: str, field_name: str) -> set[str]:
    return {
        str(event[field_name])
        for event in events
        if event.get("event_type") == event_type and isinstance(event.get(field_name), str)
    }


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 1.0
    return round(numerator / denominator, 6)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Calculate CIPH mechanism metrics.")
    parser.add_argument("manifest", type=Path, help="Path to MANIFEST.json")
    parser.add_argument("--root", type=Path, default=None, help="Repository root for manifest references")
    parser.add_argument("--trace", type=Path, default=None, help="Override trace path")
    args = parser.parse_args(argv)

    metrics = calculate_metrics(args.manifest, trace_path=args.trace, root=args.root)
    print(json.dumps(metrics, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
