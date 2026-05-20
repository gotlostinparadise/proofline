import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO_ROOT / "skills" / "proofline"
INSTALLER = SKILL_DIR / "scripts" / "install_proofline.py"


class ProoflineSkillTests(unittest.TestCase):
    def test_installer_copies_harness_assets_and_installed_init_run_works(self):
        self.assertTrue(INSTALLER.exists(), f"Missing installer: {INSTALLER}")
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target"
            target.mkdir()

            completed = _run_installer(target)

            self.assertEqual(completed.returncode, 0, completed.stderr)
            vendor = target / "vendor" / "proofline"
            self.assertTrue((vendor / "harness" / "CIPH.md").is_file())
            self.assertTrue((vendor / "harness" / "runtime-charter.md").is_file())
            self.assertTrue((vendor / "templates" / "TASK.html").is_file())
            self.assertTrue((vendor / "templates" / "MANIFEST.json").is_file())
            self.assertTrue((vendor / "scripts" / "init_run.py").is_file())
            self.assertTrue((vendor / "scripts" / "init_candidate.py").is_file())
            self.assertTrue((vendor / "scripts" / "validate_candidate.py").is_file())
            self.assertTrue((vendor / "scripts" / "validate_evaluation.py").is_file())
            self.assertTrue((vendor / "scripts" / "release_holdout.py").is_file())
            self.assertTrue((vendor / "scripts" / "ingest_holdout_scores.py").is_file())
            self.assertTrue((vendor / "scripts" / "final_comparison.py").is_file())
            self.assertTrue((vendor / "scripts" / "validate_score_provenance.py").is_file())
            self.assertTrue((vendor / "scripts" / "validate_score_integrity.py").is_file())
            self.assertTrue((vendor / "scripts" / "validate_evaluator_replay.py").is_file())
            self.assertTrue((vendor / "scripts" / "execute_evaluator_replay.py").is_file())
            self.assertTrue((vendor / "scripts" / "lint_trace.py").is_file())
            self.assertTrue((vendor / "scripts" / "trace_metrics.py").is_file())
            self.assertTrue((vendor / "harness" / "policies" / "README.md").is_file())
            self.assertTrue(os.access(vendor / "scripts" / "init_run.py", os.X_OK))
            self.assertTrue(os.access(vendor / "scripts" / "init_candidate.py", os.X_OK))
            self.assertTrue(os.access(vendor / "scripts" / "validate_candidate.py", os.X_OK))
            self.assertTrue(os.access(vendor / "scripts" / "validate_evaluation.py", os.X_OK))
            self.assertTrue(os.access(vendor / "scripts" / "release_holdout.py", os.X_OK))
            self.assertTrue(os.access(vendor / "scripts" / "ingest_holdout_scores.py", os.X_OK))
            self.assertTrue(os.access(vendor / "scripts" / "final_comparison.py", os.X_OK))
            self.assertTrue(os.access(vendor / "scripts" / "validate_score_provenance.py", os.X_OK))
            self.assertTrue(os.access(vendor / "scripts" / "validate_score_integrity.py", os.X_OK))
            self.assertTrue(os.access(vendor / "scripts" / "validate_evaluator_replay.py", os.X_OK))
            self.assertTrue(os.access(vendor / "scripts" / "execute_evaluator_replay.py", os.X_OK))
            self.assertTrue(os.access(vendor / "scripts" / "lint_trace.py", os.X_OK))
            self.assertTrue(os.access(vendor / "scripts" / "trace_metrics.py", os.X_OK))

            init_run = subprocess.run(
                [
                    sys.executable,
                    "vendor/proofline/scripts/init_run.py",
                    "sample-run",
                    "--root",
                    str(target),
                    "--proofline-root",
                    str(vendor),
                    "--objective",
                    "Exercise installed Proofline.",
                ],
                cwd=target,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(init_run.returncode, 0, init_run.stderr)
            self.assertTrue((vendor / "runs" / "sample-run" / "TASK.html").is_file())
            self.assertTrue((vendor / "runs" / "sample-run" / "MANIFEST.json").is_file())
            self.assertTrue((vendor / "runs" / "sample-run" / "TRACE.jsonl").is_file())

            lint_trace = subprocess.run(
                [
                    sys.executable,
                    "vendor/proofline/scripts/lint_trace.py",
                    "vendor/proofline/runs/sample-run/TRACE.jsonl",
                    "--root",
                    str(target),
                ],
                cwd=target,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(lint_trace.returncode, 0, lint_trace.stderr)
            self.assertIn("PASS trace", lint_trace.stdout)

            init_candidate = subprocess.run(
                [
                    sys.executable,
                    "vendor/proofline/scripts/init_candidate.py",
                    "vendor/proofline/runs/sample-run/MANIFEST.json",
                    "baseline",
                    "--root",
                    str(target),
                    "--changed-module",
                    "candidate-search",
                ],
                cwd=target,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(init_candidate.returncode, 0, init_candidate.stderr)
            candidate_dir = vendor / "runs" / "sample-run" / "candidates" / "baseline"
            self.assertTrue((candidate_dir / "score.json").is_file())
            self.assertTrue((candidate_dir / "TRACE.jsonl").is_file())

            init_frontier = subprocess.run(
                [
                    sys.executable,
                    "vendor/proofline/scripts/init_candidate.py",
                    "vendor/proofline/runs/sample-run/MANIFEST.json",
                    "frontier",
                    "--root",
                    str(target),
                    "--changed-module",
                    "holdout-release",
                    "--parent",
                    "baseline",
                ],
                cwd=target,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(init_frontier.returncode, 0, init_frontier.stderr)
            frontier_dir = vendor / "runs" / "sample-run" / "candidates" / "frontier"
            self.assertTrue((frontier_dir / "score.json").is_file())

            validate_candidate = subprocess.run(
                [
                    sys.executable,
                    "vendor/proofline/scripts/validate_candidate.py",
                    "vendor/proofline/runs/sample-run/candidates/baseline",
                    "--root",
                    str(target),
                ],
                cwd=target,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(validate_candidate.returncode, 0, validate_candidate.stderr)
            self.assertIn("PASS candidate", validate_candidate.stdout)

            (vendor / "runs" / "sample-run" / "EVALUATION.json").write_text(
                json.dumps(
                    {
                        "schema_version": "ciph.evaluation.v1",
                        "run_id": "sample-run",
                        "phase": "search",
                        "baseline_candidate_id": "baseline",
                        "search_set": {"scenario_ids": ["search-1"]},
                        "holdout_set": {"scenario_ids": ["holdout-1"], "sealed": True},
                        "budget": {"max_candidates": 3, "max_holdout_releases": 1},
                        "frontier_candidate_ids": ["frontier"],
                        "candidates": [
                            {
                                "candidate_id": "baseline",
                                "role": "baseline",
                                "evaluation_phase": "search",
                                "score_path": "vendor/proofline/runs/sample-run/candidates/baseline/score.json",
                            },
                            {
                                "candidate_id": "frontier",
                                "role": "frontier",
                                "evaluation_phase": "search",
                                "score_path": "vendor/proofline/runs/sample-run/candidates/frontier/score.json",
                            }
                        ],
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            validate_evaluation = subprocess.run(
                [
                    sys.executable,
                    "vendor/proofline/scripts/validate_evaluation.py",
                    "vendor/proofline/runs/sample-run",
                    "--root",
                    str(target),
                ],
                cwd=target,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(validate_evaluation.returncode, 0, validate_evaluation.stderr)
            self.assertIn("PASS evaluation", validate_evaluation.stdout)

            release_holdout = subprocess.run(
                [
                    sys.executable,
                    "vendor/proofline/scripts/release_holdout.py",
                    "vendor/proofline/runs/sample-run",
                    "--root",
                    str(target),
                    "--released-at",
                    "2026-05-20T04:00:00Z",
                ],
                cwd=target,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(release_holdout.returncode, 0, release_holdout.stderr)
            self.assertIn("PASS holdout release", release_holdout.stdout)
            evaluation = json.loads((vendor / "runs" / "sample-run" / "EVALUATION.json").read_text(encoding="utf-8"))
            self.assertEqual(evaluation["phase"], "holdout_released")
            self.assertFalse(evaluation["holdout_set"]["sealed"])

            _write_installed_search_score(candidate_dir / "score.json", "baseline")
            _write_installed_search_score(frontier_dir / "score.json", "frontier")
            incoming_holdout = vendor / "runs" / "sample-run" / "artifacts" / "frontier-holdout-input.json"
            incoming_holdout.parent.mkdir(parents=True, exist_ok=True)
            incoming_holdout.write_text(
                json.dumps(
                    {
                        "schema_version": "ciph.holdout-score.v1",
                        "candidate_id": "frontier",
                        "release_index": 1,
                        "scored_at": "2026-05-20T05:00:00Z",
                        "scenario_ids": ["holdout-1"],
                        "holdout_scores": {
                            "task_success": 0.95,
                            "audit_completeness": 0.94,
                            "cost_tokens": 130,
                            "wall_minutes": 3,
                            "defect_escape_rate": 0.01,
                        },
                        "score_provenance": _installed_score_provenance("holdout-evaluator", "holdout"),
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            ingest_holdout = subprocess.run(
                [
                    sys.executable,
                    "vendor/proofline/scripts/ingest_holdout_scores.py",
                    "vendor/proofline/runs/sample-run",
                    "vendor/proofline/runs/sample-run/artifacts/frontier-holdout-input.json",
                    "--root",
                    str(target),
                ],
                cwd=target,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(ingest_holdout.returncode, 0, ingest_holdout.stderr)
            self.assertIn("PASS holdout ingest", ingest_holdout.stdout)
            _write_installed_evaluator_files(vendor)

            final_comparison = subprocess.run(
                [
                    sys.executable,
                    "vendor/proofline/scripts/final_comparison.py",
                    "vendor/proofline/runs/sample-run",
                    "--root",
                    str(target),
                    "--output",
                    "vendor/proofline/runs/sample-run/artifacts/final-comparison.html",
                ],
                cwd=target,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(final_comparison.returncode, 0, final_comparison.stderr)
            self.assertIn("PASS final comparison", final_comparison.stdout)
            self.assertTrue((vendor / "runs" / "sample-run" / "artifacts" / "final-comparison.html").is_file())

            validate_provenance = subprocess.run(
                [
                    sys.executable,
                    "vendor/proofline/scripts/validate_score_provenance.py",
                    "vendor/proofline/runs/sample-run",
                    "--root",
                    str(target),
                ],
                cwd=target,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(validate_provenance.returncode, 0, validate_provenance.stderr)
            self.assertIn("PASS score provenance", validate_provenance.stdout)

            validate_integrity = subprocess.run(
                [
                    sys.executable,
                    "vendor/proofline/scripts/validate_score_integrity.py",
                    "vendor/proofline/runs/sample-run",
                    "--root",
                    str(target),
                ],
                cwd=target,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(validate_integrity.returncode, 0, validate_integrity.stderr)
            self.assertIn("PASS score integrity", validate_integrity.stdout)

            validate_replay = subprocess.run(
                [
                    sys.executable,
                    "vendor/proofline/scripts/validate_evaluator_replay.py",
                    "vendor/proofline/runs/sample-run",
                    "--root",
                    str(target),
                ],
                cwd=target,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(validate_replay.returncode, 0, validate_replay.stderr)
            self.assertIn("PASS evaluator replay", validate_replay.stdout)

            execute_replay = subprocess.run(
                [
                    sys.executable,
                    "vendor/proofline/scripts/execute_evaluator_replay.py",
                    "vendor/proofline/runs/sample-run",
                    "--root",
                    str(target),
                    "--receipt-dir",
                    "vendor/proofline/runs/sample-run/replay_receipts",
                ],
                cwd=target,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(execute_replay.returncode, 0, execute_replay.stderr)
            self.assertIn("PASS evaluator replay execution", execute_replay.stdout)
            self.assertIn("DRY-RUN evaluator search-evaluator command not executed", execute_replay.stdout)
            receipt_path = vendor / "runs" / "sample-run" / "replay_receipts" / "search-evaluator-dry-run.json"
            self.assertTrue(receipt_path.is_file())
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["schema_version"], "ciph.replay-receipt.v1")
            self.assertEqual(receipt["status"], "DRY_RUN")
            self.assertNotIn("env", receipt)

    def test_bundled_assets_are_trace_aware(self):
        skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        manifest = (SKILL_DIR / "assets" / "proofline" / "templates" / "MANIFEST.json").read_text(encoding="utf-8")
        task_html = (SKILL_DIR / "assets" / "proofline" / "templates" / "TASK.html").read_text(encoding="utf-8")

        self.assertIn("lint_trace.py", skill_text)
        self.assertIn("trace_metrics.py", skill_text)
        self.assertIn("validate_candidate.py", skill_text)
        self.assertIn("validate_evaluation.py", skill_text)
        self.assertIn("release_holdout.py", skill_text)
        self.assertIn("ingest_holdout_scores.py", skill_text)
        self.assertIn("final_comparison.py", skill_text)
        self.assertIn("validate_score_provenance.py", skill_text)
        self.assertIn("validate_score_integrity.py", skill_text)
        self.assertIn("validate_evaluator_replay.py", skill_text)
        self.assertIn("execute_evaluator_replay.py", skill_text)
        self.assertIn("--receipt-dir", skill_text)
        self.assertIn('"trace"', manifest)
        self.assertIn('"policy_modules"', manifest)
        self.assertIn("Policy Modules", task_html)
        self.assertIn("Mechanism Metrics", task_html)
        self.assertTrue((SKILL_DIR / "assets" / "proofline" / "scripts" / "lint_trace.py").is_file())
        self.assertTrue((SKILL_DIR / "assets" / "proofline" / "scripts" / "trace_metrics.py").is_file())
        self.assertTrue((SKILL_DIR / "assets" / "proofline" / "scripts" / "validate_candidate.py").is_file())
        self.assertTrue((SKILL_DIR / "assets" / "proofline" / "scripts" / "validate_evaluation.py").is_file())
        self.assertTrue((SKILL_DIR / "assets" / "proofline" / "scripts" / "release_holdout.py").is_file())
        self.assertTrue((SKILL_DIR / "assets" / "proofline" / "scripts" / "ingest_holdout_scores.py").is_file())
        self.assertTrue((SKILL_DIR / "assets" / "proofline" / "scripts" / "final_comparison.py").is_file())
        self.assertTrue((SKILL_DIR / "assets" / "proofline" / "scripts" / "validate_score_provenance.py").is_file())
        self.assertTrue((SKILL_DIR / "assets" / "proofline" / "scripts" / "validate_score_integrity.py").is_file())
        self.assertTrue((SKILL_DIR / "assets" / "proofline" / "scripts" / "validate_evaluator_replay.py").is_file())
        self.assertTrue((SKILL_DIR / "assets" / "proofline" / "scripts" / "execute_evaluator_replay.py").is_file())
        self.assertTrue((SKILL_DIR / "assets" / "proofline" / "harness" / "policies" / "state.md").is_file())

    def test_installer_refuses_to_overwrite_without_force(self):
        self.assertTrue(INSTALLER.exists(), f"Missing installer: {INSTALLER}")
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target"
            target.joinpath("vendor", "proofline", "scripts").mkdir(parents=True)
            existing = target / "vendor" / "proofline" / "scripts" / "init_run.py"
            existing.write_text("custom\n", encoding="utf-8")

            refused = _run_installer(target)

            self.assertNotEqual(refused.returncode, 0)
            self.assertIn("Refusing to overwrite", refused.stderr)
            self.assertEqual(existing.read_text(encoding="utf-8"), "custom\n")

            forced = _run_installer(target, "--force")

            self.assertEqual(forced.returncode, 0, forced.stderr)
            self.assertNotEqual(existing.read_text(encoding="utf-8"), "custom\n")
            mode = existing.stat().st_mode
            self.assertTrue(mode & stat.S_IXUSR)


def _run_installer(target: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(INSTALLER), "--target", str(target), *extra_args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _write_installed_search_score(score_path: Path, candidate_id: str) -> None:
    score = json.loads(score_path.read_text(encoding="utf-8"))
    score["candidate_id"] = candidate_id
    score["search_scores"] = {
        "task_success": 0.9,
        "audit_completeness": 0.9,
        "cost_tokens": 100,
        "wall_minutes": 2,
        "defect_escape_rate": 0.02,
    }
    score["score_provenance"] = _installed_score_provenance("search-evaluator", "search")
    score_path.write_text(json.dumps(score, indent=2) + "\n", encoding="utf-8")


def _write_installed_evaluator_files(vendor: Path) -> None:
    run_dir = vendor / "runs" / "sample-run"
    artifacts = run_dir / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    (artifacts / "search-input.json").write_text("{}\n", encoding="utf-8")
    (artifacts / "holdout-input.json").write_text("{}\n", encoding="utf-8")
    (artifacts / "search-evidence.txt").write_text("search evidence\n", encoding="utf-8")
    (artifacts / "holdout-evidence.txt").write_text("holdout evidence\n", encoding="utf-8")
    evaluators = run_dir / "evaluators"
    evaluators.mkdir(parents=True, exist_ok=True)
    _write_installed_evaluator_manifest(
        evaluators / "search-evaluator.json",
        "search-evaluator",
        "search",
        [
            "vendor/proofline/runs/sample-run/candidates/baseline/score.json",
            "vendor/proofline/runs/sample-run/candidates/frontier/score.json",
        ],
    )
    _write_installed_evaluator_manifest(
        evaluators / "holdout-evaluator.json",
        "holdout-evaluator",
        "holdout",
        ["vendor/proofline/runs/sample-run/holdout_scores/frontier.json"],
    )


def _write_installed_evaluator_manifest(path: Path, evaluator_id: str, phase: str, output_paths: list[str]) -> None:
    root = path.parents[5]
    input_path = f"vendor/proofline/runs/sample-run/artifacts/{phase}-input.json"
    evidence_path = f"vendor/proofline/runs/sample-run/artifacts/{phase}-evidence.txt"
    output_hashes = {output_path: _digest(root / output_path) for output_path in output_paths}
    path.write_text(
        json.dumps(
            {
                "schema_version": "ciph.evaluator-manifest.v1",
                "evaluator_id": evaluator_id,
                "evaluation_phase": phase,
                "command": f"python3 tools/evaluate.py --phase {phase}",
                "input_paths": [input_path],
                "output_paths": output_paths,
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
                    "output_hashes": output_hashes,
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
                    "expected_output_hashes": output_hashes,
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _installed_score_provenance(evaluator_id: str, phase: str) -> dict[str, object]:
    return {
        "schema_version": "ciph.score-provenance.v1",
        "evaluator_id": evaluator_id,
        "evaluator_manifest_path": f"vendor/proofline/runs/sample-run/evaluators/{evaluator_id}.json",
        "evaluation_phase": phase,
        "produced_at": "2026-05-20T07:00:00Z",
        "input_paths": [f"vendor/proofline/runs/sample-run/artifacts/{phase}-input.json"],
        "evidence_paths": [f"vendor/proofline/runs/sample-run/artifacts/{phase}-evidence.txt"],
    }


if __name__ == "__main__":
    unittest.main()
