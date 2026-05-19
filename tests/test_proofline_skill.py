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
            self.assertTrue((vendor / "scripts" / "lint_trace.py").is_file())
            self.assertTrue((vendor / "scripts" / "trace_metrics.py").is_file())
            self.assertTrue((vendor / "harness" / "policies" / "README.md").is_file())
            self.assertTrue(os.access(vendor / "scripts" / "init_run.py", os.X_OK))
            self.assertTrue(os.access(vendor / "scripts" / "init_candidate.py", os.X_OK))
            self.assertTrue(os.access(vendor / "scripts" / "validate_candidate.py", os.X_OK))
            self.assertTrue(os.access(vendor / "scripts" / "validate_evaluation.py", os.X_OK))
            self.assertTrue(os.access(vendor / "scripts" / "release_holdout.py", os.X_OK))
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

    def test_bundled_assets_are_trace_aware(self):
        skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        manifest = (SKILL_DIR / "assets" / "proofline" / "templates" / "MANIFEST.json").read_text(encoding="utf-8")
        task_html = (SKILL_DIR / "assets" / "proofline" / "templates" / "TASK.html").read_text(encoding="utf-8")

        self.assertIn("lint_trace.py", skill_text)
        self.assertIn("trace_metrics.py", skill_text)
        self.assertIn("validate_candidate.py", skill_text)
        self.assertIn("validate_evaluation.py", skill_text)
        self.assertIn("release_holdout.py", skill_text)
        self.assertIn('"trace"', manifest)
        self.assertIn('"policy_modules"', manifest)
        self.assertIn("Policy Modules", task_html)
        self.assertIn("Mechanism Metrics", task_html)
        self.assertTrue((SKILL_DIR / "assets" / "proofline" / "scripts" / "lint_trace.py").is_file())
        self.assertTrue((SKILL_DIR / "assets" / "proofline" / "scripts" / "trace_metrics.py").is_file())
        self.assertTrue((SKILL_DIR / "assets" / "proofline" / "scripts" / "validate_candidate.py").is_file())
        self.assertTrue((SKILL_DIR / "assets" / "proofline" / "scripts" / "validate_evaluation.py").is_file())
        self.assertTrue((SKILL_DIR / "assets" / "proofline" / "scripts" / "release_holdout.py").is_file())
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


if __name__ == "__main__":
    unittest.main()
