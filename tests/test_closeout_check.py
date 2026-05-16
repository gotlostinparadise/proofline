import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.closeout_check import render_closeout


class CloseoutCheckTests(unittest.TestCase):
    def test_render_closeout_maps_deliverables_to_artifacts_and_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = {
                "schema_version": "ciph.manifest.v1",
                "task_id": "sample",
                "objective": "Build and verify a sample artifact.",
                "deliverables": [
                    {
                        "id": "html-artifact",
                        "requirement": "Produce structured HTML.",
                        "artifact_paths": ["index.html"],
                        "evidence_paths": ["runs/sample/artifacts/verification.md"],
                    }
                ],
                "artifacts": [
                    {
                        "path": "index.html",
                        "description": "Structured HTML artifact.",
                        "required": True,
                    }
                ],
                "checks": [
                    {
                        "name": "html-parse",
                        "command": "python3 -m unittest",
                        "required": True,
                        "evidence": "runs/sample/artifacts/verification.md",
                    }
                ],
                "risks": [],
            }
            manifest_path = root / "MANIFEST.json"
            artifact_path = root / "index.html"
            evidence_path = root / "runs" / "sample" / "artifacts" / "verification.md"
            evidence_path.parent.mkdir(parents=True)
            artifact_path.write_text("<!doctype html><title>Sample</title>", encoding="utf-8")
            evidence_path.write_text("HTML parse ok", encoding="utf-8")
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

            output = render_closeout(manifest_path, root)

            self.assertIn("# CIPH Closeout Checklist", output)
            self.assertIn("Build and verify a sample artifact.", output)
            self.assertIn("html-artifact", output)
            self.assertIn("Produce structured HTML.", output)
            self.assertIn("index.html", output)
            self.assertIn("runs/sample/artifacts/verification.md", output)
            self.assertIn("COVERED", output)

    def test_closeout_script_runs_when_executed_by_file_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / "MANIFEST.json"
            evidence_path = root / "runs" / "sample" / "artifacts" / "verification.md"
            evidence_path.parent.mkdir(parents=True)
            (root / "index.html").write_text("<!doctype html>", encoding="utf-8")
            evidence_path.write_text("HTML parse ok", encoding="utf-8")
            manifest_path.write_text(
                json.dumps(
                    {
                        "schema_version": "ciph.manifest.v1",
                        "task_id": "sample",
                        "objective": "Build and verify a sample artifact.",
                        "deliverables": [
                            {
                                "id": "html-artifact",
                                "requirement": "Produce structured HTML.",
                                "artifact_paths": ["index.html"],
                                "evidence_paths": ["runs/sample/artifacts/verification.md"],
                            }
                        ],
                        "artifacts": [
                            {
                                "path": "index.html",
                                "description": "Structured HTML artifact.",
                                "required": True,
                            }
                        ],
                        "checks": [
                            {
                                "name": "html-parse",
                                "command": "python3 -m unittest",
                                "required": True,
                                "evidence": "runs/sample/artifacts/verification.md",
                            }
                        ],
                        "risks": [],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            repo_root = Path(__file__).resolve().parents[1]
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/closeout_check.py",
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
            self.assertIn("CIPH Closeout Checklist", completed.stdout)

    def test_closeout_script_writes_output_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / "MANIFEST.json"
            output_path = root / "closeout.md"
            evidence_path = root / "runs" / "sample" / "artifacts" / "verification.md"
            evidence_path.parent.mkdir(parents=True)
            (root / "index.html").write_text("<!doctype html>", encoding="utf-8")
            evidence_path.write_text("HTML parse ok", encoding="utf-8")
            manifest_path.write_text(
                json.dumps(
                    {
                        "schema_version": "ciph.manifest.v1",
                        "task_id": "sample",
                        "objective": "Build and verify a sample artifact.",
                        "deliverables": [
                            {
                                "id": "html-artifact",
                                "requirement": "Produce structured HTML.",
                                "artifact_paths": ["index.html"],
                                "evidence_paths": ["runs/sample/artifacts/verification.md"],
                            }
                        ],
                        "artifacts": [
                            {
                                "path": "index.html",
                                "description": "Structured HTML artifact.",
                                "required": True,
                            }
                        ],
                        "checks": [
                            {
                                "name": "html-parse",
                                "command": "python3 -m unittest",
                                "required": True,
                                "evidence": "runs/sample/artifacts/verification.md",
                            }
                        ],
                        "risks": [],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            repo_root = Path(__file__).resolve().parents[1]
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/closeout_check.py",
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
            self.assertIn(f"Wrote CIPH closeout checklist: {output_path}", completed.stdout)
            self.assertIn("CIPH Closeout Checklist", output_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
