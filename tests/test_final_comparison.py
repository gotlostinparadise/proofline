import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.final_comparison import compare_final_results, render_final_comparison, write_final_comparison


class FinalComparisonTests(unittest.TestCase):
    def test_render_final_comparison_reports_holdout_winner_and_generalization_delta(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_run(root)
            _write_search_score(run_dir, "baseline", task_success=0.80)
            _write_search_score(run_dir, "frontier-a", task_success=0.92)
            _write_search_score(run_dir, "frontier-b", task_success=0.91)
            _write_holdout_score(run_dir, "frontier-a", task_success=0.88)
            _write_holdout_score(run_dir, "frontier-b", task_success=0.94)
            _write_evaluation(run_dir, ["frontier-a", "frontier-b"])

            result = compare_final_results(run_dir, root=root)
            output = render_final_comparison(run_dir, result)

            self.assertTrue(result.ok, result.errors)
            self.assertEqual(result.winner_candidate_id, "frontier-b")
            self.assertIn("# CIPH Final Comparison", output)
            self.assertIn("| frontier-b | winner | 0.91 | 0.94 | 0.03 |", output)
            self.assertIn("| frontier-a | finalist | 0.92 | 0.88 | -0.04 |", output)

    def test_render_final_comparison_includes_score_provenance_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_run(root)
            _write_search_score(run_dir, "frontier", task_success=0.92, evaluator_id="search-evaluator")
            _write_holdout_score(run_dir, "frontier", task_success=0.94, evaluator_id="holdout-evaluator")
            _write_evaluation(run_dir, ["frontier"])

            result = compare_final_results(run_dir, root=root)
            output = render_final_comparison(run_dir, result)

            self.assertTrue(result.ok, result.errors)
            self.assertIn("Search Evaluator", output)
            self.assertIn("Holdout Evaluator", output)
            self.assertIn("| frontier | winner | 0.92 | 0.94 | 0.02 | 0.9 | 0.91 | 0.01 | search-evaluator | holdout-evaluator |", output)

    def test_compare_final_results_breaks_holdout_score_ties_by_candidate_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_run(root)
            _write_search_score(run_dir, "frontier-a", task_success=0.92)
            _write_search_score(run_dir, "frontier-b", task_success=0.91)
            _write_holdout_score(run_dir, "frontier-a", task_success=0.90)
            _write_holdout_score(run_dir, "frontier-b", task_success=0.90)
            _write_evaluation(run_dir, ["frontier-b", "frontier-a"])

            result = compare_final_results(run_dir, root=root)

            self.assertTrue(result.ok, result.errors)
            self.assertEqual(result.winner_candidate_id, "frontier-a")

    def test_compare_final_results_rejects_missing_holdout_scores(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_run(root)
            _write_search_score(run_dir, "frontier", task_success=0.92)
            _write_evaluation(run_dir, ["frontier"], include_holdout_path=False)

            result = compare_final_results(run_dir, root=root)

            self.assertFalse(result.ok)
            self.assertIn("candidate frontier is missing holdout_score_path", result.errors)

    def test_write_final_comparison_creates_html_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_run(root)
            output_path = run_dir / "artifacts" / "final-comparison.html"
            _write_search_score(run_dir, "frontier", task_success=0.92)
            _write_holdout_score(run_dir, "frontier", task_success=0.94)
            _write_evaluation(run_dir, ["frontier"])

            write_final_comparison(run_dir, output_path, root=root)

            html = output_path.read_text(encoding="utf-8")
            self.assertTrue(html.startswith("<!doctype html>"))
            self.assertIn('data-proofline-report="final-comparison"', html)
            self.assertIn("frontier", html)
            self.assertIn("winner", html)

    def test_final_comparison_script_runs_when_executed_by_file_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_run(root)
            output_path = run_dir / "artifacts" / "final-comparison.html"
            _write_search_score(run_dir, "frontier", task_success=0.92)
            _write_holdout_score(run_dir, "frontier", task_success=0.94)
            _write_evaluation(run_dir, ["frontier"])
            repo_root = Path(__file__).resolve().parents[1]

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/final_comparison.py",
                    str(run_dir),
                    "--root",
                    str(root),
                    "--output",
                    str(output_path),
                ],
                cwd=repo_root,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn(f"PASS final comparison {run_dir}", completed.stdout)
            self.assertTrue(output_path.is_file())


def _create_run(root: Path) -> Path:
    run_dir = root / "runs" / "sample"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _write_search_score(run_dir: Path, candidate_id: str, *, task_success: float, evaluator_id: str | None = None) -> None:
    candidate_dir = run_dir / "candidates" / candidate_id
    candidate_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "ciph.candidate.v1",
        "candidate_id": candidate_id,
        "hypothesis": f"Candidate {candidate_id}.",
        "parent_ids": [],
        "lineage": {"parents": [], "generation": 0},
        "changed_modules": [],
        "search_scores": {
            "task_success": task_success,
            "audit_completeness": 0.90,
            "cost_tokens": 100,
            "wall_minutes": 2,
            "defect_escape_rate": 0.02,
        },
        "candidate_trace": f"runs/sample/candidates/{candidate_id}/TRACE.jsonl",
        "trace_paths": [],
        "artifact_paths": [],
        "mechanism_metrics": {},
        "pareto_status": "unscored",
    }
    if evaluator_id is not None:
        payload["score_provenance"] = {"evaluator_id": evaluator_id}
    candidate_dir.joinpath("score.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_holdout_score(run_dir: Path, candidate_id: str, *, task_success: float, evaluator_id: str | None = None) -> None:
    score_dir = run_dir / "holdout_scores"
    score_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "ciph.holdout-score.v1",
        "candidate_id": candidate_id,
        "release_index": 1,
        "scored_at": "2026-05-20T05:00:00Z",
        "scenario_ids": ["holdout-1"],
        "holdout_scores": {
            "task_success": task_success,
            "audit_completeness": 0.91,
            "cost_tokens": 120,
            "wall_minutes": 3,
            "defect_escape_rate": 0.01,
        },
    }
    if evaluator_id is not None:
        payload["score_provenance"] = {"evaluator_id": evaluator_id}
    score_dir.joinpath(f"{candidate_id}.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_evaluation(run_dir: Path, frontier_ids: list[str], *, include_holdout_path: bool = True) -> None:
    run_id = run_dir.name
    candidates = []
    for candidate_id in sorted(frontier_ids):
        candidate = {
            "candidate_id": candidate_id,
            "role": "frontier",
            "evaluation_phase": "holdout" if include_holdout_path else "search",
            "score_path": f"runs/{run_id}/candidates/{candidate_id}/score.json",
        }
        if include_holdout_path:
            candidate["holdout_score_path"] = f"runs/{run_id}/holdout_scores/{candidate_id}.json"
        candidates.append(candidate)
    run_dir.joinpath("EVALUATION.json").write_text(
        json.dumps(
            {
                "schema_version": "ciph.evaluation.v1",
                "run_id": run_id,
                "phase": "holdout_released",
                "baseline_candidate_id": frontier_ids[0],
                "search_set": {"scenario_ids": ["search-1"]},
                "holdout_set": {"scenario_ids": ["holdout-1"], "sealed": False},
                "budget": {"max_candidates": 3, "max_holdout_releases": 1},
                "frontier_candidate_ids": frontier_ids,
                "holdout_releases": [
                    {
                        "release_index": 1,
                        "released_at": "2026-05-20T04:00:00Z",
                        "frontier_candidate_ids": frontier_ids,
                    }
                ],
                "candidates": candidates,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
