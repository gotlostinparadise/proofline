#!/usr/bin/env python3
"""Summarize CIPH candidate scores and Pareto frontier status."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


MAXIMIZE = ["task_success", "audit_completeness"]
MINIMIZE = ["cost_tokens", "wall_minutes", "defect_escape_rate"]


def render_candidate_summary(run_dir: Path | str) -> str:
    run_path = Path(run_dir)
    candidates = _load_candidates(run_path)
    statuses = _pareto_statuses(candidates)
    lines = [
        "# CIPH Candidate Summary",
        "",
        f"Run: {run_path}",
        "",
        "| Candidate | Pareto | Task Success | Audit | Cost Tokens | Wall Minutes | Defect Escape |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for candidate in sorted(candidates, key=lambda item: str(item.get("candidate_id", ""))):
        candidate_id = str(candidate.get("candidate_id", "<missing>"))
        scores = candidate.get("search_scores", {})
        if not isinstance(scores, dict):
            scores = {}
        lines.append(
            "| "
            + " | ".join(
                [
                    candidate_id,
                    statuses.get(candidate_id, "unscored"),
                    _fmt(scores.get("task_success")),
                    _fmt(scores.get("audit_completeness")),
                    _fmt(scores.get("cost_tokens")),
                    _fmt(scores.get("wall_minutes")),
                    _fmt(scores.get("defect_escape_rate")),
                ]
            )
            + " |"
        )
    if not candidates:
        lines.append("| None | unscored | - | - | - | - | - |")
    return "\n".join(lines) + "\n"


def write_candidate_summary(run_dir: Path | str, output_path: Path | str) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_candidate_summary(run_dir), encoding="utf-8")
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
