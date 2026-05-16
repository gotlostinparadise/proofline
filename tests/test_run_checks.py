import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.run_checks import run_checks
from scripts.verify_manifest import validate_manifest


class RunChecksTests(unittest.TestCase):
    def test_run_checks_writes_structured_evidence_for_passing_required_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = _write_manifest(
                root,
                [
                    {
                        "name": "hello-check",
                        "command": f"{sys.executable} -c \"print('hello from check')\"",
                        "required": True,
                        "evidence": "runs/sample/artifacts/checks/hello-check.txt",
                        "evidence_producer": "run_checks",
                    }
                ],
            )

            result = run_checks(manifest_path, root)

            evidence = root / "runs" / "sample" / "artifacts" / "checks" / "hello-check.txt"
            self.assertTrue(result.ok, result)
            self.assertTrue(evidence.is_file())
            text = evidence.read_text(encoding="utf-8")
            self.assertIn("CIPH-CHECK-EVIDENCE v1", text)
            self.assertIn('"check_name": "hello-check"', text)
            self.assertIn('"exit_code": 0', text)
            self.assertIn("hello from check", text)

            manifest_result = validate_manifest(manifest_path, root)
            self.assertTrue(manifest_result.ok, manifest_result.messages)

    def test_run_checks_fails_when_required_command_fails_but_still_writes_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = _write_manifest(
                root,
                [
                    {
                        "name": "failing-check",
                        "command": f"{sys.executable} -c \"import sys; print('bad'); sys.exit(3)\"",
                        "required": True,
                        "evidence": "runs/sample/artifacts/checks/failing-check.txt",
                        "evidence_producer": "run_checks",
                    }
                ],
            )

            result = run_checks(manifest_path, root)

            evidence = root / "runs" / "sample" / "artifacts" / "checks" / "failing-check.txt"
            self.assertFalse(result.ok)
            self.assertEqual(3, result.checks[0].exit_code)
            self.assertTrue(evidence.is_file())
            self.assertIn('"status": "FAIL"', evidence.read_text(encoding="utf-8"))

            manifest_result = validate_manifest(manifest_path, root)
            self.assertFalse(manifest_result.ok)
            self.assertIn(
                "run_checks evidence for failing-check did not pass: runs/sample/artifacts/checks/failing-check.txt",
                manifest_result.errors,
            )

    def test_validate_manifest_rejects_stale_run_checks_evidence_for_changed_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = root / "runs" / "sample" / "artifacts" / "checks" / "hello-check.txt"
            evidence.parent.mkdir(parents=True)
            evidence.write_text(
                'CIPH-CHECK-EVIDENCE v1\n'
                '{"check_name": "hello-check", "command": "old command", '
                '"exit_code": 0, "status": "PASS", "generated_by": "scripts/run_checks.py"}\n',
                encoding="utf-8",
            )
            manifest_path = _write_manifest(
                root,
                [
                    {
                        "name": "hello-check",
                        "command": "new command",
                        "required": True,
                        "evidence": "runs/sample/artifacts/checks/hello-check.txt",
                        "evidence_producer": "run_checks",
                    }
                ],
            )

            result = validate_manifest(manifest_path, root)

            self.assertFalse(result.ok)
            self.assertIn(
                "run_checks evidence for hello-check does not match manifest command: runs/sample/artifacts/checks/hello-check.txt",
                result.errors,
            )

    def test_run_checks_script_runs_when_executed_by_file_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = _write_manifest(
                root,
                [
                    {
                        "name": "cli-check",
                        "command": f"{sys.executable} -c \"print('cli ok')\"",
                        "required": True,
                        "evidence": "runs/sample/artifacts/checks/cli-check.txt",
                        "evidence_producer": "run_checks",
                    }
                ],
            )
            repo_root = Path(__file__).resolve().parents[1]

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_checks.py",
                    str(manifest_path),
                    "--root",
                    str(root),
                ],
                cwd=repo_root,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("PASS cli-check", completed.stdout)
            self.assertTrue((root / "runs" / "sample" / "artifacts" / "checks" / "cli-check.txt").is_file())


def _write_manifest(root: Path, checks: list[dict[str, object]]) -> Path:
    manifest_path = root / "runs" / "sample" / "MANIFEST.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    artifact = root / "artifact.txt"
    artifact.write_text("artifact", encoding="utf-8")
    payload = {
        "schema_version": "ciph.manifest.v1",
        "task_id": "sample",
        "objective": "Run executable checks.",
        "deliverables": [
            {
                "id": "artifact",
                "requirement": "Keep an artifact and check evidence.",
                "artifact_paths": ["artifact.txt"],
                "evidence_paths": [checks[0]["evidence"]],
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
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return manifest_path


if __name__ == "__main__":
    unittest.main()
