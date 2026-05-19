#!/usr/bin/env python3
"""Summarize CIPH candidate scores and Pareto frontier status."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts.html_report import render_html_document, render_table
except ModuleNotFoundError:  # pragma: no cover - exercised by direct script execution.
    from html_report import render_html_document, render_table


MAXIMIZE = ["task_success", "audit_completeness"]
MINIMIZE = ["cost_tokens", "wall_minutes", "defect_escape_rate"]
MECHANISM_METRICS = [
    ("artifact_contract_compliance", "Artifact Contract"),
    ("stage_coverage", "Stage Coverage"),
    ("ordered_workflow_compliance", "Ordered Workflow"),
    ("tool_call_success", "Tool Success"),
    ("handoff_recall", "Handoff Recall"),
    ("validation_coverage", "Validation Coverage"),
]


def render_candidate_summary(run_dir: Path | str) -> str:
    run_path = Path(run_dir)
    candidates = _load_candidates(run_path)
    statuses = _pareto_statuses(candidates)
    evaluation = _evaluation_statuses(run_path)
    lines = [
        "# CIPH Candidate Summary",
        "",
        f"Run: {run_path}",
        "",
        "| Candidate | Pareto | Eval Phase | Holdout | Task Success | Audit | Cost Tokens | Wall Minutes | Defect Escape | Artifact Contract | Stage Coverage | Ordered Workflow | Tool Success | Handoff Recall | Validation Coverage |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for candidate in sorted(candidates, key=lambda item: str(item.get("candidate_id", ""))):
        candidate_id = str(candidate.get("candidate_id", "<missing>"))
        eval_phase, holdout_status = evaluation.get(candidate_id, ("-", "-"))
        scores = candidate.get("search_scores", {})
        if not isinstance(scores, dict):
            scores = {}
        mechanism = candidate.get("mechanism_metrics", {})
        if not isinstance(mechanism, dict):
            mechanism = {}
        lines.append(
            "| "
            + " | ".join(
                [
                    candidate_id,
                    statuses.get(candidate_id, "unscored"),
                    eval_phase,
                    holdout_status,
                    _fmt(scores.get("task_success")),
                    _fmt(scores.get("audit_completeness")),
                    _fmt(scores.get("cost_tokens")),
                    _fmt(scores.get("wall_minutes")),
                    _fmt(scores.get("defect_escape_rate")),
                    *[_fmt(mechanism.get(key)) for key, _label in MECHANISM_METRICS],
                ]
            )
            + " |"
        )
    if not candidates:
        lines.append("| None | unscored | - | - | - | - | - | - | - | - | - | - | - | - | - |")
    return "\n".join(lines) + "\n"


def render_candidate_summary_html(run_dir: Path | str) -> str:
    run_path = Path(run_dir)
    candidates = _load_candidates(run_path)
    statuses = _pareto_statuses(candidates)
    evaluation = _evaluation_statuses(run_path)
    rows: list[list[str]] = []
    for candidate in sorted(candidates, key=lambda item: str(item.get("candidate_id", ""))):
        candidate_id = str(candidate.get("candidate_id", "<missing>"))
        eval_phase, holdout_status = evaluation.get(candidate_id, ("-", "-"))
        scores = candidate.get("search_scores", {})
        if not isinstance(scores, dict):
            scores = {}
        mechanism = candidate.get("mechanism_metrics", {})
        if not isinstance(mechanism, dict):
            mechanism = {}
        rows.append(
            [
                candidate_id,
                statuses.get(candidate_id, "unscored"),
                eval_phase,
                holdout_status,
                _fmt(scores.get("task_success")),
                _fmt(scores.get("audit_completeness")),
                _fmt(scores.get("cost_tokens")),
                _fmt(scores.get("wall_minutes")),
                _fmt(scores.get("defect_escape_rate")),
                *[_fmt(mechanism.get(key)) for key, _label in MECHANISM_METRICS],
            ]
        )
    if not rows:
        rows.append(["None", "unscored", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-"])

    return render_html_document(
        title="CIPH Candidate Summary",
        heading="CIPH Candidate Summary",
        report_kind="candidate-summary",
        summary_items=[("Run", str(run_path)), ("Candidates", str(len(candidates)))],
        sections=[
            {
                "id": "scores",
                "title": "Candidate Scores",
                "body_html": render_table(
                    [
                        "Candidate",
                        "Pareto",
                        "Eval Phase",
                        "Holdout",
                        "Task Success",
                        "Audit",
                        "Cost Tokens",
                        "Wall Minutes",
                        "Defect Escape",
                        *[label for _key, label in MECHANISM_METRICS],
                    ],
                    rows,
                ),
            }
        ],
    )


def write_candidate_summary(run_dir: Path | str, output_path: Path | str) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    rendered = render_candidate_summary_html(run_dir) if output.suffix == ".html" else render_candidate_summary(run_dir)
    output.write_text(rendered, encoding="utf-8")
    return output


def _load_candidates(run_path: Path) -> list[dict[str, Any]]:
    candidate_root = run_path / "candidates"
    if not candidate_root.is_dir():
        return []
    candidates: list[dict[str, Any]] = []
    for score_path in sorted(candidate_root.glob("*/score.json")):
        with score_path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, dict):
            candidates.append(payload)
    return candidates


def _evaluation_statuses(run_path: Path) -> dict[str, tuple[str, str]]:
    evaluation_path = run_path / "EVALUATION.json"
    if not evaluation_path.is_file():
        return {}
    try:
        payload = json.loads(evaluation_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}

    phase = payload.get("phase")
    holdout_set = payload.get("holdout_set")
    holdout_sealed = isinstance(holdout_set, dict) and holdout_set.get("sealed") is True
    frontier_ids = set(_string_list(payload.get("frontier_candidate_ids")))
    statuses: dict[str, tuple[str, str]] = {}
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        return {}

    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        candidate_id = candidate.get("candidate_id")
        if not isinstance(candidate_id, str) or not candidate_id.strip():
            continue
        eval_phase = candidate.get("evaluation_phase")
        if not isinstance(eval_phase, str) or not eval_phase.strip():
            eval_phase = "-"
        holdout_score_path = candidate.get("holdout_score_path")
        if isinstance(holdout_score_path, str) and holdout_score_path.strip():
            holdout = "released"
        elif phase == "holdout_released" and candidate_id in frontier_ids:
            holdout = "released"
        elif holdout_sealed:
            holdout = "sealed"
        else:
            holdout = "-"
        statuses[candidate_id] = (eval_phase, holdout)
    return statuses


def _pareto_statuses(candidates: list[dict[str, Any]]) -> dict[str, str]:
    statuses: dict[str, str] = {}
    scored = [candidate for candidate in candidates if _is_scored(candidate)]
    for candidate in candidates:
        candidate_id = str(candidate.get("candidate_id", "<missing>"))
        if candidate not in scored:
            statuses[candidate_id] = "unscored"
            continue
        statuses[candidate_id] = "dominated" if any(_dominates(other, candidate) for other in scored if other is not candidate) else "frontier"
    return statuses


def _is_scored(candidate: dict[str, Any]) -> bool:
    scores = candidate.get("search_scores", {})
    if not isinstance(scores, dict):
        return False
    return all(isinstance(scores.get(key), (int, float)) for key in [*MAXIMIZE, *MINIMIZE])


def _dominates(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_scores = left["search_scores"]
    right_scores = right["search_scores"]
    at_least_equal = all(left_scores[key] >= right_scores[key] for key in MAXIMIZE)
    at_most_equal = all(left_scores[key] <= right_scores[key] for key in MINIMIZE)
    strictly_better = any(left_scores[key] > right_scores[key] for key in MAXIMIZE) or any(
        left_scores[key] < right_scores[key] for key in MINIMIZE
    )
    return at_least_equal and at_most_equal and strictly_better


def _fmt(value: Any) -> str:
    if value is None:
        return "-"
    return str(value)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize CIPH candidate scores.")
    parser.add_argument("run_dir", type=Path, help="Path to run directory")
    parser.add_argument("--output", type=Path, default=None, help="Write summary to this path")
    args = parser.parse_args(argv)

    if args.output is not None:
        path = write_candidate_summary(args.run_dir, args.output)
        print(f"Wrote CIPH candidate summary: {path}")
    else:
        print(render_candidate_summary(args.run_dir), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
