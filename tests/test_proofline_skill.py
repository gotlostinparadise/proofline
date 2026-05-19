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
            self.assertTrue((vendor / "scripts" / "lint_trace.py").is_file())
            self.assertTrue((vendor / "scripts" / "trace_metrics.py").is_file())
            self.assertTrue((vendor / "harness" / "policies" / "README.md").is_file())
            self.assertTrue(os.access(vendor / "scripts" / "init_run.py", os.X_OK))
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

    def test_bundled_assets_are_trace_aware(self):
        skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        manifest = (SKILL_DIR / "assets" / "proofline" / "templates" / "MANIFEST.json").read_text(encoding="utf-8")
        task_html = (SKILL_DIR / "assets" / "proofline" / "templates" / "TASK.html").read_text(encoding="utf-8")

        self.assertIn("lint_trace.py", skill_text)
        self.assertIn("trace_metrics.py", skill_text)
        self.assertIn('"trace"', manifest)
        self.assertIn('"policy_modules"', manifest)
        self.assertIn("Policy Modules", task_html)
        self.assertIn("Mechanism Metrics", task_html)
        self.assertTrue((SKILL_DIR / "assets" / "proofline" / "scripts" / "lint_trace.py").is_file())
        self.assertTrue((SKILL_DIR / "assets" / "proofline" / "scripts" / "trace_metrics.py").is_file())
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
