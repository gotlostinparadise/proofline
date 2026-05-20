#!/usr/bin/env python3
"""Calculate CIPH mechanism metrics from a manifest and trace ledger."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from scripts.html_report import render_html_document, render_table
    from scripts.verify_manifest import load_manifest, path_exists
except ModuleNotFoundError:  # pragma: no cover - exercised by direct script execution.
    from html_report import render_html_document, render_table
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
        "model_result_coverage": _model_result_coverage(events),
        "context_token_total": float(_context_token_total(events)),
        "wall_time_seconds": float(_wall_time_seconds(events)),
        "declared_runtime_seconds": float(_declared_runtime_seconds(events)),
        "declared_cost_total": float(_declared_cost_total(events)),
        "cost_proxy": float(_cost_proxy(events)),
        "recovery_evidence_coverage": _recovery_evidence_coverage(events),
    }


def render_metrics_html(metrics: dict[str, float], manifest_path: Path | str) -> str:
    rows = [[_titleize(key), _format_metric(value)] for key, value in sorted(metrics.items())]
    return render_html_document(
        title="CIPH Mechanism Metrics",
        heading="CIPH Mechanism Metrics",
        report_kind="mechanism-metrics",
        summary_items=[
            ("Manifest", str(manifest_path)),
            ("Metrics", str(len(metrics))),
        ],
        sections=[
            {
                "id": "metrics",
                "title": "Metrics",
                "body_html": render_table(["Metric", "Value"], rows),
            }
        ],
    )


def write_metrics_report(metrics: dict[str, float], manifest_path: Path | str, output_path: Path | str) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix == ".html":
        output.write_text(render_metrics_html(metrics, manifest_path), encoding="utf-8")
    else:
        output.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


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


def _model_result_coverage(events: list[dict[str, Any]]) -> float:
    calls = [event for event in events if event.get("event_type") == "model.call"]
    results = [event for event in events if event.get("event_type") == "model.result"]
    if not calls:
        return 1.0
    return _ratio(len(results), len(calls))


def _context_token_total(events: list[dict[str, Any]]) -> int:
    total = 0.0
    for event in events:
        total += _event_token_total(event)
    return int(total)


def _wall_time_seconds(events: list[dict[str, Any]]) -> int:
    timestamps = [_parse_time(event.get("occurred_at")) for event in events]
    timestamps = [timestamp for timestamp in timestamps if timestamp is not None]
    if len(timestamps) < 2:
        return 0
    return max(0, int((max(timestamps) - min(timestamps)).total_seconds()))


def _cost_proxy(events: list[dict[str, Any]]) -> int:
    tool_results = sum(1 for event in events if event.get("event_type") == "tool.result")
    model_tokens = _context_token_total(events)
    return model_tokens + tool_results * 100


def _declared_runtime_seconds(events: list[dict[str, Any]]) -> float:
    total = 0.0
    for event in events:
        total += _event_runtime_seconds(event)
    return round(total, 6)


def _declared_cost_total(events: list[dict[str, Any]]) -> float:
    total = 0.0
    for event in events:
        total += _event_cost(event)
    return round(total, 6)


def _recovery_evidence_coverage(events: list[dict[str, Any]]) -> float:
    recoveries = [event for event in events if event.get("event_type") == "recovery.attempted"]
    if not recoveries:
        return 1.0
    covered = sum(
        1
        for event in recoveries
        if isinstance(event.get("evidence_path"), str)
        or isinstance(event.get("linked_event_id"), str)
        or isinstance(event.get("failure_event_id"), str)
    )
    return _ratio(covered, len(recoveries))


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


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


def _event_token_total(event: dict[str, Any]) -> float:
    mappings = _event_metric_mappings(event)
    total_values = [
        _positive_number(mapping.get(field_name))
        for mapping in mappings
        for field_name in ["total_tokens", "tokens_total"]
    ]
    total_values = [value for value in total_values if value is not None]
    if total_values:
        return max(total_values)

    categories = [
        ["context_tokens"],
        ["input_tokens", "prompt_tokens"],
        ["output_tokens", "completion_tokens"],
    ]
    total = 0.0
    for category in categories:
        values = [
            _positive_number(mapping.get(field_name))
            for mapping in mappings
            for field_name in category
        ]
        values = [value for value in values if value is not None]
        if values:
            total += max(values)
    return total


def _event_runtime_seconds(event: dict[str, Any]) -> float:
    values: list[float] = []
    for mapping in _event_metric_mappings(event):
        for field_name in ["duration_seconds", "elapsed_seconds", "runtime_seconds", "wall_seconds"]:
            value = _positive_number(mapping.get(field_name))
            if value is not None:
                values.append(value)
        for field_name in ["duration_ms", "elapsed_ms", "runtime_ms", "wall_time_ms"]:
            value = _positive_number(mapping.get(field_name))
            if value is not None:
                values.append(value / 1000.0)
    return max(values) if values else 0.0


def _event_cost(event: dict[str, Any]) -> float:
    values = [
        _positive_number(mapping.get(field_name))
        for mapping in _event_metric_mappings(event)
        for field_name in ["cost_usd", "estimated_cost_usd", "cost"]
    ]
    values = [value for value in values if value is not None]
    return max(values) if values else 0.0


def _event_metric_mappings(event: dict[str, Any]) -> list[dict[str, Any]]:
    mappings = [event]
    for field_name in ["usage", "token_usage", "metrics"]:
        value = event.get(field_name)
        if isinstance(value, dict):
            mappings.append(value)
    return mappings


def _positive_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and value > 0:
        return float(value)
    return None


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 1.0
    return round(numerator / denominator, 6)


def _titleize(value: str) -> str:
    return value.replace("_", " ").title()


def _format_metric(value: float) -> str:
    return f"{value:.6g}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Calculate CIPH mechanism metrics.")
    parser.add_argument("manifest", type=Path, help="Path to MANIFEST.json")
    parser.add_argument("--root", type=Path, default=None, help="Repository root for manifest references")
    parser.add_argument("--trace", type=Path, default=None, help="Override trace path")
    parser.add_argument("--output", type=Path, default=None, help="Write JSON or HTML report to this path")
    args = parser.parse_args(argv)

    metrics = calculate_metrics(args.manifest, trace_path=args.trace, root=args.root)
    if args.output is not None:
        path = write_metrics_report(metrics, args.manifest, args.output)
        print(f"Wrote CIPH mechanism metrics: {path}")
    else:
        print(json.dumps(metrics, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
