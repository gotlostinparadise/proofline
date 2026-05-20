import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.validate_evaluator_replay import validate_evaluator_replay, write_evaluator_replay_report


class ValidateEvaluatorReplayTests(unittest.TestCase):
    def test_validate_evaluator_replay_accepts_search_and_holdout_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_replay_run(root)

            result = validate_evaluator_replay(run_dir, root=root)

            self.assertTrue(result.ok, result.errors)
            self.assertIn("PASS evaluator replay search-evaluator", result.messages)
            self.assertIn("PASS evaluator replay holdout-evaluator", result.messages)
            self.assertIn("PASS score replay frontier search", result.messages)
            self.assertIn("PASS score replay frontier holdout", result.messages)

    def test_validate_evaluator_replay_rejects_missing_replay_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_replay_run(root)
            manifest_path = run_dir / "evaluators" / "search-evaluator.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            del manifest["replay"]
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

            result = validate_evaluator_replay(run_dir, root=root)

            self.assertFalse(result.ok)
            self.assertIn("evaluator search-evaluator replay must be an object", result.errors)

    def test_validate_evaluator_replay_rejects_unsafe_working_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_replay_run(root)
            manifest_path = run_dir / "evaluators" / "search-evaluator.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["replay"]["working_directory"] = "../outside"
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

            result = validate_evaluator_replay(run_dir, root=root)

            self.assertFalse(result.ok)
            self.assertIn("evaluator search-evaluator replay.working_directory must be a local path under root: ../outside", result.errors)

    def test_validate_evaluator_replay_rejects_shell_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_replay_run(root)
            manifest_path = run_dir / "evaluators" / "search-evaluator.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["replay"]["command_metadata"]["shell"] = True
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

            result = validate_evaluator_replay(run_dir, root=root)

            self.assertFalse(result.ok)
            self.assertIn("evaluator search-evaluator replay.command_metadata.shell must be false", result.errors)

    def test_validate_evaluator_replay_rejects_empty_env_allowlist_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_replay_run(root)
            manifest_path = run_dir / "evaluators" / "search-evaluator.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["replay"]["env_allowlist"] = ["PATH", ""]
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

            result = validate_evaluator_replay(run_dir, root=root)

            self.assertFalse(result.ok)
            self.assertIn("evaluator search-evaluator replay.env_allowlist must contain unique non-empty strings", result.errors)

    def test_validate_evaluator_replay_rejects_output_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_replay_run(root)
            score_path = run_dir / "candidates" / "frontier" / "score.json"
            score = json.loads(score_path.read_text(encoding="utf-8"))
            score["search_scores"]["task_success"] = 0.01
            score_path.write_text(json.dumps(score, indent=2) + "\n", encoding="utf-8")

            result = validate_evaluator_replay(run_dir, root=root)

            self.assertFalse(result.ok)
            self.assertIn(
                "evaluator search-evaluator replay.expected_output_hashes mismatch for runs/sample/candidates/frontier/score.json",
                result.errors,
            )

    def test_validate_evaluator_replay_rejects_integrity_hash_disagreement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_replay_run(root)
            manifest_path = run_dir / "evaluators" / "search-evaluator.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["integrity"]["output_hashes"]["runs/sample/candidates/frontier/score.json"] = "sha256:" + ("0" * 64)
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

            result = validate_evaluator_replay(run_dir, root=root)

            self.assertFalse(result.ok)
            self.assertIn(
                "evaluator search-evaluator replay.expected_output_hashes disagrees with integrity.output_hashes for runs/sample/candidates/frontier/score.json",
                result.errors,
            )

    def test_write_evaluator_replay_report_creates_html_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_replay_run(root)
            output_path = run_dir / "artifacts" / "evaluator-replay.html"

            write_evaluator_replay_report(run_dir, output_path, root=root)

            html = output_path.read_text(encoding="utf-8")
            self.assertTrue(html.startswith("<!doctype html>"))
            self.assertIn('data-proofline-report="evaluator-replay"', html)
            self.assertIn("PASS evaluator replay search-evaluator", html)

    def test_validate_evaluator_replay_script_runs_when_executed_by_file_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_replay_run(root)
            output_path = run_dir / "artifacts" / "evaluator-replay.html"
            repo_root = Path(__file__).resolve().parents[1]

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/validate_evaluator_replay.py",
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
            self.assertIn(f"PASS evaluator replay {run_dir}", completed.stdout)
            self.assertTrue(output_path.is_file())


def _create_replay_run(root: Path) -> Path:
    run_dir = root / "runs" / "sample"
    (run_dir / "candidates" / "frontier").mkdir(parents=True)
    (run_dir / "holdout_scores").mkdir(parents=True)
    (run_dir / "evaluators").mkdir(parents=True)
    (run_dir / "artifacts").mkdir(parents=True)
    (run_dir / "artifacts" / "search-evidence.txt").write_text("search evidence\n", encoding="utf-8")
    (run_dir / "artifacts" / "holdout-evidence.txt").write_text("holdout evidence\n", encoding="utf-8")
    (run_dir / "artifacts" / "search-input.json").write_text("{}\n", encoding="utf-8")
    (run_dir / "artifacts" / "holdout-input.json").write_text("{}\n", encoding="utf-8")
    _write_search_score(run_dir)
    _write_holdout_score(run_dir)
    _write_evaluator_manifest(run_dir, "search-evaluator", "search", "runs/sample/candidates/frontier/score.json")
    _write_evaluator_manifest(run_dir, "holdout-evaluator", "holdout", "runs/sample/holdout_scores/frontier.json")
    _write_evaluation(run_dir)
    return run_dir


