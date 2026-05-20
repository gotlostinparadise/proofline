import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.init_candidate import initialize_candidate
from scripts.validate_evaluation import validate_evaluation, write_evaluation_report


class ValidateEvaluationTests(unittest.TestCase):
    def test_validate_evaluation_accepts_search_phase_protocol(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_run(root)
            _write_evaluation(run_dir)

            result = validate_evaluation(run_dir, root=root)

            self.assertTrue(result.ok, result.errors)
            self.assertIn("PASS baseline candidate baseline", result.messages)
            self.assertIn("PASS holdout sealed", result.messages)

    def test_validate_evaluation_rejects_overlapping_search_and_holdout_sets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_run(root)
            _write_evaluation(run_dir, holdout_ids=["search-1"])

            result = validate_evaluation(run_dir, root=root)

            self.assertFalse(result.ok)
            self.assertIn("search_set and holdout_set scenario_ids must be disjoint: search-1", result.errors)

    def test_validate_evaluation_requires_existing_baseline_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_run(root)
            _write_evaluation(run_dir, baseline_candidate_id="missing")

            result = validate_evaluation(run_dir, root=root)

            self.assertFalse(result.ok)
            self.assertIn("baseline candidate must be listed: missing", result.errors)

    def test_validate_evaluation_rejects_holdout_leakage_during_search_phase(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_run(root)
            score_path = run_dir / "candidates" / "baseline" / "score.json"
            score = json.loads(score_path.read_text(encoding="utf-8"))
            score["holdout_scores"] = {"task_success": 1.0}
            score_path.write_text(json.dumps(score, indent=2) + "\n", encoding="utf-8")
            _write_evaluation(run_dir)

            result = validate_evaluation(run_dir, root=root)

            self.assertFalse(result.ok)
            self.assertIn("search phase forbids holdout_scores in runs/sample/candidates/baseline/score.json", result.errors)

    def test_validate_evaluation_rejects_multi_class_ablation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_run(root)
            score_path = run_dir / "candidates" / "baseline" / "score.json"
            score = json.loads(score_path.read_text(encoding="utf-8"))
            score["ablation"]["changed_dimensions"] = ["policy:verification", "source:runner"]
            score_path.write_text(json.dumps(score, indent=2) + "\n", encoding="utf-8")
            _write_evaluation(run_dir)

            result = validate_evaluation(run_dir, root=root)

            self.assertFalse(result.ok)
            self.assertIn("candidate baseline must change one ablation class at a time", result.errors)

    def test_validate_evaluation_rejects_compound_lineage_ablation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_run(root)
            initialize_candidate(
                run_dir / "MANIFEST.json",
                "frontier",
                root=root,
                changed_modules=["runner"],
                parent_ids=["baseline"],
                change_class="source",
            )
            _write_evaluation(run_dir, frontier_ids=["frontier"], extra_candidates=["frontier"])

            result = validate_evaluation(run_dir, root=root)

            self.assertFalse(result.ok)
            self.assertIn(
                "candidate frontier ablation changed_class source compounds with parent baseline changed_class policy",
                result.errors,
            )

    def test_validate_evaluation_accepts_source_lineage_from_baseline_role(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_run(root)
            initialize_candidate(
                run_dir / "MANIFEST.json",
                "frontier",
                root=root,
                changed_modules=["runner"],
                parent_ids=["baseline"],
                change_class="source",
            )
            _write_evaluation(
                run_dir,
                frontier_ids=["frontier"],
                extra_candidates=["frontier"],
                baseline_role="baseline",
            )

            result = validate_evaluation(run_dir, root=root)

            self.assertTrue(result.ok, result.errors)

    def test_validate_evaluation_rejects_holdout_phase_without_frontier(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_run(root)
            _write_evaluation(
                run_dir,
                phase="holdout_released",
                frontier_ids=[],
                holdout_sealed=False,
                holdout_releases=[
                    {
                        "release_index": 1,
                        "released_at": "2026-05-20T04:00:00Z",
                        "frontier_candidate_ids": ["baseline"],
                    }
                ],
            )

            result = validate_evaluation(run_dir, root=root)

            self.assertFalse(result.ok)
            self.assertIn("holdout_released phase requires at least one frontier candidate", result.errors)

    def test_validate_evaluation_accepts_holdout_released_protocol(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_run(root)
            _write_evaluation(
                run_dir,
                phase="holdout_released",
                frontier_ids=["baseline"],
                holdout_sealed=False,
                holdout_releases=[
                    {
                        "release_index": 1,
                        "released_at": "2026-05-20T04:00:00Z",
                        "frontier_candidate_ids": ["baseline"],
                    }
                ],
            )

            result = validate_evaluation(run_dir, root=root)

            self.assertTrue(result.ok, result.errors)
            self.assertIn("PASS holdout released", result.messages)
            self.assertIn("PASS holdout release 1", result.messages)

    def test_validate_evaluation_accepts_released_protocol_with_holdout_score_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_run(root)
            _write_holdout_score(run_dir, "baseline")
            _write_evaluation(
                run_dir,
                phase="holdout_released",
                frontier_ids=["baseline"],
                holdout_sealed=False,
                holdout_score_path=f"runs/{run_dir.name}/holdout_scores/baseline.json",
                holdout_releases=[
                    {
                        "release_index": 1,
                        "released_at": "2026-05-20T04:00:00Z",
                        "frontier_candidate_ids": ["baseline"],
                    }
                ],
            )

            result = validate_evaluation(run_dir, root=root)

            self.assertTrue(result.ok, result.errors)
            self.assertIn("PASS holdout score baseline", result.messages)

    def test_validate_evaluation_rejects_holdout_score_for_wrong_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_run(root)
            _write_holdout_score(run_dir, "other")
            _write_evaluation(
                run_dir,
                phase="holdout_released",
                frontier_ids=["baseline"],
                holdout_sealed=False,
                holdout_score_path=f"runs/{run_dir.name}/holdout_scores/other.json",
                holdout_releases=[
                    {
                        "release_index": 1,
                        "released_at": "2026-05-20T04:00:00Z",
                        "frontier_candidate_ids": ["baseline"],
                    }
                ],
            )

            result = validate_evaluation(run_dir, root=root)

            self.assertFalse(result.ok)
            self.assertIn("candidate baseline holdout score candidate_id mismatch", result.errors)

    def test_validate_evaluation_rejects_holdout_score_with_search_scenario(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_run(root)
            _write_holdout_score(run_dir, "baseline", scenario_ids=["search-1"])
            _write_evaluation(
                run_dir,
                phase="holdout_released",
                frontier_ids=["baseline"],
                holdout_sealed=False,
                holdout_score_path=f"runs/{run_dir.name}/holdout_scores/baseline.json",
                holdout_releases=[
                    {
                        "release_index": 1,
                        "released_at": "2026-05-20T04:00:00Z",
                        "frontier_candidate_ids": ["baseline"],
                    }
                ],
            )

            result = validate_evaluation(run_dir, root=root)

            self.assertFalse(result.ok)
            self.assertIn("candidate baseline holdout score scenario_ids must be within holdout_set: search-1", result.errors)

    def test_validate_evaluation_rejects_released_protocol_with_sealed_holdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_run(root)
            _write_evaluation(
                run_dir,
                phase="holdout_released",
                frontier_ids=["baseline"],
                holdout_sealed=True,
                holdout_releases=[
                    {
                        "release_index": 1,
                        "released_at": "2026-05-20T04:00:00Z",
                        "frontier_candidate_ids": ["baseline"],
                    }
                ],
            )

            result = validate_evaluation(run_dir, root=root)

            self.assertFalse(result.ok)
            self.assertIn("holdout_set.sealed must be false after holdout release", result.errors)

    def test_validate_evaluation_rejects_release_count_over_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_run(root)
            _write_evaluation(
                run_dir,
                phase="holdout_released",
                frontier_ids=["baseline"],
                holdout_sealed=False,
                holdout_releases=[
                    {
                        "release_index": 1,
                        "released_at": "2026-05-20T04:00:00Z",
                        "frontier_candidate_ids": ["baseline"],
                    },
                    {
                        "release_index": 2,
                        "released_at": "2026-05-20T05:00:00Z",
                        "frontier_candidate_ids": ["baseline"],
                    },
                ],
            )

            result = validate_evaluation(run_dir, root=root)

            self.assertFalse(result.ok)
            self.assertIn("holdout_releases count exceeds budget.max_holdout_releases: 2/1", result.errors)

    def test_write_evaluation_report_creates_html_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_run(root)
            _write_evaluation(run_dir)
            output_path = run_dir / "artifacts" / "evaluation-report.html"

            write_evaluation_report(run_dir, output_path, root=root)

            html = output_path.read_text(encoding="utf-8")
            self.assertTrue(html.startswith("<!doctype html>"))
            self.assertIn('data-proofline-report="evaluation-protocol"', html)
            self.assertIn("PASS baseline candidate baseline", html)

    def test_validate_evaluation_script_runs_when_executed_by_file_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_run(root)
            _write_evaluation(run_dir)
            output_path = run_dir / "artifacts" / "evaluation-report.html"
            repo_root = Path(__file__).resolve().parents[1]

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/validate_evaluation.py",
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
            self.assertIn(f"PASS evaluation {run_dir}", completed.stdout)
            self.assertTrue(output_path.is_file())


def _create_run(root: Path) -> Path:
    run_dir = root / "runs" / "sample"
    manifest_path = run_dir / "MANIFEST.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "ciph.manifest.v1",
                "task_id": "sample",
                "objective": "Validate evaluation protocol.",
                "deliverables": [],
                "artifacts": [],
                "checks": [],
                "risks": [],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    initialize_candidate(manifest_path, "baseline", root=root, changed_modules=["baseline"])
    score_path = run_dir / "candidates" / "baseline" / "score.json"
    score = json.loads(score_path.read_text(encoding="utf-8"))
    score["search_scores"] = {
        "task_success": 1.0,
        "audit_completeness": 1.0,
        "cost_tokens": 100,
        "wall_minutes": 2,
        "defect_escape_rate": 0.0,
    }
    score_path.write_text(json.dumps(score, indent=2) + "\n", encoding="utf-8")
    return run_dir


def _write_evaluation(
    run_dir: Path,
    *,
    phase: str = "search",
    baseline_candidate_id: str = "baseline",
    holdout_ids: list[str] | None = None,
    frontier_ids: list[str] | None = None,
    holdout_sealed: bool = True,
    holdout_score_path: str | None = None,
    holdout_releases: list[dict[str, object]] | None = None,
    extra_candidates: list[str] | None = None,
    baseline_role: str = "candidate",
) -> None:
    run_id = run_dir.name
    candidate_path = f"runs/{run_id}/candidates/baseline/score.json"
    candidate = {
        "candidate_id": "baseline",
        "role": baseline_role,
        "evaluation_phase": "search",
        "score_path": candidate_path,
    }
    if holdout_score_path is not None:
        candidate["evaluation_phase"] = "holdout"
        candidate["holdout_score_path"] = holdout_score_path
    payload = {
        "schema_version": "ciph.evaluation.v1",
        "run_id": run_id,
        "phase": phase,
        "baseline_candidate_id": baseline_candidate_id,
        "search_set": {"scenario_ids": ["search-1", "search-2"]},
        "holdout_set": {"scenario_ids": holdout_ids or ["holdout-1"], "sealed": holdout_sealed},
        "budget": {"max_candidates": 3, "max_holdout_releases": 1},
        "frontier_candidate_ids": frontier_ids if frontier_ids is not None else [],
        "candidates": [candidate],
    }
    for candidate_id in extra_candidates or []:
        payload["candidates"].append(
            {
                "candidate_id": candidate_id,
                "role": "candidate",
                "evaluation_phase": "search",
                "score_path": f"runs/{run_id}/candidates/{candidate_id}/score.json",
            }
        )
    if holdout_releases is not None:
        payload["holdout_releases"] = holdout_releases
    run_dir.joinpath("EVALUATION.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_holdout_score(run_dir: Path, candidate_id: str, scenario_ids: list[str] | None = None) -> None:
    score_dir = run_dir / "holdout_scores"
    score_dir.mkdir(parents=True, exist_ok=True)
    score_dir.joinpath(f"{candidate_id}.json").write_text(
        json.dumps(
            {
                "schema_version": "ciph.holdout-score.v1",
                "candidate_id": candidate_id,
                "release_index": 1,
                "scored_at": "2026-05-20T05:00:00Z",
                "scenario_ids": scenario_ids or ["holdout-1"],
                "holdout_scores": {
                    "task_success": 0.95,
                    "audit_completeness": 0.94,
                    "cost_tokens": 140,
                    "wall_minutes": 3,
                    "defect_escape_rate": 0.01,
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
