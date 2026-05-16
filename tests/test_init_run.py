import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.init_run import initialize_run


class InitRunTests(unittest.TestCase):
    def test_initialize_run_creates_task_manifest_and_artifacts_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_templates(root)

            result = initialize_run("sample-run", root, objective="Ship a useful harness.")

            run_dir = root / "runs" / "sample-run"
            self.assertEqual(run_dir, result.run_dir)
            self.assertTrue((run_dir / "TASK.md").is_file())
            self.assertTrue((run_dir / "MANIFEST.json").is_file())
            self.assertTrue((run_dir / "artifacts").is_dir())
            self.assertTrue((run_dir / "artifacts" / ".gitkeep").is_file())
            self.assertIn("Ship a useful harness.", (run_dir / "TASK.md").read_text(encoding="utf-8"))

            manifest = json.loads((run_dir / "MANIFEST.json").read_text(encoding="utf-8"))
            self.assertEqual("sample-run", manifest["task_id"])
            self.assertEqual("Ship a useful harness.", manifest["objective"])
            self.assertEqual(
                "runs/sample-run/artifacts/verification.md",
                manifest["checks"][0]["evidence"],
            )

    def test_initialize_run_refuses_to_overwrite_existing_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_templates(root)
            initialize_run("sample-run", root, objective="First objective.")

            with self.assertRaises(FileExistsError):
                initialize_run("sample-run", root, objective="Second objective.")

    def test_initialize_run_rejects_unsafe_run_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_templates(root)

            with self.assertRaises(ValueError):
                initialize_run("../escape", root, objective="No path traversal.")

    def test_init_run_script_runs_when_executed_by_file_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_templates(root)
            repo_root = Path(__file__).resolve().parents[1]

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/init_run.py",
                    "cli-run",
                    "--root",
                    str(root),
                    "--objective",
                    "Create from the CLI.",
                ],
                cwd=repo_root,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("Created CIPH run: runs/cli-run", completed.stdout)
            self.assertTrue((root / "runs" / "cli-run" / "TASK.md").is_file())


def _write_templates(root: Path) -> None:
    template_dir = root / "templates"
    template_dir.mkdir()
    template_dir.joinpath("TASK.md").write_text(
        "# CIPH Task\n\n## Objective\n\nState the original user request in concrete terms.\n\n"
        "## Closeout Commands\n\n"
        "python3 scripts/verify_manifest.py runs/<run-id>/MANIFEST.json --root .\n",
        encoding="utf-8",
    )
    template_dir.joinpath("MANIFEST.json").write_text(
        json.dumps(
            {
                "schema_version": "ciph.manifest.v1",
                "task_id": "<run-id>",
                "objective": "<original objective>",
                "deliverables": [
                    {
                        "id": "example",
                        "requirement": "Replace this with a concrete requirement from the prompt.",
                        "artifact_paths": ["path/to/artifact"],
                        "evidence_paths": ["runs/<run-id>/artifacts/verification.md"],
                    }
                ],
                "artifacts": [
                    {
                        "path": "path/to/artifact",
                        "description": "Replace this with the artifact purpose.",
                        "required": True,
                    }
                ],
                "checks": [
                    {
                        "name": "replace-with-check-name",
                        "command": "replace with exact command",
                        "required": True,
                        "evidence": "runs/<run-id>/artifacts/verification.md",
                    }
                ],
                "risks": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
