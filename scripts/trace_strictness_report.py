#!/usr/bin/env python3
"""Report CIPH trace strictness readiness across run manifests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts.html_report import render_html_document, render_table
    from scripts.lint_trace import lint_trace
    from scripts.verify_manifest import load_manifest
except ModuleNotFoundError:  # pragma: no cover - exercised by direct script execution.
    from html_report import render_html_document, render_table
    from lint_trace import lint_trace
    from verify_manifest import load_manifest


SCHEMA_VERSION = "ciph.trace-strictness-report.v1"


def build_trace_strictness_report(*, root: Path | str = ".", runs_dir: Path | str | None = None) -> dict[str, Any]:
    root_path = Path(root)
    runs_path = Path(runs_dir) if runs_dir is not None else root_path / "runs"
    records = [_build_record(manifest_path, root_path) for manifest_path in _manifest_paths(runs_path)]
    return {
        "schema_version": SCHEMA_VERSION,
        "query": {
            "runs_dir": _display_path(runs_path, root_path),
        },
        "summary": {
            "total_runs": len(records),
            "strict_opt_in_runs": sum(1 for record in records if record["strict_opt_in"]),
            "strict_ready_runs": sum(1 for record in records if record["strict_status"] == "PASS"),
            "strict_error_runs": sum(1 for record in records if record["strict_errors"] > 0),
            "strict_warning_runs": sum(1 for record in records if record["strict_warnings"] > 0),
        },
        "runs": records,
    }


def write_trace_strictness_report(payload: dict[str, Any], output: Path | str, report_format: str) -> None:
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if report_format == "html":
        output_path.write_text(render_trace_strictness_html(payload), encoding="utf-8")
    else:
        output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def render_trace_strictness_html(payload: dict[str, Any]) -> str:
    summary = payload.get("summary", {})
    rows = [
        [
            record.get("run_id", ""),
            "yes" if record.get("strict_opt_in") else "no",
            record.get("strict_status", ""),
            str(record.get("strict_errors", 0)),
            str(record.get("strict_warnings", 0)),
            record.get("trace_path", "") or "",
        ]
        for record in payload.get("runs", [])
        if isinstance(record, dict)
    ]
    return render_html_document(
        title="CIPH Trace Strictness Report",
        heading="CIPH Trace Strictness Report",
        report_kind="trace-strictness",
        summary_items=[
            ("Runs", str(summary.get("total_runs", 0))),
            ("Strict Opt-In", str(summary.get("strict_opt_in_runs", 0))),
            ("Strict Ready", str(summary.get("strict_ready_runs", 0))),
            ("Error Runs", str(summary.get("strict_error_runs", 0))),
            ("Warning Runs", str(summary.get("strict_warning_runs", 0))),
        ],
        sections=[
            {
                "id": "runs",
                "title": "Runs",
                "body_html": render_table(
                    ["Run", "Opt-In", "Strict Status", "Errors", "Warnings", "Trace"],
                    rows,
                ),
            }
        ],
    )


def _build_record(manifest_path: Path, root: Path) -> dict[str, Any]:
    try:
        manifest = load_manifest(manifest_path)
    except ValueError as exc:
        return {
            "run_id": manifest_path.parent.name,
            "manifest_path": _display_path(manifest_path, root),
            "trace_path": None,
            "strict_opt_in": False,
            "strict_status": "MANIFEST_ERROR",
            "strict_errors": 1,
            "strict_warnings": 0,
            "errors": [str(exc)],
            "warnings": [],
        }

    trace = manifest.get("trace")
    run_id = str(manifest.get("task_id") or manifest_path.parent.name)
    strict_opt_in = isinstance(trace, dict) and trace.get("strict") is True
    trace_path = trace.get("path") if isinstance(trace, dict) else None
    if not isinstance(trace_path, str) or not trace_path.strip():
        return _record(run_id, manifest_path, None, strict_opt_in, "MISSING", ["trace.path missing"], [], root)

    lint_result = lint_trace(root / trace_path, root=root, strict=True)
    status = "PASS" if lint_result.ok else "FAIL"
    return _record(run_id, manifest_path, trace_path, strict_opt_in, status, lint_result.errors, lint_result.warnings, root)


def _record(
    run_id: str,
    manifest_path: Path,
    trace_path: str | None,
    strict_opt_in: bool,
    status: str,
    errors: list[str],
    warnings: list[str],
    root: Path,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "manifest_path": _display_path(manifest_path, root),
        "trace_path": trace_path,
        "strict_opt_in": strict_opt_in,
        "strict_status": status,
        "strict_errors": len(errors),
        "strict_warnings": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }


def _manifest_paths(runs_path: Path) -> list[Path]:
    if not runs_path.exists():
        return []
    return sorted(path for path in runs_path.glob("*/MANIFEST.json") if path.is_file())


def _display_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report trace strictness readiness across CIPH runs.")
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root")
    parser.add_argument("--runs-dir", type=Path, default=None, help="Runs directory; defaults to <root>/runs")
    parser.add_argument("--format", choices=["json", "html"], default="json", help="Output format")
    parser.add_argument("--output", type=Path, default=None, help="Write report to this path")
    args = parser.parse_args(argv)

    payload = build_trace_strictness_report(root=args.root, runs_dir=args.runs_dir)
    if args.output is not None:
        write_trace_strictness_report(payload, args.output, args.format)
        print(f"Wrote CIPH trace strictness report: {args.output}")
    elif args.format == "html":
        print(render_trace_strictness_html(payload), end="")
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
