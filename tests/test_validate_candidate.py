import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.init_candidate import initialize_candidate
from scripts.validate_candidate import validate_candidate, write_candidate_validation


class ValidateCandidateTests(unittest.TestCase):
    def test_validate_candidate_accepts_full_candidate_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate_dir = _create_candidate(root)

            result = validate_candidate(candidate_dir, root=root)

            self.assertTrue(result.ok, result.errors)
            self.assertIn("PASS required file score.json", result.messages)

    def test_validate_candidate_detects_missing_required_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate_dir = _create_candidate(root)
            (candidate_dir / "source" / "README.md").unlink()

            result = validate_candidate(candidate_dir, root=root)

            self.assertFalse(result.ok)
            self.assertIn("missing required file: source/README.md", result.errors)

    def test_validate_candidate_detects_mismatched_candidate_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate_dir = _create_candidate(root)
            score_path = candidate_dir / "score.json"
            score = json.loads(score_path.read_text(encoding="utf-8"))
            score["candidate_id"] = "other"
            score_path.write_text(json.dumps(score, indent=2) + "\n", encoding="utf-8")

            result = validate_candidate(candidate_dir, root=root)

            self.assertFalse(result.ok)
            self.assertIn("score candidate_id must match directory name: baseline", result.errors)

    def test_validate_candidate_lints_candidate_trace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate_dir = _create_candidate(root)
            (candidate_dir / "TRACE.jsonl").write_text("{not-json}\n", encoding="utf-8")

            result = validate_candidate(candidate_dir, root=root)

            self.assertFalse(result.ok)
            self.assertTrue(any("candidate trace line 1 invalid JSON" in error for error in result.errors))

    def test_validate_candidate_detects_missing_declared_artifact_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate_dir = _create_candidate(root)
            score_path = candidate_dir / "score.json"
            score = json.loads(score_path.read_text(encoding="utf-8"))
            score["artifact_paths"].append("runs/sample/candidates/baseline/artifacts/missing.html")
            score_path.write_text(json.dumps(score, indent=2) + "\n", encoding="utf-8")

            result = validate_candidate(candidate_dir, root=root)

            self.assertFalse(result.ok)
            self.assertIn("declared artifact path does not exist: runs/sample/candidates/baseline/artifacts/missing.html", result.errors)

    def test_write_candidate_validation_creates_html_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate_dir = _create_candidate(root)
            output_path = root / "runs" / "sample" / "artifacts" / "candidate-validation.html"

            write_candidate_validation(candidate_dir, output_path, root=root)

            html = output_path.read_text(encoding="utf-8")
            self.assertTrue(html.startswith("<!doctype html>"))
            self.assertIn('data-proofline-report="candidate-validation"', html)
            self.assertIn("PASS required file score.json", html)

    def test_validate_candidate_script_runs_when_executed_by_file_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate_dir = _create_candidate(root)
            output_path = root / "runs" / "sample" / "artifacts" / "candidate-validation.html"
            repo_root = Path(__file__).resolve().parents[1]

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/validate_candidate.py",
                    str(candidate_dir),
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
            self.assertIn(f"PASS candidate {candidate_dir}", completed.stdout)
            self.assertTrue(output_path.is_file())


def _create_candidate(root: Path) -> Path:
    manifest_path = _write_manifest(root)
    initialize_candidate(
        manifest_path,
        "baseline",
        root=root,
        changed_modules=["candidate-search"],
        parent_ids=["seed"],
    )
    return root / "runs" / "sample" / "candidates" / "baseline"


def _write_manifest(root: Path) -> Path:
    manifest_path = root / "runs" / "sample" / "MANIFEST.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "ciph.manifest.v1",
                "task_id": "sample",
                "objective": "Validate candidate records.",
                "deliverables": [],
                "artifacts": [],
                "checks": [],
                "risks": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return manifest_path


if __name__ == "__main__":
    unittest.main()
