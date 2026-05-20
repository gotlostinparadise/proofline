#!/usr/bin/env python3
"""Plan next CIPH candidate stubs from diagnostics output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts.html_report import render_html_document, render_table
except ModuleNotFoundError:  # pragma: no cover - exercised by direct script execution.
    from html_report import render_html_document, render_table


SCHEMA_VERSION = "ciph.next-candidate-plan.v1"


def plan_next_candidates(
    diagnostics_path: Path | str,
    *,
    frontier_context: Path | str | None = None,
    limit: int = 3,
) -> dict[str, Any]:
    diagnostics = _load_json_object(Path(diagnostics_path))
    findings = diagnostics.get("findings", []) if isinstance(diagnostics.get("findings"), list) else []
    recommendations = diagnostics.get("recommendations", []) if isinstance(diagnostics.get("recommendations"), list) else []
    frontier = _load_json_object(Path(frontier_context)) if frontier_context is not None else {}

    ranked = sorted(
        recommendations,
        key=lambda item: (_severity_rank(str(item.get("severity", ""))), str(item.get("id", ""))),
        reverse=True,
    )
    candidates = []
    for index, recommendation in enumerate(ranked[:limit], start=1):
        recommendation_id = str(recommendation.get("id") or f"recommendation-{index}")
        changed_module, changed_class = _module_for_recommendation(recommendation_id)
        candidates.append(
            {
                "candidate_id": f"next-{index}-{_slugify(recommendation_id)}",
                "changed_module": changed_module,
                "changed_class": changed_class,
                "rationale": str(recommendation.get("suggested_next_action") or recommendation.get("reason") or ""),
                "source_recommendation_id": recommendation_id,
                "affected_run_ids": recommendation.get("run_ids", []),
            }
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "diagnostics_path": str(diagnostics_path),
        "frontier_context_path": str(frontier_context) if frontier_context is not None else None,
        "summary": {
            "diagnostic_findings": len(findings),
            "recommendations_considered": len(ranked),
            "candidate_stubs": len(candidates),
            "frontier_candidate_ids": _frontier_ids(frontier),
        },
        "candidate_stubs": candidates,
    }


def write_next_candidate_plan(payload: dict[str, Any], output: Path | str, report_format: str) -> None:
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if report_format == "html":
        output_path.write_text(render_next_candidate_plan_html(payload), encoding="utf-8")
    else:
        output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def render_next_candidate_plan_html(payload: dict[str, Any]) -> str:
    summary = payload.get("summary", {})
    rows = [
        [
            candidate.get("candidate_id", ""),
            candidate.get("changed_class", ""),
            candidate.get("changed_module", ""),
            candidate.get("source_recommendation_id", ""),
            candidate.get("rationale", ""),
        ]
        for candidate in payload.get("candidate_stubs", [])
        if isinstance(candidate, dict)
    ]
    return render_html_document(
        title="CIPH Next Candidate Plan",
        heading="CIPH Next Candidate Plan",
        report_kind="next-candidate-plan",
        summary_items=[
            ("Findings", str(summary.get("diagnostic_findings", 0))),
            ("Recommendations", str(summary.get("recommendations_considered", 0))),
            ("Candidate Stubs", str(summary.get("candidate_stubs", 0))),
        ],
        sections=[
            {
                "id": "candidate-stubs",
                "title": "Candidate Stubs",
                "body_html": render_table(
                    ["Candidate", "Changed Class", "Changed Module", "Recommendation", "Rationale"],
                    rows,
                ),
            }
        ],
    )


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to read JSON object from {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"JSON must contain an object: {path}")
    return payload


def _module_for_recommendation(recommendation_id: str) -> tuple[str, str]:
    if "trace" in recommendation_id or "stage" in recommendation_id:
        return "state", "policy"
    if "validation" in recommendation_id or "check" in recommendation_id:
        return "verification", "policy"
    if "replay" in recommendation_id:
        return "candidate-search", "evaluator"
    if "artifact" in recommendation_id or "evidence" in recommendation_id:
        return "context", "policy"
    return "candidate-search", "policy"


def _frontier_ids(frontier: dict[str, Any]) -> list[str]:
    ids = frontier.get("frontier_candidate_ids")
    return [item for item in ids if isinstance(item, str)] if isinstance(ids, list) else []


def _severity_rank(severity: str) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(severity, 0)


def _slugify(value: str) -> str:
    chars = [char.lower() if char.isalnum() else "-" for char in value]
    slug = "-".join(part for part in "".join(chars).split("-") if part)
    return slug or "candidate"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan next CIPH candidate stubs from diagnostics output.")
    parser.add_argument("diagnostics", type=Path, help="Path to experience diagnostics JSON")
    parser.add_argument("--frontier-context", type=Path, default=None, help="Optional EVALUATION.json or frontier context JSON")
    parser.add_argument("--limit", type=int, default=3, help="Maximum candidate stubs to emit")
    parser.add_argument("--format", choices=["json", "html"], default="json", help="Output format")
    parser.add_argument("--output", type=Path, default=None, help="Write report to this path")
    args = parser.parse_args(argv)

    if args.limit < 1:
        print("ERROR: --limit must be positive")
        return 1
    try:
        payload = plan_next_candidates(args.diagnostics, frontier_context=args.frontier_context, limit=args.limit)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    if args.output is not None:
        write_next_candidate_plan(payload, args.output, args.format)
        print(f"Wrote CIPH next candidate plan: {args.output}")
    elif args.format == "html":
        print(render_next_candidate_plan_html(payload), end="")
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
