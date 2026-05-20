#!/usr/bin/env python3
"""Query CIPH run experience as a deterministic read-only projection."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from html import escape
import json
from pathlib import Path
from typing import Any

try:
    from scripts.html_report import render_html_document, render_table
    from scripts.verify_manifest import load_manifest
except ModuleNotFoundError:  # pragma: no cover - exercised by direct script execution.
    from html_report import render_html_document, render_table
    from verify_manifest import load_manifest


SCHEMA_VERSION = "ciph.experience-store.v1"


@dataclass(frozen=True)
class ExperienceFilters:
    status: str | None = None
    event_type: str | None = None
    contains: str | None = None
    has_replay_receipts: bool = False
    limit: int | None = None


def query_experience_store(
    *,
    root: Path | str = ".",
    runs_dir: Path | str | None = None,
    status: str | None = None,
    event_type: str | None = None,
    contains: str | None = None,
    has_replay_receipts: bool = False,
    limit: int | None = None,
) -> dict[str, Any]:
    """Return a deterministic query result over CIPH run records."""

    root_path = Path(root)
    runs_path = Path(runs_dir) if runs_dir is not None else root_path / "runs"
    filters = ExperienceFilters(
        status=status.upper() if isinstance(status, str) and status else None,
        event_type=event_type,
        contains=contains.lower() if isinstance(contains, str) and contains else None,
        has_replay_receipts=has_replay_receipts,
        limit=limit,
    )
    all_records = [_build_record(manifest_path, root_path) for manifest_path in _manifest_paths(runs_path)]
    records = [_record for _record in all_records if _matches(_record, filters)]
    records.sort(key=lambda record: record["run_id"], reverse=True)
    if filters.limit is not None:
        records = records[: filters.limit]

    return {
        "schema_version": SCHEMA_VERSION,
        "query": {
            "runs_dir": _display_path(runs_path, root_path),
            "status": filters.status,
            "event_type": filters.event_type,
            "contains": filters.contains,
            "has_replay_receipts": filters.has_replay_receipts,
            "limit": filters.limit,
        },
        "summary": {
            "total_runs": len(all_records),
            "filtered_runs": len(records),
            "pass_runs": sum(1 for record in all_records if record["closeout_status"] == "PASS"),
            "runs_with_replay_receipts": sum(1 for record in all_records if record["replay_receipts"]),
        },
        "runs": records,
    }


def write_experience_store_report(payload: dict[str, Any], output: Path | str, report_format: str) -> None:
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if report_format == "html":
        output_path.write_text(render_experience_store_html(payload), encoding="utf-8")
        return
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def render_experience_store_html(payload: dict[str, Any]) -> str:
    summary = payload.get("summary", {})
    runs = payload.get("runs", [])
    run_rows = [
        [
            record.get("run_id", ""),
            record.get("closeout_status", "UNKNOWN"),
            str(record.get("trace_event_count", 0)),
            str(len(record.get("replay_receipts", []))),
            record.get("objective", ""),
        ]
        for record in runs
    ]
    receipt_rows: list[list[str]] = []
    for record in runs:
        for receipt in record.get("replay_receipts", []):
            receipt_rows.append(
                [
                    record.get("run_id", ""),
                    receipt.get("evaluator_id", ""),
                    receipt.get("mode", ""),
                    receipt.get("status", ""),
                    receipt.get("path", ""),
                ]
            )

    filters = payload.get("query", {})
    filter_items = [
        f"{key}: {value}"
        for key, value in filters.items()
        if value not in (None, False, "")
    ]
    return render_html_document(
        title="CIPH Experience Store",
        heading="CIPH Experience Store",
        report_kind="experience-store",
        summary_items=[
            ("Total Runs", str(summary.get("total_runs", 0))),
            ("Filtered Runs", str(summary.get("filtered_runs", 0))),
            ("Pass Runs", str(summary.get("pass_runs", 0))),
            ("Replay Runs", str(summary.get("runs_with_replay_receipts", 0))),
        ],
        sections=[
            {
                "id": "filters",
                "title": "Filters",
                "items": filter_items,
            },
            {
                "id": "runs",
                "title": "Runs",
                "body_html": render_table(
                    ["Run", "Status", "Events", "Receipts", "Objective"],
                    run_rows,
                ),
            },
            {
                "id": "replay-receipts",
                "title": "Replay Receipts",
                "body_html": render_table(
                    ["Run", "Evaluator", "Mode", "Status", "Receipt Path"],
                    receipt_rows,
                ),
            },
        ],
    )


def _manifest_paths(runs_path: Path) -> list[Path]:
    if not runs_path.exists():
        return []
    return sorted(path for path in runs_path.glob("*/MANIFEST.json") if path.is_file())


def _build_record(manifest_path: Path, root: Path) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    run_dir = manifest_path.parent
    trace_path = _trace_path(manifest, run_dir, root)
    events = _load_trace(trace_path)
    receipts = _load_replay_receipts(run_dir, root)
    closeout_status = _closeout_status(events)
    checks = manifest.get("checks", []) if isinstance(manifest.get("checks"), list) else []
    artifacts = manifest.get("artifacts", []) if isinstance(manifest.get("artifacts"), list) else []
    deliverables = manifest.get("deliverables", []) if isinstance(manifest.get("deliverables"), list) else []
    evidence_paths = _manifest_paths_from_deliverables(deliverables, "evidence_paths")
    artifact_paths = _manifest_paths_from_deliverables(deliverables, "artifact_paths")

    event_types = sorted({str(event.get("event_type")) for event in events if isinstance(event.get("event_type"), str)})
    stages = sorted({str(event.get("stage")) for event in events if isinstance(event.get("stage"), str)})
    validation_checks = sorted(
        {
            str(event.get("check_name"))
            for event in events
            if event.get("event_type") == "validation.completed" and isinstance(event.get("check_name"), str)
        }
    )

    return {
        "run_id": str(manifest.get("task_id") or run_dir.name),
        "objective": str(manifest.get("objective") or ""),
        "manifest_path": _display_path(manifest_path, root),
        "trace_path": _display_path(trace_path, root) if trace_path else None,
        "closeout_status": closeout_status,
        "trace_event_count": len(events),
        "event_types": event_types,
        "stages": stages,
        "validation_checks": validation_checks,
        "deliverable_count": len(deliverables),
        "check_count": len(checks),
        "required_artifact_count": sum(1 for artifact in artifacts if isinstance(artifact, dict) and artifact.get("required") is True),
        "artifact_paths": sorted(artifact_paths),
        "evidence_paths": sorted(evidence_paths),
        "replay_receipts": receipts,
    }


def _trace_path(manifest: dict[str, Any], run_dir: Path, root: Path) -> Path | None:
    trace = manifest.get("trace")
    if isinstance(trace, dict) and isinstance(trace.get("path"), str):
        return root / trace["path"]
    candidate = run_dir / "TRACE.jsonl"
    return candidate if candidate.exists() else None


def _load_trace(trace_path: Path | None) -> list[dict[str, Any]]:
    if trace_path is None or not trace_path.is_file():
        return []
    events: list[dict[str, Any]] = []
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            events.append(payload)
    return events


def _load_replay_receipts(run_dir: Path, root: Path) -> list[dict[str, Any]]:
    receipts_dir = run_dir / "replay_receipts"
    if not receipts_dir.is_dir():
        return []
    receipts: list[dict[str, Any]] = []
    for receipt_path in sorted(receipts_dir.glob("*.json")):
        try:
            payload = json.loads(receipt_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        receipts.append(
            {
                "path": _display_path(receipt_path, root),
                "schema_version": _string_or_none(payload.get("schema_version")),
                "evaluator_id": _string_or_none(payload.get("evaluator_id")),
                "mode": _string_or_none(payload.get("mode")),
                "status": _string_or_none(payload.get("status")) or "UNKNOWN",
                "sandbox_mode": _string_or_none(payload.get("sandbox_mode")),
                "command_digest": _string_or_none(payload.get("command_digest")),
                "timeout_seconds": payload.get("timeout_seconds") if isinstance(payload.get("timeout_seconds"), (int, float)) else None,
            }
        )
    return receipts


def _closeout_status(events: list[dict[str, Any]]) -> str:
    for event in reversed(events):
        if event.get("event_type") == "closeout.completed":
            status = event.get("status")
            return str(status).upper() if isinstance(status, str) and status else "UNKNOWN"
    return "UNKNOWN"


def _manifest_paths_from_deliverables(deliverables: list[Any], key: str) -> list[str]:
    paths: list[str] = []
    for deliverable in deliverables:
        if not isinstance(deliverable, dict):
            continue
        values = deliverable.get(key, [])
        if isinstance(values, list):
            paths.extend(value for value in values if isinstance(value, str))
    return paths


def _matches(record: dict[str, Any], filters: ExperienceFilters) -> bool:
    if filters.status and record.get("closeout_status") != filters.status:
        return False
    if filters.event_type and filters.event_type not in record.get("event_types", []):
        return False
    if filters.has_replay_receipts and not record.get("replay_receipts"):
        return False
    if filters.contains and filters.contains not in _search_text(record):
        return False
    return True


def _search_text(record: dict[str, Any]) -> str:
    chunks: list[str] = []
    for key in ["run_id", "objective", "manifest_path", "trace_path", "closeout_status"]:
        value = record.get(key)
        if value is not None:
            chunks.append(str(value))
    for key in ["event_types", "stages", "validation_checks", "artifact_paths", "evidence_paths"]:
        values = record.get(key, [])
        if isinstance(values, list):
            chunks.extend(str(value) for value in values)
    for receipt in record.get("replay_receipts", []):
        if isinstance(receipt, dict):
            chunks.extend(str(value) for value in receipt.values() if value is not None)
    return "\n".join(chunks).lower()


def _string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _display_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Query CIPH run experience records.")
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root")
    parser.add_argument("--runs-dir", type=Path, default=None, help="Runs directory; defaults to <root>/runs")
    parser.add_argument("--status", choices=["PASS", "FAIL", "UNKNOWN"], default=None, help="Filter by closeout status")
    parser.add_argument("--event-type", default=None, help="Filter by trace event type")
    parser.add_argument("--contains", default=None, help="Case-insensitive text filter over indexed metadata and paths")
    parser.add_argument("--has-replay-receipts", action="store_true", help="Only include runs with replay receipts")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of runs to return")
    parser.add_argument("--format", choices=["json", "html"], default="json", help="Output format")
    parser.add_argument("--output", type=Path, default=None, help="Write report to this path instead of stdout")
    args = parser.parse_args(argv)

    if args.limit is not None and args.limit < 1:
        print("ERROR: --limit must be positive")
        return 1

    payload = query_experience_store(
        root=args.root,
        runs_dir=args.runs_dir,
        status=args.status,
        event_type=args.event_type,
        contains=args.contains,
        has_replay_receipts=args.has_replay_receipts,
        limit=args.limit,
    )
    if args.output is not None:
        write_experience_store_report(payload, args.output, args.format)
        print(f"Wrote CIPH experience store query: {args.output}")
        return 0

    if args.format == "html":
        print(render_experience_store_html(payload), end="")
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
