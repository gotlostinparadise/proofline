import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.init_child_task import initialize_child_task


class InitChildTaskTests(unittest.TestCase):
    def test_initialize_child_task_creates_packet_workspace_and_response_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = _write_parent_manifest(root)

            result = initialize_child_task(
                manifest_path,
                "docs-worker",
                root=root,
                title="Document the child workflow.",
                owner="worker-docs",
                write_scopes=["README.md", "harness/CIPH.md"],
            )

            child_dir = root / "runs" / "sample" / "children" / "docs-worker"
            self.assertEqual(child_dir, result.child_dir)
            self.assertTrue((child_dir / "TASK.md").is_file())
            self.assertTrue((child_dir / "RESPONSE.md").is_file())
            self.assertTrue((child_dir / "OWNERSHIP.json").is_file())
            self.assertTrue((child_dir / "inputs").is_dir())
            self.assertTrue((child_dir / "scratch").is_dir())
            self.assertTrue((child_dir / "artifacts").is_dir())

            task_text = (child_dir / "TASK.md").read_text(encoding="utf-8")
            self.assertIn("Document the child workflow.", task_text)
            self.assertIn("worker-docs", task_text)
            self.assertIn("README.md", task_text)
            self.assertIn("You are not alone in this codebase", task_text)

            ownership = json.loads((child_dir / "OWNERSHIP.json").read_text(encoding="utf-8"))
            self.assertEqual("sample", ownership["parent_task_id"])
            self.assertEqual("docs-worker", ownership["child_id"])
            self.assertEqual(["README.md", "harness/CIPH.md"], ownership["write_scopes"])

    def test_initialize_child_task_refuses_to_overwrite_existing_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = _write_parent_manifest(root)
            initialize_child_task(manifest_path, "docs-worker", root=root, title="First")

            with self.assertRaises(FileExistsError):
                initialize_child_task(manifest_path, "docs-worker", root=root, title="Second")

    def test_initialize_child_task_rejects_unsafe_child_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = _write_parent_manifest(root)

            with self.assertRaises(ValueError):
                initialize_child_task(manifest_path, "../escape", root=root, title="Unsafe")

    def test_init_child_task_script_runs_when_executed_by_file_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = _write_parent_manifest(root)
            repo_root = Path(__file__).resolve().parents[1]

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/init_child_task.py",
                    str(manifest_path),
                    "cli-worker",
                    "--root",
                    str(root),
                    "--title",
                    "CLI child task.",
                    "--owner",
                    "worker-cli",
                    "--write-scope",
                    "scripts/init_child_task.py",
                ],
                cwd=repo_root,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("Created CIPH child task: runs/sample/children/cli-worker", completed.stdout)
            self.assertTrue((root / "runs" / "sample" / "children" / "cli-worker" / "TASK.md").is_file())


def _write_parent_manifest(root: Path) -> Path:
    manifest_path = root / "runs" / "sample" / "MANIFEST.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "ciph.manifest.v1",
                "task_id": "sample",
                "objective": "Coordinate bounded child work.",
                "deliverables": [
                    {
                        "id": "child-workflow",
                        "requirement": "Create child task scaffolding.",
                        "artifact_paths": ["scripts/init_child_task.py"],
                        "evidence_paths": ["runs/sample/artifacts/checks/child-tests.txt"],
                    }
                ],
                "artifacts": [
                    {
                        "path": "scripts/init_child_task.py",
                        "description": "Child task initializer.",
                        "required": True,
                    }
                ],
                "checks": [
                    {
                        "name": "child-tests",
                        "command": "python3 -m unittest tests.test_init_child_task",
                        "required": True,
                        "evidence": "runs/sample/artifacts/checks/child-tests.txt",
                        "evidence_producer": "run_checks",
                    }
                ],
                "risks": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return manifest_path


if __name__ == "__main__":
    unittest.main()
