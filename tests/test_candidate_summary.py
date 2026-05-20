import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.candidate_summary import render_candidate_summary, write_candidate_summary


class CandidateSummaryTests(unittest.TestCase):
    def test_render_candidate_summary_marks_pareto_frontier_and_dominated_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "runs" / "sample"
            _write_score(run_dir, "strong", task_success=0.9, audit_completeness=0.9, cost_tokens=100, wall_minutes=2, defect_escape_rate=0.0)
            _write_score(run_dir, "weak", task_success=0.6, audit_completeness=0.7, cost_tokens=200, wall_minutes=5, defect_escape_rate=0.2)

            output = render_candidate_summary(run_dir)

            self.assertIn("# CIPH Candidate Summary", output)
            self.assertIn("| strong | frontier |", output)
            self.assertIn("| weak | dominated |", output)

    def test_write_candidate_summary_creates_report_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "runs" / "sample"
            output_path = run_dir / "artifacts" / "candidate-summary.md"
            _write_score(run_dir, "strong", task_success=0.9, audit_completeness=0.9, cost_tokens=100, wall_minutes=2, defect_escape_rate=0.0)

            write_candidate_summary(run_dir, output_path)

            self.assertTrue(output_path.is_file())
            self.assertIn("# CIPH Candidate Summary", output_path.read_text(encoding="utf-8"))

    def test_write_candidate_summary_creates_html_report_when_output_suffix_is_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "runs" / "sample"
            output_path = run_dir / "artifacts" / "candidate-summary.html"
            _write_score(run_dir, "strong", task_success=0.9, audit_completeness=0.9, cost_tokens=100, wall_minutes=2, defect_escape_rate=0.0)

            write_candidate_summary(run_dir, output_path)

            html = output_path.read_text(encoding="utf-8")
            self.assertTrue(html.startswith("<!doctype html>"))
            self.assertIn('data-proofline-report="candidate-summary"', html)
            self.assertIn("CIPH Candidate Summary", html)
            self.assertIn("<table", html)
            self.assertIn("strong", html)

    def test_candidate_summary_includes_mechanism_metrics_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "runs" / "sample"
            _write_score(
                run_dir,
                "instrumented",
                task_success=0.9,
                audit_completeness=0.9,
                cost_tokens=100,
                wall_minutes=2,
                defect_escape_rate=0.0,
                mechanism_metrics={
                    "artifact_contract_compliance": 1.0,
                    "stage_coverage": 0.75,
                    "ordered_workflow_compliance": 1.0,
                    "tool_call_success": 0.5,
                    "handoff_recall": 1.0,
                    "validation_coverage": 0.8,
                },
            )

            output = render_candidate_summary(run_dir)

            self.assertIn("Artifact Contract", output)
            self.assertIn("Stage Coverage", output)
            self.assertIn("| instrumented | frontier |", output)
            self.assertIn("0.75", output)

    def test_candidate_summary_includes_evaluation_protocol_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "runs" / "sample"
            _write_score(run_dir, "baseline", task_success=0.9, audit_completeness=0.9, cost_tokens=100, wall_minutes=2, defect_escape_rate=0.0)
            (run_dir / "EVALUATION.json").write_text(
                json.dumps(
                    {
                        "schema_version": "ciph.evaluation.v1",
                        "run_id": "sample",
                        "phase": "search",
                        "baseline_candidate_id": "baseline",
                        "search_set": {"scenario_ids": ["search-1"]},
                        "holdout_set": {"scenario_ids": ["holdout-1"], "sealed": True},
                        "budget": {"max_candidates": 3, "max_holdout_releases": 1},
                        "frontier_candidate_ids": [],
                        "candidates": [
                            {
                                "candidate_id": "baseline",
                                "role": "baseline",
                                "evaluation_phase": "search",
                                "score_path": "runs/sample/candidates/baseline/score.json",
                            }
                        ],
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            output = render_candidate_summary(run_dir)

            self.assertIn("Eval Phase", output)
            self.assertIn("Holdout", output)
            self.assertIn("| baseline | frontier | search | sealed |", output)

    def test_candidate_summary_includes_score_provenance_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "runs" / "sample"
            _write_score(
                run_dir,
                "frontier",
                task_success=0.9,
                audit_completeness=0.9,
                cost_tokens=100,
                wall_minutes=2,
                defect_escape_rate=0.0,
                evaluator_id="search-evaluator",
            )

            output = render_candidate_summary(run_dir)

            self.assertIn("Search Evaluator", output)
            self.assertIn("| frontier | frontier | - | - | 0.9 | 0.9 | 100 | 2 | 0.0 | - | - | - | - | - | - | - | - | - | - | - | search-evaluator |", output)

    def test_candidate_summary_script_runs_when_executed_by_file_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "runs" / "sample"
            output_path = run_dir / "artifacts" / "candidate-summary.md"
            _write_score(run_dir, "strong", task_success=0.9, audit_completeness=0.9, cost_tokens=100, wall_minutes=2, defect_escape_rate=0.0)
            repo_root = Path(__file__).resolve().parents[1]

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/candidate_summary.py",
                    str(run_dir),
                    "--output",
                    str(output_path),
                ],
                cwd=repo_root,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn(f"Wrote CIPH candidate summary: {output_path}", completed.stdout)
            self.assertTrue(output_path.is_file())


def _write_score(
    run_dir: Path,
    candidate_id: str,
    task_success: float,
    audit_completeness: float,
    cost_tokens: int,
    wall_minutes: int,
    defect_escape_rate: float,
    mechanism_metrics: dict[str, float] | None = None,
    evaluator_id: str | None = None,
) -> None:
    candidate_dir = run_dir / "candidates" / candidate_id
    candidate_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "candidate_id": candidate_id,
        "parent_ids": [],
        "changed_modules": [],
        "search_scores": {
            "task_success": task_success,
            "audit_completeness": audit_completeness,
            "cost_tokens": cost_tokens,
            "wall_minutes": wall_minutes,
            "defect_escape_rate": defect_escape_rate,
        },
        "trace_paths": [
            f"candidates/{candidate_id}/trace/prompts.jsonl",
            f"candidates/{candidate_id}/trace/tools.jsonl",
            f"candidates/{candidate_id}/trace/failures.md",
        ],
        "mechanism_metrics": mechanism_metrics or {},
        "pareto_status": "unscored",
    }
    if evaluator_id is not None:
        payload["score_provenance"] = {"evaluator_id": evaluator_id}
    candidate_dir.joinpath("score.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
