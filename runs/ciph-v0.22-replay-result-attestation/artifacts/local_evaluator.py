#!/usr/bin/env python3
"""Dogfood local evaluator for CIPH v0.22 replay receipt attestation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


RUN_ID = "ciph-v0.22-replay-result-attestation"


def _score_payload() -> dict[str, object]:
    return {
        "schema_version": "ciph.candidate.v1",
        "candidate_id": "frontier",
        "search_scores": {
            "task_success": 0.98,
            "audit_completeness": 0.97,
            "cost_tokens": 85,
            "wall_minutes": 2,
            "defect_escape_rate": 0.0,
        },
        "score_provenance": {
            "schema_version": "ciph.score-provenance.v1",
            "evaluator_id": "search-evaluator",
            "evaluator_manifest_path": f"runs/{RUN_ID}/evaluators/search-evaluator.json",
            "evaluation_phase": "search",
            "produced_at": "2026-05-20T12:30:00Z",
            "input_paths": [f"runs/{RUN_ID}/artifacts/search-input.json"],
            "evidence_paths": [f"runs/{RUN_ID}/artifacts/search-evidence.txt"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Write deterministic CIPH v0.22 dogfood score output.")
    parser.add_argument("--output", required=True, help="Score output path")
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(_score_payload(), indent=2) + "\n", encoding="utf-8")
    print("local evaluator output written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
