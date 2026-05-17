import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.run_status import render_status, write_status


class RunStatusTests(unittest.TestCase):
    def test_render_status_summarizes_lint_manifest_deliverables_and_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = _write_manifest(root)

            output = render_status(manifest_path, root)

            self.assertIn("# CIPH Run Status", output)
            self.assertIn("Task: sample", output)
            self.assertIn("- Lint: PASS", output)
            self.assertIn("- Manifest: PASS", output)
            self.assertIn("- Deliverables: 1/1 covered", output)
            self.assertIn("- Required checks: 1/1 passed", output)
            self.assertIn("unit-tests: PASS", output)

    def test_render_status_marks_lint_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = _write_manifest(root, objective="<original objective>")

            output = render_status(manifest_path, root)

            self.assertIn("- Lint: FAIL", output)
            self.assertIn("objective contains placeholder text", output)

    def test_write_status_creates_report_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = _write_manifest(root)
            output_path = root / "runs" / "sample" / "artifacts" / "status.md"

            write_status(manifest_path, root, output_path)

            self.assertTrue(output_path.is_file())
            self.assertIn("# CIPH Run Status", output_path.read_text(encoding="utf-8"))

    def test_write_status_creates_html_report_when_output_suffix_is_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = _write_manifest(root, objective="Escape <script>alert(1)</script> in status.")
            output_path = root / "runs" / "sample" / "artifacts" / "status.html"

            write_status(manifest_path, root, output_path)

            html = output_path.read_text(encoding="utf-8")
            self.assertTrue(html.startswith("<!doctype html>"))
            self.assertIn('data-proofline-report="status"', html)
            self.assertIn("CIPH Run Status", html)
            self.assertIn("Escape &lt;script&gt;alert(1)&lt;/script&gt; in status.", html)
            self.assertIn("<section", html)

    def test_run_status_script_runs_when_executed_by_file_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = _write_manifest(root)
            output_path = root / "status.md"
            repo_root = Path(__file__).resolve().parents[1]

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_status.py",
                    str(manifest_path),
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
            self.assertIn(f"Wrote CIPH run status: {output_path}", completed.stdout)
            self.assertTrue(output_path.is_file())


def _write_manifest(
    root: Path,
    objective: str = "Produce a status report.",
) -> Path:
    manifest_path = root / "runs" / "sample" / "MANIFEST.json"
    evidence_path = root / "runs" / "sample" / "artifacts" / "checks" / "unit-tests.txt"
    artifact_path = root / "artifact.txt"
    manifest_path.parent.mkdir(parents=True)
    evidence_path.parent.mkdir(parents=True)
    artifact_path.write_text("artifact", encoding="utf-8")
    evidence_path.write_text(
        'CIPH-CHECK-EVIDENCE v1\n'
        '{"check_name": "unit-tests", "command": "python3 -m unittest discover", '
        '"exit_code": 0, "status": "PASS", "generated_by": "scripts/run_checks.py"}\n'
        '\n## STDOUT\n\nOK\n\n## STDERR\n\n<empty>',
        encoding="utf-8",
    )
    payload = {
        "schema_version": "ciph.manifest.v1",
        "task_id": "sample",
        "objective": objective,
        "deliverables": [
            {
                "id": "status-report",
                "requirement": "Produce a status report.",
                "artifact_paths": ["artifact.txt"],
                "evidence_paths": ["runs/sample/artifacts/checks/unit-tests.txt"],
            }
        ],
        "artifacts": [
            {
                "path": "artifact.txt",
                "description": "Sample artifact.",
                "required": True,
            }
        ],
        "checks": [
            {
                "name": "unit-tests",
                "command": "python3 -m unittest discover",
                "required": True,
                "evidence": "runs/sample/artifacts/checks/unit-tests.txt",
                "evidence_producer": "run_checks",
            }
        ],
        "risks": [],
    }
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return manifest_path


if __name__ == "__main__":
    unittest.main()
