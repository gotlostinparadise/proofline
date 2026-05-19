import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.init_candidate import initialize_candidate
from scripts.release_holdout import release_holdout
from scripts.validate_evaluation import validate_evaluation


class ReleaseHoldoutTests(unittest.TestCase):
    def test_release_holdout_transitions_search_protocol_to_released(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_run(root)
            _write_evaluation(run_dir, frontier_ids=["frontier"])

            result = release_holdout(run_dir, root=root, released_at="2026-05-20T04:00:00Z")

            self.assertTrue(result.ok, result.errors)
            self.assertTrue(result.updated)
            payload = _read_evaluation(run_dir)
            self.assertEqual(payload["phase"], "holdout_released")
            self.assertFalse(payload["holdout_set"]["sealed"])
            self.assertEqual(
                payload["holdout_releases"],
                [
                    {
                        "release_index": 1,
                        "released_at": "2026-05-20T04:00:00Z",
                        "frontier_candidate_ids": ["frontier"],
                    }
                ],
            )
            post_release = validate_evaluation(run_dir, root=root)
            self.assertTrue(post_release.ok, post_release.errors)

    def test_release_holdout_is_idempotent_after_valid_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_run(root)
            _write_evaluation(
                run_dir,
                phase="holdout_released",
                holdout_sealed=False,
                frontier_ids=["frontier"],
                holdout_releases=[
                    {
                        "release_index": 1,
                        "released_at": "2026-05-20T04:00:00Z",
                        "frontier_candidate_ids": ["frontier"],
                    }
                ],
            )

            result = release_holdout(run_dir, root=root, released_at="2026-05-20T05:00:00Z")

            self.assertTrue(result.ok, result.errors)
            self.assertFalse(result.updated)
            self.assertIn("PASS holdout already released", result.messages)
            self.assertEqual(len(_read_evaluation(run_dir)["holdout_releases"]), 1)

    def test_release_holdout_rejects_missing_frontier(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_run(root)
            _write_evaluation(run_dir, frontier_ids=[])

            result = release_holdout(run_dir, root=root, released_at="2026-05-20T04:00:00Z")

            self.assertFalse(result.ok)
            self.assertIn("frontier_candidate_ids must contain at least one candidate before holdout release", result.errors)
            self.assertEqual(_read_evaluation(run_dir)["phase"], "search")

    def test_release_holdout_rejects_exhausted_release_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_run(root)
            _write_evaluation(
                run_dir,
                frontier_ids=["frontier"],
                holdout_releases=[
                    {
                        "release_index": 1,
                        "released_at": "2026-05-20T03:00:00Z",
                        "frontier_candidate_ids": ["frontier"],
                    }
                ],
            )

            result = release_holdout(run_dir, root=root, released_at="2026-05-20T04:00:00Z")

            self.assertFalse(result.ok)
            self.assertIn("holdout release budget exhausted: 1/1", result.errors)
            self.assertEqual(_read_evaluation(run_dir)["phase"], "search")

    def test_release_holdout_rejects_invalid_frontier_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_run(root)
            _write_evaluation(run_dir, frontier_ids=["frontier"])
            (run_dir / "candidates" / "frontier" / "source" / "README.md").unlink()

            result = release_holdout(run_dir, root=root, released_at="2026-05-20T04:00:00Z")

            self.assertFalse(result.ok)
            self.assertIn("candidate frontier missing required file: source/README.md", result.errors)
            self.assertEqual(_read_evaluation(run_dir)["phase"], "search")

    def test_release_holdout_rejects_search_phase_holdout_leakage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_run(root)
            score_path = run_dir / "candidates" / "frontier" / "score.json"
            score = json.loads(score_path.read_text(encoding="utf-8"))
            score["holdout_scores"] = {"task_success": 1.0}
            score_path.write_text(json.dumps(score, indent=2) + "\n", encoding="utf-8")
            _write_evaluation(run_dir, frontier_ids=["frontier"])

            result = release_holdout(run_dir, root=root, released_at="2026-05-20T04:00:00Z")

            self.assertFalse(result.ok)
            self.assertIn("evaluation search phase forbids holdout_scores in runs/sample/candidates/frontier/score.json", result.errors)
            self.assertEqual(_read_evaluation(run_dir)["phase"], "search")

    def test_release_holdout_cli_updates_protocol_and_writes_html_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_run(root)
            _write_evaluation(run_dir, frontier_ids=["frontier"])
            output_path = run_dir / "artifacts" / "holdout-release.html"
            repo_root = Path(__file__).resolve().parents[1]

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/release_holdout.py",
                    str(run_dir),
                    "--root",
                    str(root),
                    "--released-at",
                    "2026-05-20T04:00:00Z",
                    "--output",
                    str(output_path),
                ],
                cwd=repo_root,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn(f"PASS holdout release {run_dir}", completed.stdout)
            self.assertTrue(output_path.is_file())
            html = output_path.read_text(encoding="utf-8")
            self.assertIn('data-proofline-report="holdout-release"', html)
            self.assertEqual(_read_evaluation(run_dir)["phase"], "holdout_released")


def _create_run(root: Path) -> Path:
    run_dir = root / "runs" / "sample"
    manifest_path = run_dir / "MANIFEST.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "ciph.manifest.v1",
                "task_id": "sample",
                "objective": "Validate holdout release.",
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
    initialize_candidate(manifest_path, "frontier", root=root, changed_modules=["frontier"], parent_ids=["baseline"])
    _write_score(run_dir / "candidates" / "baseline" / "score.json", task_success=0.8)
    _write_score(run_dir / "candidates" / "frontier" / "score.json", task_success=0.9)
    return run_dir


def _write_score(score_path: Path, *, task_success: float) -> None:
    score = json.loads(score_path.read_text(encoding="utf-8"))
    score["search_scores"] = {
        "task_success": task_success,
        "audit_completeness": 1.0,
        "cost_tokens": 100,
        "wall_minutes": 2,
        "defect_escape_rate": 0.0,
    }
    score["mechanism_metrics"] = {
        "artifact_contract_compliance": 1.0,
        "stage_coverage": 1.0,
        "ordered_workflow_compliance": 1.0,
        "tool_call_success": 1.0,
        "handoff_recall": 1.0,
        "validation_coverage": 1.0,
    }
    score_path.write_text(json.dumps(score, indent=2) + "\n", encoding="utf-8")


def _write_evaluation(
    run_dir: Path,
    *,
    phase: str = "search",
    holdout_sealed: bool = True,
    frontier_ids: list[str] | None = None,
    holdout_releases: list[dict[str, object]] | None = None,
) -> None:
    run_id = run_dir.name
    payload = {
        "schema_version": "ciph.evaluation.v1",
        "run_id": run_id,
        "phase": phase,
        "baseline_candidate_id": "baseline",
        "search_set": {"scenario_ids": ["search-1", "search-2"]},
        "holdout_set": {"scenario_ids": ["holdout-1"], "sealed": holdout_sealed},
        "budget": {"max_candidates": 3, "max_holdout_releases": 1},
        "frontier_candidate_ids": frontier_ids if frontier_ids is not None else [],
        "candidates": [
            {
                "candidate_id": "baseline",
                "role": "baseline",
                "evaluation_phase": "search",
                "score_path": f"runs/{run_id}/candidates/baseline/score.json",
            },
            {
                "candidate_id": "frontier",
                "role": "frontier",
                "evaluation_phase": "search",
                "score_path": f"runs/{run_id}/candidates/frontier/score.json",
            },
        ],
    }
    if holdout_releases is not None:
        payload["holdout_releases"] = holdout_releases
    run_dir.joinpath("EVALUATION.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _read_evaluation(run_dir: Path) -> dict[str, object]:
    return json.loads(run_dir.joinpath("EVALUATION.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
