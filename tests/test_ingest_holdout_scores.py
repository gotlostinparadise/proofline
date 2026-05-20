import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.ingest_holdout_scores import ingest_holdout_scores
from scripts.init_candidate import initialize_candidate
from scripts.validate_evaluation import validate_evaluation


class IngestHoldoutScoresTests(unittest.TestCase):
    def test_ingest_holdout_scores_links_canonical_score_after_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_run(root, released=True)
            input_path = root / "incoming-frontier.json"
            _write_holdout_score(input_path, "frontier")

            result = ingest_holdout_scores(run_dir, input_path, root=root)

            self.assertTrue(result.ok, result.errors)
            self.assertTrue(result.updated)
            canonical = run_dir / "holdout_scores" / "frontier.json"
            self.assertTrue(canonical.is_file())
            payload = _read_evaluation(run_dir)
            frontier = _candidate(payload, "frontier")
            self.assertEqual(frontier["evaluation_phase"], "holdout")
            self.assertEqual(frontier["holdout_score_path"], "runs/sample/holdout_scores/frontier.json")
            validation = validate_evaluation(run_dir, root=root)
            self.assertTrue(validation.ok, validation.errors)
            self.assertIn("PASS holdout score frontier", validation.messages)

    def test_ingest_holdout_scores_is_idempotent_for_same_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_run(root, released=True)
            input_path = root / "incoming-frontier.json"
            _write_holdout_score(input_path, "frontier")

            first = ingest_holdout_scores(run_dir, input_path, root=root)
            second = ingest_holdout_scores(run_dir, input_path, root=root)

            self.assertTrue(first.ok, first.errors)
            self.assertTrue(second.ok, second.errors)
            self.assertFalse(second.updated)
            self.assertIn("PASS holdout score already ingested frontier", second.messages)

    def test_ingest_holdout_scores_rejects_search_phase(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_run(root, released=False)
            input_path = root / "incoming-frontier.json"
            _write_holdout_score(input_path, "frontier")

            result = ingest_holdout_scores(run_dir, input_path, root=root)

            self.assertFalse(result.ok)
            self.assertIn("phase must be holdout_released before ingesting holdout scores", result.errors)
            self.assertFalse((run_dir / "holdout_scores" / "frontier.json").exists())

    def test_ingest_holdout_scores_rejects_candidate_outside_release_frontier(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_run(root, released=True)
            input_path = root / "incoming-baseline.json"
            _write_holdout_score(input_path, "baseline")

            result = ingest_holdout_scores(run_dir, input_path, root=root)

            self.assertFalse(result.ok)
            self.assertIn("candidate baseline was not in holdout release 1 frontier", result.errors)

    def test_ingest_holdout_scores_rejects_invalid_score_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_run(root, released=True)
            input_path = root / "incoming-frontier.json"
            _write_holdout_score(input_path, "frontier")
            score = json.loads(input_path.read_text(encoding="utf-8"))
            del score["holdout_scores"]["task_success"]
            input_path.write_text(json.dumps(score, indent=2) + "\n", encoding="utf-8")

            result = ingest_holdout_scores(run_dir, input_path, root=root)

            self.assertFalse(result.ok)
            self.assertIn("holdout_scores.task_success must be numeric", result.errors)

    def test_ingest_holdout_scores_cli_writes_html_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_run(root, released=True)
            input_path = root / "incoming-frontier.json"
            output_path = run_dir / "artifacts" / "holdout-ingest.html"
            _write_holdout_score(input_path, "frontier")
            repo_root = Path(__file__).resolve().parents[1]

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/ingest_holdout_scores.py",
                    str(run_dir),
                    str(input_path),
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
            self.assertIn(f"PASS holdout ingest {run_dir}", completed.stdout)
            self.assertTrue(output_path.is_file())
            html = output_path.read_text(encoding="utf-8")
            self.assertIn('data-proofline-report="holdout-ingest"', html)


def _create_run(root: Path, *, released: bool) -> Path:
    run_dir = root / "runs" / "sample"
    manifest_path = run_dir / "MANIFEST.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "ciph.manifest.v1",
                "task_id": "sample",
                "objective": "Ingest holdout scores.",
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
    _write_search_score(run_dir / "candidates" / "baseline" / "score.json", "baseline", task_success=0.8)
    _write_search_score(run_dir / "candidates" / "frontier" / "score.json", "frontier", task_success=0.9)
    _write_evaluation(run_dir, released=released)
    return run_dir


def _write_search_score(score_path: Path, candidate_id: str, *, task_success: float) -> None:
    score = json.loads(score_path.read_text(encoding="utf-8"))
    score["candidate_id"] = candidate_id
    score["search_scores"] = {
        "task_success": task_success,
        "audit_completeness": 1.0,
        "cost_tokens": 100,
        "wall_minutes": 2,
        "defect_escape_rate": 0.0,
    }
    score_path.write_text(json.dumps(score, indent=2) + "\n", encoding="utf-8")


def _write_evaluation(run_dir: Path, *, released: bool) -> None:
    run_id = run_dir.name
    payload = {
        "schema_version": "ciph.evaluation.v1",
        "run_id": run_id,
        "phase": "holdout_released" if released else "search",
        "baseline_candidate_id": "baseline",
        "search_set": {"scenario_ids": ["search-1", "search-2"]},
        "holdout_set": {"scenario_ids": ["holdout-1"], "sealed": not released},
        "budget": {"max_candidates": 3, "max_holdout_releases": 1},
        "frontier_candidate_ids": ["frontier"],
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
    if released:
        payload["holdout_releases"] = [
            {
                "release_index": 1,
                "released_at": "2026-05-20T04:00:00Z",
                "frontier_candidate_ids": ["frontier"],
            }
        ]
    run_dir.joinpath("EVALUATION.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_holdout_score(path: Path, candidate_id: str) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "ciph.holdout-score.v1",
                "candidate_id": candidate_id,
                "release_index": 1,
                "scored_at": "2026-05-20T05:00:00Z",
                "scenario_ids": ["holdout-1"],
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


def _read_evaluation(run_dir: Path) -> dict[str, object]:
    return json.loads(run_dir.joinpath("EVALUATION.json").read_text(encoding="utf-8"))


def _candidate(payload: dict[str, object], candidate_id: str) -> dict[str, object]:
    candidates = payload["candidates"]
    assert isinstance(candidates, list)
    for candidate in candidates:
        if isinstance(candidate, dict) and candidate.get("candidate_id") == candidate_id:
            return candidate
    raise AssertionError(f"missing candidate {candidate_id}")


if __name__ == "__main__":
    unittest.main()
