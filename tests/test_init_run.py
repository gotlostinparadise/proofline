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
            self.assertEqual(run_dir / "TASK.html", result.task_path)
            self.assertTrue((run_dir / "TASK.html").is_file())
            self.assertTrue((run_dir / "MANIFEST.json").is_file())
            self.assertTrue((run_dir / "TRACE.jsonl").is_file())
            self.assertEqual("", (run_dir / "TRACE.jsonl").read_text(encoding="utf-8"))
            self.assertTrue((run_dir / "artifacts").is_dir())
            self.assertTrue((run_dir / "artifacts" / ".gitkeep").is_file())
            task_html = (run_dir / "TASK.html").read_text(encoding="utf-8")
            self.assertIn('data-proofline-kind="task"', task_html)
            self.assertIn("Ship a useful harness.", task_html)

            manifest = json.loads((run_dir / "MANIFEST.json").read_text(encoding="utf-8"))
            self.assertEqual("sample-run", manifest["task_id"])
            self.assertEqual("Ship a useful harness.", manifest["objective"])
            self.assertEqual(
                {
                    "schema_version": "ciph.trace.v1",
                    "path": "runs/sample-run/TRACE.jsonl",
                },
                manifest["trace"],
            )
            self.assertEqual(
                "runs/sample-run/artifacts/verification.html",
                manifest["checks"][0]["evidence"],
            )

    def test_initialize_run_falls_back_to_legacy_markdown_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_legacy_templates(root)

            result = initialize_run("legacy-run", root, objective="Keep old runs usable.")

            run_dir = root / "runs" / "legacy-run"
            self.assertEqual(run_dir / "TASK.md", result.task_path)
            self.assertTrue((run_dir / "TASK.md").is_file())
            self.assertTrue((run_dir / "TRACE.jsonl").is_file())
            self.assertIn("Keep old runs usable.", (run_dir / "TASK.md").read_text(encoding="utf-8"))

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
            self.assertTrue((root / "runs" / "cli-run" / "TASK.html").is_file())
            self.assertTrue((root / "runs" / "cli-run" / "TRACE.jsonl").is_file())

    def test_initialize_run_can_keep_state_in_vendor_proofline(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "project"
            proofline_root = project_root / "vendor" / "proofline"
            proofline_root.mkdir(parents=True)
            _write_templates(proofline_root)

            result = initialize_run(
                "vendor-run",
                root=project_root,
                proofline_root=proofline_root,
                objective="Keep Proofline locked in vendor.",
            )

            run_dir = proofline_root / "runs" / "vendor-run"
            self.assertEqual(run_dir, result.run_dir)
            self.assertTrue((run_dir / "TASK.html").is_file())
            self.assertTrue((run_dir / "MANIFEST.json").is_file())
            self.assertTrue((run_dir / "TRACE.jsonl").is_file())
            self.assertIn("Keep Proofline locked in vendor.", (run_dir / "TASK.html").read_text(encoding="utf-8"))

            manifest = json.loads((run_dir / "MANIFEST.json").read_text(encoding="utf-8"))
            self.assertEqual("vendor-run", manifest["task_id"])
            self.assertEqual("runs/vendor-run/TRACE.jsonl", manifest["trace"]["path"])

    def test_repo_templates_include_policy_modules_and_trace_closeout(self):
        repo_root = Path(__file__).resolve().parents[1]
        task_html = (repo_root / "templates" / "TASK.html").read_text(encoding="utf-8")
        task_md = (repo_root / "templates" / "TASK.md").read_text(encoding="utf-8")
        manifest = json.loads((repo_root / "templates" / "MANIFEST.json").read_text(encoding="utf-8"))

        self.assertIn("Policy Modules", task_html)
        self.assertIn("scripts/lint_trace.py", task_html)
        self.assertIn("Policy Modules", task_md)
        self.assertIn("scripts/lint_trace.py", task_md)
        self.assertEqual(
            {
                "schema_version": "ciph.trace.v1",
                "path": "runs/<run-id>/TRACE.jsonl",
            },
            manifest["trace"],
        )


def _write_templates(root: Path) -> None:
    template_dir = root / "templates"
    template_dir.mkdir()
    template_dir.joinpath("TASK.html").write_text(
        '<!doctype html>\n<html lang="en">\n<body data-proofline-kind="task">\n'
        "<h1>CIPH Task</h1>\n"
        '<section id="objective"><h2>Objective</h2><p>State the original user request in concrete terms.</p></section>\n'
        '<section id="closeout"><h2>Closeout Commands</h2><pre>python3 scripts/verify_manifest.py runs/&lt;run-id&gt;/MANIFEST.json --root .</pre></section>\n'
        "</body>\n</html>\n",
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
                        "evidence_paths": ["runs/<run-id>/artifacts/verification.html"],
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
                        "evidence": "runs/<run-id>/artifacts/verification.html",
                    }
                ],
                "risks": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_legacy_templates(root: Path) -> None:
    template_dir = root / "templates"
    template_dir.mkdir()
    template_dir.joinpath("TASK.md").write_text(
        "# CIPH Task\n\n## Objective\n\nState the original user request in concrete terms.\n",
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
                        "id": "legacy",
                        "requirement": "Keep legacy Markdown initialization available.",
                        "artifact_paths": ["runs/<run-id>/TASK.md"],
                        "evidence_paths": ["runs/<run-id>/artifacts/verification.md"],
                    }
                ],
                "artifacts": [
                    {
                        "path": "runs/<run-id>/TASK.md",
                        "description": "Legacy task document.",
                        "required": True,
                    }
                ],
                "checks": [
                    {
                        "name": "legacy-check",
                        "command": "python3 -m unittest",
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
