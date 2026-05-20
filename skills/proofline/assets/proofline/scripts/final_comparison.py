#!/usr/bin/env python3
"""Render final CIPH search-versus-holdout comparisons."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from scripts.html_report import render_html_document, render_table
    from scripts.validate_evaluation import validate_evaluation
except ModuleNotFoundError:  # pragma: no cover - exercised by direct script execution.
    from html_report import render_html_document, render_table
    from validate_evaluation import validate_evaluation


@dataclass(frozen=True)
class ComparisonRow:
    candidate_id: str
    status: str
    search_task_success: float
    holdout_task_success: float
    generalization_delta: float
    search_audit_completeness: float
    holdout_audit_completeness: float
    holdout_defect_escape_rate: float


@dataclass
class FinalComparisonResult:
    rows: list[ComparisonRow] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)
    winner_candidate_id: str | None = None

    @property
    def ok(self) -> bool:
        return not self.errors


def compare_final_results(run_dir: Path | str, root: Path | str = ".") -> FinalComparisonResult:
    run_path = Path(run_dir)
    root_path = Path(root)
    result = FinalComparisonResult()

    validation = validate_evaluation(run_path, root=root_path)
    if not validation.ok:
        result.errors.extend(f"evaluation {error}" for error in validation.errors)
        return result

    evaluation = _load_json_object(run_path / "EVALUATION.json", result, "EVALUATION.json")
    if evaluation is None:
        return result
    if evaluation.get("phase") != "holdout_released":
        result.errors.append("phase must be holdout_released before final comparison")
        return result

    frontier_ids = _string_list(evaluation.get("frontier_candidate_ids"))
    if not frontier_ids:
        result.errors.append("frontier_candidate_ids must contain at least one candidate")
        return result

    candidates = _candidate_records(evaluation)
    raw_rows: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    for candidate_id in frontier_ids:
        candidate = candidates.get(candidate_id)
        if candidate is None:
            result.errors.append(f"frontier candidate must be listed: {candidate_id}")
            continue
        holdout_score_path = candidate.get("holdout_score_path")
        if not _non_empty_string(holdout_score_path):
            result.errors.append(f"candidate {candidate_id} is missing holdout_score_path")
            continue
        search_score_path = candidate.get("score_path")
        if not _non_empty_string(search_score_path):
            result.errors.append(f"candidate {candidate_id} is missing score_path")
            continue

        search_score = _load_json_object(root_path / str(search_score_path), result, str(search_score_path))
        holdout_score = _load_json_object(root_path / str(holdout_score_path), result, str(holdout_score_path))
        if search_score is None or holdout_score is None:
            continue
        raw_rows.append((candidate_id, search_score, holdout_score))

    if result.errors:
        return result
    if not raw_rows:
        result.errors.append("no candidates with holdout scores are available for final comparison")
        return result

    winner_id = sorted(
        raw_rows,
        key=lambda row: (-_metric(row[2], "holdout_scores", "task_success"), row[0]),
    )[0][0]
    result.winner_candidate_id = winner_id
    for candidate_id, search_score, holdout_score in sorted(raw_rows, key=lambda row: row[0]):
        search_task_success = _metric(search_score, "search_scores", "task_success")
        holdout_task_success = _metric(holdout_score, "holdout_scores", "task_success")
        result.rows.append(
            ComparisonRow(
                candidate_id=candidate_id,
                status="winner" if candidate_id == winner_id else "finalist",
                search_task_success=search_task_success,
                holdout_task_success=holdout_task_success,
                generalization_delta=round(holdout_task_success - search_task_success, 6),
                search_audit_completeness=_metric(search_score, "search_scores", "audit_completeness"),
                holdout_audit_completeness=_metric(holdout_score, "holdout_scores", "audit_completeness"),
                holdout_defect_escape_rate=_metric(holdout_score, "holdout_scores", "defect_escape_rate"),
            )
        )
    result.messages.append(f"PASS final winner {winner_id}")
    return result


def render_final_comparison(run_dir: Path | str, result: FinalComparisonResult) -> str:
    status = "PASS" if result.ok else "FAIL"
    lines = [
        "# CIPH Final Comparison",
        "",
        f"Run: {run_dir}",
        f"Status: {status}",
        f"Winner: {result.winner_candidate_id or '-'}",
        "",
        "| Candidate | Final Status | Search Task Success | Holdout Task Success | Generalization Delta | Search Audit | Holdout Audit | Holdout Defect Escape |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in result.rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    row.candidate_id,
                    row.status,
                    _fmt(row.search_task_success),
                    _fmt(row.holdout_task_success),
                    _fmt(row.generalization_delta),
                    _fmt(row.search_audit_completeness),
                    _fmt(row.holdout_audit_completeness),
                    _fmt(row.holdout_defect_escape_rate),
                ]
            )
            + " |"
        )
    if not result.rows:
        lines.append("| None | - | - | - | - | - | - | - |")
    if result.errors:
        lines.extend(["", "## Errors", *[f"- {error}" for error in result.errors]])
    return "\n".join(lines) + "\n"


def render_final_comparison_html(run_dir: Path | str, result: FinalComparisonResult) -> str:
    status = "PASS" if result.ok else "FAIL"
    rows = [
        [
            row.candidate_id,
            row.status,
            _fmt(row.search_task_success),
            _fmt(row.holdout_task_success),
            _fmt(row.generalization_delta),
            _fmt(row.search_audit_completeness),
            _fmt(row.holdout_audit_completeness),
            _fmt(row.holdout_defect_escape_rate),
        ]
        for row in result.rows
    ]
    if not rows:
        rows.append(["None", "-", "-", "-", "-", "-", "-", "-"])
    return render_html_document(
        title="CIPH Final Comparison",
        heading="CIPH Final Comparison",
        report_kind="final-comparison",
        summary_items=[
            ("Run", str(run_dir)),
            ("Status", status),
            ("Winner", result.winner_candidate_id or "-"),
            ("Errors", str(len(result.errors))),
        ],
        sections=[
            {
                "id": "scores",
                "title": "Search vs Holdout",
                "body_html": render_table(
                    [
                        "Candidate",
                        "Final Status",
                        "Search Task Success",
                        "Holdout Task Success",
                        "Generalization Delta",
                        "Search Audit",
                        "Holdout Audit",
                        "Holdout Defect Escape",
                    ],
                    rows,
                ),
            },
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


def write_final_comparison(run_dir: Path | str, output_path: Path | str, root: Path | str = ".") -> Path:
    result = compare_final_results(run_dir, root=root)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix == ".html":
        output.write_text(render_final_comparison_html(run_dir, result), encoding="utf-8")
    else:
        output.write_text(render_final_comparison(run_dir, result), encoding="utf-8")
    return output


def _candidate_records(evaluation: dict[str, Any]) -> dict[str, dict[str, Any]]:
    candidates = evaluation.get("candidates")
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


def _metric(payload: dict[str, Any], group: str, metric: str) -> float:
    scores = payload.get(group)
    if not isinstance(scores, dict):
        return 0.0
    value = scores.get(metric)
    return float(value) if isinstance(value, (int, float)) else 0.0


def _load_json_object(path: Path, result: FinalComparisonResult, label: str) -> dict[str, Any] | None:
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


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _fmt(value: float) -> str:
    return f"{value:.6g}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render final CIPH search-versus-holdout comparison.")
    parser.add_argument("run_dir", type=Path, help="Path to run directory")
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root for score path references")
    parser.add_argument("--output", type=Path, default=None, help="Write comparison report to this path")
    args = parser.parse_args(argv)

    result = compare_final_results(args.run_dir, root=args.root)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if args.output.suffix == ".html":
            args.output.write_text(render_final_comparison_html(args.run_dir, result), encoding="utf-8")
        else:
            args.output.write_text(render_final_comparison(args.run_dir, result), encoding="utf-8")
        print(f"Wrote CIPH final comparison: {args.output}")

    status = "PASS" if result.ok else "FAIL"
    print(f"{status} final comparison {args.run_dir}")
    print(render_final_comparison(args.run_dir, result), end="")
    for error in result.errors:
        print(f"ERROR {error}", file=sys.stderr)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