def _write_evaluator_manifest(run_dir: Path, evaluator_id: str, phase: str, output_path: str) -> None:
    input_path = f"runs/sample/artifacts/{phase}-input.json"
    evidence_path = f"runs/sample/artifacts/{phase}-evidence.txt"
    root = run_dir.parents[1]
    output_digest = _digest(root / output_path)
    run_dir.joinpath("evaluators", f"{evaluator_id}.json").write_text(
        json.dumps(
            {
                "schema_version": "ciph.evaluator-manifest.v1",
                "evaluator_id": evaluator_id,
                "evaluation_phase": phase,
                "command": f"python3 tools/evaluate.py --phase {phase}",
                "input_paths": [input_path],
                "output_paths": [output_path],
                "evidence_paths": [evidence_path],
                "metric_keys": [
                    "task_success",
                    "audit_completeness",
                    "cost_tokens",
                    "wall_minutes",
                    "defect_escape_rate",
                ],
                "integrity": {
                    "schema_version": "ciph.evaluator-integrity.v1",
                    "algorithm": "sha256",
                    "input_hashes": {input_path: _digest(root / input_path)},
                    "evidence_hashes": {evidence_path: _digest(root / evidence_path)},
                    "output_hashes": {output_path: output_digest},
                },
                "replay": {
                    "schema_version": "ciph.evaluator-replay.v1",
                    "mode": "metadata-only",
                    "working_directory": ".",
                    "command_metadata": {
                        "argv": ["python3", "tools/evaluate.py", "--phase", phase],
                        "shell": False,
                    },
                    "env_allowlist": ["PATH", "PYTHONPATH"],
                    "external_effect_policy": "local-only",
                    "expected_output_hashes": {output_path: output_digest},
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_search_score(run_dir: Path) -> None:
    run_dir.joinpath("candidates", "frontier", "score.json").write_text(
        json.dumps(
            {
                "schema_version": "ciph.candidate.v1",
                "candidate_id": "frontier",
                "search_scores": {
                    "task_success": 0.94,
                    "audit_completeness": 0.95,
                    "cost_tokens": 100,
                    "wall_minutes": 2,
                    "defect_escape_rate": 0.01,
                },
                "score_provenance": _score_provenance("search-evaluator", "search"),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_holdout_score(run_dir: Path) -> None:
    run_dir.joinpath("holdout_scores", "frontier.json").write_text(
        json.dumps(
            {
                "schema_version": "ciph.holdout-score.v1",
                "candidate_id": "frontier",
                "release_index": 1,
                "scored_at": "2026-05-20T07:00:00Z",
                "scenario_ids": ["holdout-1"],
                "holdout_scores": {
                    "task_success": 0.91,
                    "audit_completeness": 0.93,
                    "cost_tokens": 120,
                    "wall_minutes": 3,
                    "defect_escape_rate": 0.02,
                },
                "score_provenance": _score_provenance("holdout-evaluator", "holdout"),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _score_provenance(evaluator_id: str, phase: str) -> dict[str, object]:
    return {
        "schema_version": "ciph.score-provenance.v1",
        "evaluator_id": evaluator_id,
        "evaluator_manifest_path": f"runs/sample/evaluators/{evaluator_id}.json",
        "evaluation_phase": phase,
        "produced_at": "2026-05-20T07:00:00Z",
        "input_paths": [f"runs/sample/artifacts/{phase}-input.json"],
        "evidence_paths": [f"runs/sample/artifacts/{phase}-evidence.txt"],
    }


def _write_evaluation(run_dir: Path) -> None:
    run_dir.joinpath("EVALUATION.json").write_text(
        json.dumps(
            {
                "schema_version": "ciph.evaluation.v1",
                "run_id": "sample",
                "phase": "holdout_released",
                "baseline_candidate_id": "frontier",
                "search_set": {"scenario_ids": ["search-1"]},
                "holdout_set": {"scenario_ids": ["holdout-1"], "sealed": False},
                "budget": {"max_candidates": 3, "max_holdout_releases": 1},
                "frontier_candidate_ids": ["frontier"],
                "holdout_releases": [
                    {
                        "release_index": 1,
                        "released_at": "2026-05-20T06:00:00Z",
                        "frontier_candidate_ids": ["frontier"],
                    }
                ],
                "candidates": [
                    {
                        "candidate_id": "frontier",
                        "role": "frontier",
                        "evaluation_phase": "holdout",
                        "score_path": "runs/sample/candidates/frontier/score.json",
                        "holdout_score_path": "runs/sample/holdout_scores/frontier.json",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    unittest.main()
