#!/usr/bin/env python3
"""Diagnose run-history quality issues with actionable recommendations."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from scripts.html_report import render_html_document, render_table
    from scripts.verify_manifest import load_manifest, path_exists
except ModuleNotFoundError:  # pragma: no cover - exercised by direct script execution.
    from html_report import render_html_document, render_table
    from verify_manifest import load_manifest, path_exists


SCHEMA_VERSION = "ciph.experience-diagnostics.v1"
SEVERITY_ORDER = ["low", "medium", "high"]


@dataclass(frozen=True)
class _Finding:
    finding_id: str
    severity: str
    run_id: str
    title: str
    reason: str
    evidence_paths: tuple[str, ...]
    recommendation_id: str


def diagnose_experience_store(
    *,
    root: Path | str = ".",
    runs_dir: Path | str | None = None,
    min_severity: str | None = None,
    include_legacy_runs: bool = False,
    limit: int | None = None,
) -> dict[str, Any]:
    root_path = Path(root)
    runs_path = Path(runs_dir) if runs_dir is not None else root_path / "runs"
    min_level = _normalize_min_severity(min_severity)

    run_records = []
    for manifest_path in _manifest_paths(runs_path):
        if not include_legacy_runs and not _run_has_trace(manifest_path, root=root_path):
            continue
        try:
            run_records.append(_build_run_record(manifest_path, root=root_path))
        except ValueError:
            run_records.append(_build_invalid_run_record(manifest_path, root=root_path))

    all_findings = sorted(
        (finding for run in run_records for finding in _diagnose_run(run, root_path)),
        key=lambda item: (
            -_severity_index(item.severity),
            item.run_id,
            item.finding_id,
        ),
    )

    findings = [
        _finding_to_payload(finding)
        for finding in all_findings
        if _severity_index(finding.severity) >= min_level
    ]
    if limit is not None:
        findings = findings[:limit]

    recommendations = _build_recommendations(findings)
    execution_control = _build_execution_control(findings)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "query": {
            "runs_dir": _display_path(runs_path, root_path),
            "min_severity": min_severity,
            "limit": limit,
            "include_legacy_runs": include_legacy_runs,
        },
        "summary": {
            "total_runs": len(run_records),
            "total_findings": len(findings),
            "high_findings": sum(1 for finding in findings if finding["severity"] == "high"),
            "medium_findings": sum(1 for finding in findings if finding["severity"] == "medium"),
            "low_findings": sum(1 for finding in findings if finding["severity"] == "low"),
            "runs_with_findings": len(set(finding["run_id"] for finding in findings)),
            "recommendations": len(recommendations),
        },
        "execution_control": execution_control,
        "findings": findings,
        "recommendations": recommendations,
    }
    return summary


def write_experience_diagnostics_report(payload: dict[str, Any], output: Path | str, report_format: str) -> None:
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if report_format == "html":
        output_path.write_text(render_experience_diagnostics_html(payload), encoding="utf-8")
    else:
        output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def render_experience_diagnostics_html(payload: dict[str, Any]) -> str:
    summary = payload.get("summary", {})
    findings = payload.get("findings", [])
    recommendations = payload.get("recommendations", [])
    finding_rows = [
        [
            finding.get("run_id", ""),
            finding.get("severity", ""),
            finding.get("id", ""),
            finding.get("title", ""),
            finding.get("reason", ""),
            ", ".join(finding.get("evidence_paths", [])),
            finding.get("recommendation_id", ""),
        ]
        for finding in findings
    ]
    recommendation_rows = [
        [
            recommendation.get("id", ""),
            recommendation.get("severity", ""),
            recommendation.get("confidence", ""),
            str(len(recommendation.get("run_ids", []))),
            ", ".join(recommendation.get("run_ids", [])),
            recommendation.get("suggested_next_action", ""),
        ]
        for recommendation in recommendations
    ]
    return render_html_document(
        title="CIPH Experience Diagnostics",
        heading="CIPH Experience Diagnostics",
        report_kind="experience-diagnostics",
        summary_items=[
            ("Runs", str(summary.get("total_runs", 0))),
            ("Findings", str(summary.get("total_findings", 0))),
            ("High", str(summary.get("high_findings", 0))),
            ("Medium", str(summary.get("medium_findings", 0))),
            ("Low", str(summary.get("low_findings", 0))),
            ("Recommendations", str(summary.get("recommendations", 0))),
            ("Runs with findings", str(summary.get("runs_with_findings", 0))),
        ],
        sections=[
            {
                "id": "execution-control",
                "title": "Execution Control",
                "items": [
                    f"Status: {payload.get('execution_control', {}).get('status', 'PASS')}",
                    f"High severity blocker count: {payload.get('execution_control', {}).get('high_severity_blocker_count', 0)}",
                    str(payload.get("execution_control", {}).get("message", "")),
                ],
            },
            {
                "id": "findings",
                "title": "Findings",
                "body_html": render_table(
                    [
                        "Run",
                        "Severity",
                        "Finding",
                        "Title",
                        "Reason",
                        "Evidence",
                        "Recommendation",
                    ],
                    finding_rows,
                ),
            },
            {
                "id": "recommendations",
                "title": "Recommendations",
                "body_html": render_table(
                    [
                        "ID",
                        "Severity",
                        "Confidence",
                        "Runs",
                        "Run IDs",
                        "Suggested Next Action",
                    ],
                    recommendation_rows,
                ),
            },
        ],
    )


def _build_run_record(manifest_path: Path, root: Path) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    run_dir = manifest_path.parent
    checks = manifest.get("checks", []) if isinstance(manifest.get("checks"), list) else []
    deliverables = manifest.get("deliverables", []) if isinstance(manifest.get("deliverables"), list) else []
    artifacts = manifest.get("artifacts", []) if isinstance(manifest.get("artifacts"), list) else []
    check_by_name = {
        str(check.get("name")): check for check in checks
        if isinstance(check, dict) and isinstance(check.get("name"), str)
    }

    trace_path = _resolve_trace_path(manifest, run_dir, root)
    events = _load_trace(trace_path)
    validation_by_name = {
        str(event.get("check_name")): str(event.get("status", ""))
        for event in events
        if event.get("event_type") == "validation.completed" and isinstance(event.get("check_name"), str)
    }
    stage_starts = {str(event.get("stage")) for event in events if event.get("event_type") == "stage.started" and isinstance(event.get("stage"), str)}
    stage_completions = {
        str(event.get("stage"))
        for event in events
        if event.get("event_type") == "stage.completed" and isinstance(event.get("stage"), str)
    }

    replay_receipts = _load_replay_receipts(run_dir, root)

    evaluation = _load_json_object(run_dir / "EVALUATION.json")
    has_evaluation_candidates = False
    if isinstance(evaluation, dict):
        candidates = evaluation.get("candidates")
        has_evaluation_candidates = isinstance(candidates, list) and len(candidates) > 0

    return {
        "run_id": str(manifest.get("task_id") or run_dir.name),
        "manifest_path": _display_path(manifest_path, root),
        "trace_path": _display_path(trace_path, root) if trace_path else None,
        "objective": str(manifest.get("objective") or ""),
        "closeout_status": _closeout_status(events),
        "event_count": len(events),
        "validation_by_name": validation_by_name,
        "event_types": sorted({str(event.get("event_type")) for event in events if isinstance(event.get("event_type"), str)}),
        "checks": checks,
        "required_check_names": sorted(name for name, check in check_by_name.items() if check.get("required") is True),
        "required_artifact_paths": sorted(
            str(artifact["path"]) for artifact in artifacts
            if isinstance(artifact, dict) and artifact.get("required") is True and isinstance(artifact.get("path"), str)
        ),
        "deliverable_artifact_paths": sorted(_manifest_paths_from_deliverables(deliverables, "artifact_paths")),
        "deliverable_evidence_paths": sorted(_manifest_paths_from_deliverables(deliverables, "evidence_paths")),
        "required_check_evidence_paths": sorted(
            str(check.get("evidence"))
            for check in checks
            if isinstance(check, dict)
            and check.get("required") is True
            and isinstance(check.get("evidence"), str)
        ),
        "replay_receipt_paths": [receipt["path"] for receipt in replay_receipts],
        "stage_starts": sorted(stage_starts),
        "stage_completions": sorted(stage_completions),
        "replay_receipts": replay_receipts,
        "evaluation_candidates": has_evaluation_candidates,
        "delivered": deliverables,
    }


def _build_invalid_run_record(manifest_path: Path, root: Path) -> dict[str, Any]:
    run_dir = manifest_path.parent
    return {
        "run_id": run_dir.name,
        "manifest_path": _display_path(manifest_path, root),
        "trace_path": None,
        "objective": "",
        "closeout_status": "UNKNOWN",
        "event_count": 0,
        "validation_by_name": {},
        "event_types": [],
        "checks": [],
        "required_check_names": [],
        "required_artifact_paths": [],
        "deliverable_artifact_paths": [],
        "deliverable_evidence_paths": [],
        "required_check_evidence_paths": [],
        "replay_receipt_paths": [],
        "stage_starts": [],
        "stage_completions": [],
        "replay_receipts": [],
        "evaluation_candidates": False,
        "delivered": [],
    }


def _diagnose_run(record: dict[str, Any], root: Path) -> list[_Finding]:
    run_id = str(record.get("run_id", ""))
    findings: list[_Finding] = []

    if not record.get("trace_path"):
        _append_finding(
            findings,
            _Finding(
                finding_id="trace-missing",
                severity="high",
                run_id=run_id,
                title="Missing trace ledger",
                reason="Trace path is missing from manifest or does not exist on disk.",
                evidence_paths=(str(record.get("manifest_path", "")),),
                recommendation_id="trace-contract",
            ),
        )
    elif int(record.get("event_count", 0)) == 0:
        _append_finding(
            findings,
            _Finding(
                finding_id="trace-empty",
                severity="medium",
                run_id=run_id,
                title="Trace ledger empty",
                reason="Trace file exists but contains no readable events.",
                evidence_paths=(str(record.get("trace_path") or record.get("manifest_path", "")),),
                recommendation_id="trace-contract",
            ),
        )

    if record.get("closeout_status") == "UNKNOWN":
        _append_finding(
            findings,
            _Finding(
                finding_id="closeout-missing",
                severity="high",
                run_id=run_id,
                title="Missing closeout status",
                reason="No closeout.completed event with PASS/FAIL status was recorded.",
                evidence_paths=(str(record.get("trace_path") or record.get("manifest_path", "")),),
                recommendation_id="closeout-contract",
            ),
        )

    required_checks = [str(name) for name in record.get("required_check_names", [])]
    validation_by_name = record.get("validation_by_name", {})
    for check_name in required_checks:
        if check_name not in validation_by_name:
            _append_finding(
                findings,
                _Finding(
                    finding_id="required-check-missing",
                    severity="medium",
                    run_id=run_id,
                    title="Required check not validated",
                    reason=f"Required check '{check_name}' has no validation.completed event.",
                    evidence_paths=(str(record.get("trace_path") or record.get("manifest_path", "")),),
                    recommendation_id="validation-coverage",
                ),
            )
        elif str(validation_by_name.get(check_name, "")).upper() != "PASS":
            _append_finding(
                findings,
                _Finding(
                    finding_id="required-check-failed",
                    severity="high",
                    run_id=run_id,
                    title="Required check did not pass",
                    reason=f"Required check '{check_name}' completed with status '{validation_by_name.get(check_name)}'.",
                    evidence_paths=(str(record.get("trace_path") or record.get("manifest_path", "")),),
                    recommendation_id="recover-check-failures",
                ),
            )

    missing_artifacts = _missing_local_paths(
        sorted(set(record.get("required_artifact_paths", []) + record.get("deliverable_artifact_paths", []))),
        root= root,
    )
    if missing_artifacts:
        _append_finding(
            findings,
            _Finding(
                finding_id="artifact-missing",
                severity="high",
                run_id=run_id,
                title="Missing required artifacts",
                reason="A required artifact path from the manifest or deliverables is not present on disk.",
                evidence_paths=tuple(missing_artifacts),
                recommendation_id="artifact-contract",
            ),
        )

    missing_evidence = _missing_local_paths(
        sorted(set(record.get("required_check_evidence_paths", []) + record.get("deliverable_evidence_paths", []))),
        root=root,
    )
    if missing_evidence:
        _append_finding(
            findings,
            _Finding(
                finding_id="evidence-missing",
                severity="medium",
                run_id=run_id,
                title="Missing evidence",
                reason="A required check or deliverable evidence path is not present on disk.",
                evidence_paths=tuple(missing_evidence),
                recommendation_id="evidence-contract",
            ),
        )

    started = set(record.get("stage_starts", []))
    completed = set(record.get("stage_completions", []))
    if started - completed:
        _append_finding(
            findings,
            _Finding(
                finding_id="stage-incomplete",
                severity="low",
                run_id=run_id,
                title="Started stage without completion",
                reason=f"Started but incomplete stages: {', '.join(sorted(started - completed))}.",
                evidence_paths=(str(record.get("trace_path") or record.get("manifest_path", "")),),
                recommendation_id="stage-coverage",
            ),
        )

    if record.get("evaluation_candidates") and not record.get("replay_receipts"):
        _append_finding(
            findings,
            _Finding(
                finding_id="evaluation-no-replay-receipts",
                severity="medium",
                run_id=run_id,
                title="Evaluation run lacks replay receipts",
                reason="EVALUATION.json exists with candidates but no replay receipts were found.",
                evidence_paths=(
                    str(record.get("manifest_path", "")),
                    f"{record.get('run_id')}/EVALUATION.json",
                ),
                recommendation_id="replay-readiness",
            ),
        )

    receipts = record.get("replay_receipts", [])
    if receipts:
        any_execute = any(receipt.get("mode") == "execute" for receipt in receipts if isinstance(receipt, dict))
        any_dry_run = any(receipt.get("mode") == "dry-run" for receipt in receipts if isinstance(receipt, dict))
        execute_pass = any(
            receipt.get("mode") == "execute" and str(receipt.get("status", "")).upper() == "PASS"
            for receipt in receipts
            if isinstance(receipt, dict)
        )

        if not any_execute and any_dry_run:
            _append_finding(
                findings,
                _Finding(
                    finding_id="replay-dry-run-only",
                    severity="low",
                    run_id=run_id,
                    title="Replay only executed in dry-run",
                    reason="Replay receipts exist, but none were generated in execute mode.",
                    evidence_paths=tuple(sorted(path for path in record.get("replay_receipt_paths", []))),
                    recommendation_id="replay-execution",
                ),
            )

        if any_execute and not execute_pass:
            _append_finding(
                findings,
                _Finding(
                    finding_id="replay-execute-no-pass",
                    severity="high",
                    run_id=run_id,
                    title="Executed replay has no PASS result",
                    reason="At least one execute-mode replay receipt was recorded, but none passed.",
                    evidence_paths=tuple(sorted(path for path in record.get("replay_receipt_paths", []))),
                    recommendation_id="replay-trust",
                ),
            )

    objective = str(record.get("objective", "")).lower()
    if "todo" in objective:
        _append_finding(
            findings,
            _Finding(
                finding_id="weak-contract",
                severity="low",
                run_id=run_id,
                title="Placeholder text in objective",
                reason="Run objective contains TODO-style placeholder text.",
                evidence_paths=(str(record.get("manifest_path", "")),),
                recommendation_id="harden-contract",
            ),
        )

    for deliverable in record.get("delivered", []):
        if not isinstance(deliverable, dict):
            continue
        requirement = str(deliverable.get("requirement", "")).lower()
        if "todo" in requirement:
            _append_finding(
                findings,
                _Finding(
                    finding_id="weak-contract",
                    severity="low",
                    run_id=run_id,
                    title="Placeholder text in deliverable",
                    reason="Deliverable requirement contains TODO-style placeholder text.",
                    evidence_paths=(str(record.get("manifest_path", "")),),
                    recommendation_id="harden-contract",
                )
            )
            break

    # Remove duplicate weak-contract findings per run to keep output stable.
    deduped = []
    seen = set()
    for finding in findings:
        key = (finding.finding_id, finding.run_id)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(finding)
    return deduped


def _build_recommendations(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not findings:
        return []

    recommendation_catalog: dict[str, tuple[str, str, str]] = {
        "trace-contract": ("high", "high", "Populate manifest.trace.path and write closeout-ready TRACE.jsonl with closeout.completed and validation events."),
        "closeout-contract": ("high", "high", "Emit a closeout.completed event with status PASS/FAIL for every run."),
        "validation-coverage": ("medium", "high", "Add validation.completed events for each required manifest check."),
        "artifact-contract": ("high", "high", "Produce required artifacts before required checks and closeout."),
        "evidence-contract": ("medium", "medium", "Write required evidence files and keep evidence path references valid."),
        "stage-coverage": ("low", "medium", "Emit stage.completed for every recorded stage.started."),
        "replay-readiness": ("medium", "high", "Generate replay receipts for evaluation candidates and include mode and status for each attempt."),
        "replay-execution": ("low", "medium", "Execute approved replay commands to collect execute-mode receipts."),
        "replay-trust": ("high", "high", "Address execute replay failures before reusing evaluation scores."),
        "harden-contract": ("low", "high", "Replace TODO placeholders with measurable acceptance wording."),
        "required-check-missing": ("medium", "high", "Run required checks and emit validation.completed events."),
        "required-check-failed": ("high", "high", "Recover and rerun failed required checks with corrected implementation/evidence."),
    }

    grouped: dict[str, list[str]] = {}
    for finding in findings:
        recommendation_id = finding.get("recommendation_id") or "general"
        grouped.setdefault(recommendation_id, []).append(finding.get("run_id", ""))

    recommendations: list[dict[str, Any]] = []
    for recommendation_id, run_ids in grouped.items():
        severity, confidence, action = recommendation_catalog.get(
            recommendation_id,
            ("low", "low", "Review and address the linked findings."),
        )
        recommendations.append(
            {
                "id": recommendation_id,
                "severity": severity,
                "confidence": confidence,
                "reason": next(
                    finding.get("reason", "")
                    for finding in findings
                    if finding.get("recommendation_id") == recommendation_id
                ),
                "run_ids": sorted(set(run_ids)),
                "suggested_next_action": action,
            }
        )

    recommendations.sort(
        key=lambda item: (
            _severity_index(item["severity"]),
            item["id"],
        ),
        reverse=True,
    )
    return recommendations


def _build_execution_control(findings: list[dict[str, Any]]) -> dict[str, Any]:
    high_findings = [finding for finding in findings if finding.get("severity") == "high"]
    if not high_findings:
        return {
            "status": "PASS",
            "high_severity_blocker_count": 0,
            "message": "No high-severity diagnostics findings are blocking execution.",
            "recommended_actions": [],
        }
    actions = sorted(
        {
            str(finding.get("recommendation_id"))
            for finding in high_findings
            if isinstance(finding.get("recommendation_id"), str) and finding.get("recommendation_id")
        }
    )
    return {
        "status": "BLOCKED",
        "high_severity_blocker_count": len(high_findings),
        "message": "High-severity diagnostics findings exist; closeout should remain blocked until they are resolved.",
        "recommended_actions": [
            {
                "recommendation_id": action,
                "command_hint": "rerun diagnose_experience_store.py after repairing the linked findings",
            }
            for action in actions
        ],
    }


def _missing_local_paths(paths: list[str], *, root: Path | None = None) -> list[str]:
    root_path = root if root is not None else Path(".")
    missing: list[str] = []
    for path in paths:
        if isinstance(path, str) and not path_exists(root_path, path):
            missing.append(path)
    return sorted(set(missing))


def _append_finding(findings: list[_Finding], finding: _Finding) -> None:
    findings.append(finding)


def _finding_to_payload(finding: _Finding) -> dict[str, Any]:
    return {
        "id": finding.finding_id,
        "severity": finding.severity,
        "run_id": finding.run_id,
        "title": finding.title,
        "reason": finding.reason,
        "evidence_paths": sorted(set(finding.evidence_paths)),
        "recommendation_id": finding.recommendation_id,
    }


def _build_replay_receipt_path(root: Path, receipt_path: Path) -> str:
    try:
        return str(receipt_path.relative_to(root))
    except ValueError:
        return receipt_path.as_posix()


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
        payload = dict(payload)
        payload["path"] = _build_replay_receipt_path(root, receipt_path)
        payload.setdefault("mode", "unknown")
        payload.setdefault("status", "UNKNOWN")
        receipts.append(payload)
    return receipts


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


def _closeout_status(events: list[dict[str, Any]]) -> str:
    for event in reversed(events):
        if event.get("event_type") == "closeout.completed":
            status = event.get("status")
            return str(status).upper() if isinstance(status, str) and status else "UNKNOWN"
    return "UNKNOWN"


def _resolve_trace_path(manifest: dict[str, Any], run_dir: Path, root: Path) -> Path | None:
    trace = manifest.get("trace")
    if isinstance(trace, dict) and isinstance(trace.get("path"), str):
        candidate = root / trace["path"]
        return candidate if candidate.is_file() else None
    candidate = run_dir / "TRACE.jsonl"
    return candidate if candidate.is_file() else None


def _load_json_object(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _manifest_paths(runs_path: Path) -> list[Path]:
    if not runs_path.exists():
        return []
    return sorted(path for path in runs_path.glob("*/MANIFEST.json") if path.is_file())


def _run_has_trace(manifest_path: Path, root: Path) -> bool:
    try:
        manifest = load_manifest(manifest_path)
    except ValueError:
        return False
    trace_path = _resolve_trace_path(manifest, manifest_path.parent, root)
    return trace_path is not None and trace_path.is_file()


def _manifest_paths_from_deliverables(deliverables: list[Any], key: str) -> list[str]:
    paths: list[str] = []
    for deliverable in deliverables:
        if not isinstance(deliverable, dict):
            continue
        values = deliverable.get(key, [])
        if isinstance(values, list):
            paths.extend(value for value in values if isinstance(value, str))
    return paths


def _normalize_min_severity(min_severity: str | None) -> int:
    if min_severity is None:
        return 0
    severity = min_severity.lower()
    if severity not in SEVERITY_ORDER:
        raise ValueError(f"min-severity must be one of: {', '.join(SEVERITY_ORDER)}")
    return SEVERITY_ORDER.index(severity)


def _severity_index(severity: str) -> int:
    return SEVERITY_ORDER.index(severity) if severity in SEVERITY_ORDER else 0


def _display_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Diagnose CIPH experience store records.")
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root")
    parser.add_argument("--runs-dir", type=Path, default=None, help="Runs directory; defaults to <root>/runs")
    parser.add_argument(
        "--include-legacy-runs",
        action="store_true",
        help="Include historical runs that do not have a TRACE.jsonl file in diagnostics",
    )
    parser.add_argument("--min-severity", choices=SEVERITY_ORDER, default="low", help="Minimum severity for emitted findings")
    parser.add_argument("--limit", type=int, default=None, help="Maximum findings in output")
    parser.add_argument("--format", choices=["json", "html"], default="json", help="Output format")
    parser.add_argument("--output", type=Path, default=None, help="Write report to this path")
    parser.add_argument("--fail-on-high", action="store_true", help="Return non-zero when high-severity findings are present")
    args = parser.parse_args(argv)

    if args.limit is not None and args.limit < 1:
        print("ERROR: --limit must be positive")
        return 1

    payload = diagnose_experience_store(
        root=args.root,
        runs_dir=args.runs_dir,
        min_severity=args.min_severity,
        include_legacy_runs=args.include_legacy_runs,
        limit=args.limit,
    )

    if args.output is not None:
        write_experience_diagnostics_report(payload, args.output, args.format)
        print(f"Wrote CIPH experience diagnostics: {args.output}")
        if args.fail_on_high and payload.get("summary", {}).get("high_findings", 0) > 0:
            print(payload["execution_control"]["message"])
            return 2
        return 0

    if args.format == "html":
        print(render_experience_diagnostics_html(payload), end="")
    else:
        print(json.dumps(payload, sort_keys=True, indent=2))
    if args.fail_on_high and payload.get("summary", {}).get("high_findings", 0) > 0:
        print(payload["execution_control"]["message"])
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
