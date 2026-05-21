import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.check_repo import check_repo


class CheckRepoTests(unittest.TestCase):
    def test_check_repo_passes_when_tests_manifests_and_closeouts_are_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_test_file(root, passing=True)
            _write_clean_run(root, "sample")

            result = check_repo(root, include_diff_check=False)

            self.assertTrue(result.ok, result.failures)
            self.assertIn("PASS tests", result.messages)
            self.assertIn("PASS lint runs/sample/MANIFEST.json", result.messages)
            self.assertIn("PASS verify runs/sample/MANIFEST.json", result.messages)
            self.assertIn("PASS closeout runs/sample/MANIFEST.json", result.messages)

    def test_check_repo_fails_when_closeout_has_missing_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_test_file(root, passing=True)
            _write_clean_run(root, "sample", create_artifact=False)

            result = check_repo(root, include_diff_check=False)

            self.assertFalse(result.ok)
            self.assertIn("FAIL closeout runs/sample/MANIFEST.json has missing coverage", result.failures)

    def test_check_repo_ignores_missing_optional_check_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_test_file(root, passing=True)
            _write_clean_run(root, "sample", include_optional_check=True)

            result = check_repo(root, include_diff_check=False)

            self.assertTrue(result.ok, result.failures)
            self.assertIn("PASS closeout runs/sample/MANIFEST.json", result.messages)

    def test_check_repo_reports_unit_test_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_test_file(root, passing=False)
            _write_clean_run(root, "sample")

            result = check_repo(root, include_diff_check=False)

            self.assertFalse(result.ok)
            self.assertIn("FAIL tests", result.failures)
            self.assertTrue(any("FAILED" in failure for failure in result.failures), result.failures)

    def test_check_repo_skips_diff_check_when_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_test_file(root, passing=True)
            _write_clean_run(root, "sample")
            _create_dirty_git_diff(root)

            skipped = check_repo(root, include_diff_check=False)
            included = check_repo(root, include_diff_check=True)

            self.assertTrue(skipped.ok, skipped.failures)
            self.assertNotIn("PASS git diff --check", skipped.messages)
            self.assertFalse(included.ok)
            self.assertIn("FAIL git diff --check", included.failures)

    def test_check_repo_script_runs_when_executed_by_file_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_test_file(root, passing=True)
            _write_clean_run(root, "sample")
            repo_root = Path(__file__).resolve().parents[1]

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/check_repo.py",
                    "--root",
                    str(root),
                    "--skip-diff-check",
                ],
                cwd=repo_root,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("CIPH repo gate passed", completed.stdout)

    def test_check_repo_accepts_vendored_runs_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_test_file(root, passing=True)
            _write_clean_run(root, "sample", runs_dir=Path("vendor") / "proofline" / "runs")

            result = check_repo(root, include_diff_check=False, runs_dir=Path("vendor") / "proofline" / "runs")

            self.assertTrue(result.ok, result.failures)
            self.assertIn("PASS lint vendor/proofline/runs/sample/MANIFEST.json", result.messages)
            self.assertIn("PASS closeout vendor/proofline/runs/sample/MANIFEST.json", result.messages)


def _write_test_file(root: Path, passing: bool) -> None:
    tests_dir = root / "tests"
    tests_dir.mkdir()
    tests_dir.joinpath("__init__.py").write_text("", encoding="utf-8")
    tests_dir.joinpath("test_sample.py").write_text(
        "import unittest\n\n"
        "class SampleTests(unittest.TestCase):\n"
        f"    def test_sample(self):\n        self.assertTrue({passing!r})\n",
        encoding="utf-8",
    )


def _create_dirty_git_diff(root: Path) -> None:
    subprocess.run(["git", "init"], cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    tracked = root / "tracked.txt"
    tracked.write_text("clean\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    tracked.write_text("trailing whitespace \n", encoding="utf-8")


def _write_clean_run(
    root: Path,
    run_id: str,
    create_artifact: bool = True,
    runs_dir: Path = Path("runs"),
    include_optional_check: bool = False,
) -> None:
    run_dir = root / runs_dir / run_id
    check_dir = run_dir / "artifacts" / "checks"
    check_dir.mkdir(parents=True)
    if create_artifact:
        (root / "artifact.txt").write_text("artifact", encoding="utf-8")
    evidence_path = check_dir / "unit-tests.txt"
    evidence_path.write_text(
        'CIPH-CHECK-EVIDENCE v1\n'
        '{"check_name": "unit-tests", "command": "python3 -m unittest discover", '
        '"exit_code": 0, "status": "PASS", "generated_by": "scripts/run_checks.py"}\n'
        '\n## STDOUT\n\nOK\n\n## STDERR\n\n<empty>',
        encoding="utf-8",
    )
    checks = [
        {
            "name": "unit-tests",
            "command": "python3 -m unittest discover",
            "required": True,
            "evidence": f"{runs_dir.as_posix()}/{run_id}/artifacts/checks/unit-tests.txt",
            "evidence_producer": "run_checks",
        }
    ]
    if include_optional_check:
        checks.append(
            {
                "name": "optional-check",
                "command": "python3 -m unittest discover",
                "required": False,
                "evidence": f"{runs_dir.as_posix()}/{run_id}/artifacts/checks/optional-check.txt",
                "evidence_producer": "run_checks",
            }
        )

    manifest = {
        "schema_version": "ciph.manifest.v1",
        "task_id": run_id,
        "objective": "Gate the repository.",
        "deliverables": [
            {
                "id": "repo-gate",
                "requirement": "Gate the repository.",
                "artifact_paths": ["artifact.txt"],
                "evidence_paths": [f"{runs_dir.as_posix()}/{run_id}/artifacts/checks/unit-tests.txt"],
            }
        ],
        "artifacts": [
            {
                "path": "artifact.txt",
                "description": "Sample artifact.",
                "required": True,
            }
        ],
        "checks": checks,
        "risks": [],
    }
    run_dir.joinpath("MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
