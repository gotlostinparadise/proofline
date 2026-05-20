import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.execute_evaluator_replay import execute_evaluator_replay, write_evaluator_replay_execution_report


class ExecuteEvaluatorReplayTests(unittest.TestCase):
    def test_execute_evaluator_replay_dry_run_does_not_run_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_replay_run(root, variant="mismatch")
            output_path = root / "runs/sample/candidates/frontier/score.json"
            before = output_path.read_text(encoding="utf-8")

            result = execute_evaluator_replay(run_dir, root=root)

            self.assertTrue(result.ok, result.errors)
            self.assertIn("DRY-RUN evaluator search-evaluator command not executed", result.messages)
            self.assertEqual(before, output_path.read_text(encoding="utf-8"))

    def test_execute_evaluator_replay_requires_argv0_approval_when_execute_is_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_replay_run(root)

            result = execute_evaluator_replay(run_dir, root=root, execute=True)

            self.assertFalse(result.ok)
            self.assertIn("evaluator search-evaluator command argv[0] is not approved for execution: python3", result.errors)

    def test_execute_evaluator_replay_fails_closed_without_network_sandbox(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_replay_run(root)

            result = execute_evaluator_replay(
                run_dir,
                root=root,
                execute=True,
                allowed_argv0=["python3"],
                sandbox_binary="/missing/ciph-bwrap",
            )

            self.assertFalse(result.ok)
            self.assertIn("network sandbox is required for execution and was not found: /missing/ciph-bwrap", result.errors)

    @unittest.skipUnless(shutil.which("bwrap"), "bwrap is required for local replay execution")
    def test_execute_evaluator_replay_runs_approved_local_command_and_verifies_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_replay_run(root)

            result = execute_evaluator_replay(
                run_dir,
                root=root,
                execute=True,
                allowed_argv0=["python3"],
                timeout_seconds=10,
            )

            self.assertTrue(result.ok, result.errors)
            self.assertIn("PASS evaluator search-evaluator execution exit_code=0", result.messages)
            self.assertIn("PASS evaluator search-evaluator output hash runs/sample/candidates/frontier/score.json", result.messages)

    @unittest.skipUnless(shutil.which("bwrap"), "bwrap is required for local replay execution")
    def test_execute_evaluator_replay_rejects_post_execution_output_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_replay_run(root, variant="mismatch")

            result = execute_evaluator_replay(
                run_dir,
                root=root,
                execute=True,
                allowed_argv0=["python3"],
                timeout_seconds=10,
            )

            self.assertFalse(result.ok)
            self.assertIn(
                "evaluator search-evaluator output hash mismatch after execution: runs/sample/candidates/frontier/score.json",
                result.errors,
            )

    @unittest.skipUnless(shutil.which("bwrap"), "bwrap is required for local replay execution")
    def test_execute_evaluator_replay_reports_timeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_replay_run(root, variant="sleep")

            result = execute_evaluator_replay(
                run_dir,
                root=root,
                execute=True,
                allowed_argv0=["python3"],
                timeout_seconds=0.1,
            )

            self.assertFalse(result.ok)
            self.assertIn("evaluator search-evaluator execution timed out after 0.1 seconds", result.errors)

    def test_write_evaluator_replay_execution_report_creates_html_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_replay_run(root)
            output_path = run_dir / "artifacts" / "execution.html"

            write_evaluator_replay_execution_report(run_dir, output_path, root=root)

            html = output_path.read_text(encoding="utf-8")
            self.assertTrue(html.startswith("<!doctype html>"))
            self.assertIn('data-proofline-report="evaluator-replay-execution"', html)
            self.assertIn("DRY-RUN evaluator search-evaluator command not executed", html)

    @unittest.skipUnless(shutil.which("bwrap"), "bwrap is required for local replay execution")
    def test_execute_evaluator_replay_report_suppresses_command_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_replay_run(root, variant="secret")
            output_path = run_dir / "artifacts" / "execution.html"

            result = write_evaluator_replay_execution_report(
                run_dir,
                output_path,
                root=root,
                execute=True,
                allowed_argv0=["python3"],
                timeout_seconds=10,
            )

            html = output_path.read_text(encoding="utf-8")
            self.assertTrue(result.ok, result.errors)
            self.assertIn("stdout_bytes=", html)
            self.assertNotIn("CIPH_SECRET_VALUE", html)

    def test_execute_evaluator_replay_script_runs_when_executed_by_file_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = _create_replay_run(root)
            output_path = run_dir / "artifacts" / "execution.html"
            repo_root = Path(__file__).resolve().parents[1]

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/execute_evaluator_replay.py",
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
            self.assertIn(f"PASS evaluator replay execution {run_dir}", completed.stdout)
            self.assertTrue(output_path.is_file())


def _create_replay_run(root: Path, variant: str = "same") -> Path:
    run_dir = root / "runs" / "sample"
    (run_dir / "candidates" / "frontier").mkdir(parents=True)
    (run_dir / "evaluators").mkdir(parents=True)
    (run_dir / "artifacts").mkdir(parents=True)
    (root / "tools").mkdir()
    _write_local_evaluator(root)
    _write_score(root, task_success=0.94)
    _write_evaluator_manifest(run_dir, variant)
    _write_evaluation(run_dir)
    return run_dir


def _write_local_evaluator(root: Path) -> None:
    root.joinpath("tools", "local_evaluator.py").write_text(
        """#!/usr/bin/env python3
import argparse
import json
import time


def payload(task_success):
    return {
        "schema_version": "ciph.candidate.v1",
        "candidate_id": "frontier",
        "search_scores": {
            "task_success": task_success,
            "audit_completeness": 0.95,
            "cost_tokens": 100,
            "wall_minutes": 2,
            "defect_escape_rate": 0.01,
        },
        "score_provenance": {
            "schema_version": "ciph.score-provenance.v1",
            "evaluator_id": "search-evaluator",
            "evaluator_manifest_path": "runs/sample/evaluators/search-evaluator.json",
            "evaluation_phase": "search",
            "produced_at": "2026-05-20T11:30:00Z",
            "input_paths": ["runs/sample/artifacts/search-input.json"],
            "evidence_paths": ["runs/sample/artifacts/search-evidence.txt"],
        },
    }


parser = argparse.ArgumentParser()
parser.add_argument("--output", required=True)
parser.add_argument("--variant", default="same")
args = parser.parse_args()

if args.variant == "sleep":
    time.sleep(2)
if args.variant == "secret":
    print("CIPH_SECRET_VALUE")

task_success = 0.2 if args.variant == "mismatch" else 0.94
with open(args.output, "w", encoding="utf-8") as handle:
    handle.write(json.dumps(payload(task_success), indent=2) + "\\n")
""",
        encoding="utf-8",
    )


def _write_score(root: Path, task_success: float) -> None:
    root.joinpath("runs", "sample", "candidates", "frontier", "score.json").write_text(
        json.dumps(_score_payload(task_success), indent=2) + "\n",
        encoding="utf-8",
    )


def _score_payload(task_success: float) -> dict[str, object]:
    return {
        "schema_version": "ciph.candidate.v1",
        "candidate_id": "frontier",
        "search_scores": {
            "task_success": task_success,
            "audit_completeness": 0.95,
            "cost_tokens": 100,
            "wall_minutes": 2,
            "defect_escape_rate": 0.01,
        },
        "score_provenance": {
            "schema_version": "ciph.score-provenance.v1",
            "evaluator_id": "search-evaluator",
            "evaluator_manifest_path": "runs/sample/evaluators/search-evaluator.json",
            "evaluation_phase": "search",
            "produced_at": "2026-05-20T11:30:00Z",
            "input_paths": ["runs/sample/artifacts/search-input.json"],
            "evidence_paths": ["runs/sample/artifacts/search-evidence.txt"],
        },
    }


def _write_evaluator_manifest(run_dir: Path, variant: str) -> None:
    root = run_dir.parents[1]
    input_path = "runs/sample/artifacts/search-input.json"
    evidence_path = "runs/sample/artifacts/search-evidence.txt"
    output_path = "runs/sample/candidates/frontier/score.json"
    root.joinpath(input_path).write_text("{}\n", encoding="utf-8")
    root.joinpath(evidence_path).write_text("search evidence\n", encoding="utf-8")
    output_digest = _digest(root / output_path)
    run_dir.joinpath("evaluators", "search-evaluator.json").write_text(
        json.dumps(
            {
                "schema_version": "ciph.evaluator-manifest.v1",
                "evaluator_id": "search-evaluator",
                "evaluation_phase": "search",
                "command": f"python3 tools/local_evaluator.py --output {output_path} --variant {variant}",
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
                        "argv": ["python3", "tools/local_evaluator.py", "--output", output_path, "--variant", variant],
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


def _write_evaluation(run_dir: Path) -> None:
    run_dir.joinpath("EVALUATION.json").write_text(
        json.dumps(
            {
                "schema_version": "ciph.evaluation.v1",
                "run_id": "sample",
                "phase": "search",
                "baseline_candidate_id": "frontier",
                "search_set": {"scenario_ids": ["search-1"]},
                "holdout_set": {"scenario_ids": ["holdout-1"], "sealed": True},
                "budget": {"max_candidates": 3, "max_holdout_releases": 1},
                "frontier_candidate_ids": ["frontier"],
                "holdout_releases": [],
                "candidates": [
                    {
                        "candidate_id": "frontier",
                        "role": "frontier",
                        "evaluation_phase": "search",
                        "score_path": "runs/sample/candidates/frontier/score.json",
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
