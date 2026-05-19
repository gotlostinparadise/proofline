import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.lint_manifest import lint_manifest


class LintManifestTests(unittest.TestCase):
    def test_clean_runner_manifest_has_no_errors_or_warnings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = _write_manifest(root)

            result = lint_manifest(manifest_path, root)

            self.assertEqual([], result.errors)
            self.assertEqual([], result.warnings)

    def test_placeholder_manifest_fields_are_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = _write_manifest(
                root,
                task_id="<run-id>",
                objective="<original objective>",
                deliverables=[
                    {
                        "id": "example",
                        "requirement": "Replace this with a concrete requirement from the prompt.",
                        "artifact_paths": ["path/to/artifact"],
                        "evidence_paths": ["runs/<run-id>/artifacts/checks/example.txt"],
                    }
                ],
            )

            result = lint_manifest(manifest_path, root)

            self.assertFalse(result.ok)
            self.assertIn("ERROR task_id contains placeholder text: <run-id>", result.errors)
            self.assertIn("ERROR objective contains placeholder text: <original objective>", result.errors)
            self.assertIn("ERROR deliverables[1].id contains placeholder text: example", result.errors)
            self.assertIn(
                "ERROR deliverables[1].requirement contains placeholder text: Replace this with a concrete requirement from the prompt.",
                result.errors,
            )

    def test_deliverables_without_artifacts_or_evidence_are_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = _write_manifest(
                root,
                deliverables=[
                    {
                        "id": "missing-links",
                        "requirement": "Record concrete artifact and evidence links.",
                        "artifact_paths": [],
                        "evidence_paths": [],
                    }
                ],
            )

            result = lint_manifest(manifest_path, root)

            self.assertIn("ERROR deliverable missing-links must list at least one artifact path", result.errors)
            self.assertIn("ERROR deliverable missing-links must list at least one evidence path", result.errors)

    def test_required_check_without_run_checks_is_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = _write_manifest(
                root,
                checks=[
                    {
                        "name": "manual-check",
                        "command": "python3 -m unittest discover",
                        "required": True,
                        "evidence": "runs/sample/artifacts/checks/manual-check.txt",
                    }
                ],
            )

            result = lint_manifest(manifest_path, root)

            self.assertEqual([], result.errors)
            self.assertIn(
                "WARN required check manual-check should use evidence_producer: run_checks",
                result.warnings,
            )

    def test_required_check_evidence_must_live_under_run_checks_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = _write_manifest(
                root,
                checks=[
                    {
                        "name": "bad-evidence-path",
                        "command": "python3 -m unittest discover",
                        "required": True,
                        "evidence": "runs/sample/artifacts/verification.md",
                        "evidence_producer": "run_checks",
                    }
                ],
            )

            result = lint_manifest(manifest_path, root)

            self.assertIn(
                "ERROR required check bad-evidence-path evidence must be under runs/sample/artifacts/checks/",
                result.errors,
            )

    def test_duplicate_paths_inside_one_deliverable_are_warnings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = _write_manifest(
                root,
                deliverables=[
                    {
                        "id": "duplicate-links",
                        "requirement": "Avoid duplicate links in one deliverable.",
                        "artifact_paths": ["artifact.txt", "artifact.txt"],
                        "evidence_paths": [
                            "runs/sample/artifacts/checks/unit-tests.txt",
                            "runs/sample/artifacts/checks/unit-tests.txt",
                        ],
                    }
                ],
            )

            result = lint_manifest(manifest_path, root)

            self.assertIn("WARN deliverable duplicate-links repeats artifact path: artifact.txt", result.warnings)
            self.assertIn(
                "WARN deliverable duplicate-links repeats evidence path: runs/sample/artifacts/checks/unit-tests.txt",
                result.warnings,
            )

    def test_trace_manifest_requires_policy_modules(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = _write_manifest(root, trace={"schema_version": "ciph.trace.v1", "path": "runs/sample/TRACE.jsonl"})

            result = lint_manifest(manifest_path, root)

            self.assertIn("ERROR trace-enabled manifest must list at least one policy module", result.errors)

    def test_trace_manifest_accepts_policy_modules(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = _write_manifest(
                root,
                trace={"schema_version": "ciph.trace.v1", "path": "runs/sample/TRACE.jsonl"},
                policy_modules=["harness/policies/state.md"],
            )

            result = lint_manifest(manifest_path, root)

            self.assertEqual([], result.errors)

    def test_lint_manifest_script_runs_when_executed_by_file_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = _write_manifest(root)
            repo_root = Path(__file__).resolve().parents[1]

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/lint_manifest.py",
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
            self.assertIn("CIPH manifest lint clean", completed.stdout)


def _write_manifest(
    root: Path,
    task_id: str = "sample",
    objective: str = "Keep the manifest specific and executable.",
    deliverables: list[dict[str, object]] | None = None,
    checks: list[dict[str, object]] | None = None,
    trace: dict[str, object] | None = None,
    policy_modules: list[str] | None = None,
) -> Path:
    manifest_path = root / "runs" / "sample" / "MANIFEST.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "ciph.manifest.v1",
        "task_id": task_id,
        "objective": objective,
        "deliverables": deliverables
        if deliverables is not None
        else [
            {
                "id": "runner-evidence",
                "requirement": "Record runner evidence for a concrete check.",
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
        "checks": checks
        if checks is not None
        else [
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
    if trace is not None:
        payload["trace"] = trace
    if policy_modules is not None:
        payload["policy_modules"] = policy_modules
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return manifest_path


if __name__ == "__main__":
    unittest.main()
