import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.init_candidate import initialize_candidate


class InitCandidateTests(unittest.TestCase):
    def test_initialize_candidate_creates_score_trace_and_notes_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = _write_manifest(root)

            result = initialize_candidate(
                manifest_path,
                "baseline",
                root=root,
                changed_modules=["verification", "delegation"],
                parent_ids=["seed"],
            )

            candidate_dir = root / "runs" / "sample" / "candidates" / "baseline"
            self.assertEqual(candidate_dir, result.candidate_dir)
            self.assertTrue((candidate_dir / "score.json").is_file())
            self.assertTrue((candidate_dir / "NOTES.md").is_file())
            self.assertTrue((candidate_dir / "patch.diff").is_file())
            self.assertTrue((candidate_dir / "TRACE.jsonl").is_file())
            self.assertTrue((candidate_dir / "policy" / "README.md").is_file())
            self.assertTrue((candidate_dir / "source" / "README.md").is_file())
            self.assertTrue((candidate_dir / "artifacts" / ".gitkeep").is_file())
            self.assertTrue((candidate_dir / "trace" / "prompts.jsonl").is_file())
            self.assertTrue((candidate_dir / "trace" / "tools.jsonl").is_file())
            self.assertTrue((candidate_dir / "trace" / "failures.md").is_file())

            score = json.loads((candidate_dir / "score.json").read_text(encoding="utf-8"))
            self.assertEqual("ciph.candidate.v1", score["schema_version"])
            self.assertEqual("baseline", score["candidate_id"])
            self.assertEqual(["seed"], score["parent_ids"])
            self.assertEqual(["verification", "delegation"], score["changed_modules"])
            self.assertEqual("policy", score["ablation"]["changed_class"])
            self.assertEqual(["policy:verification", "policy:delegation"], score["ablation"]["changed_dimensions"])
            self.assertEqual(["verification", "delegation"], [item["module"] for item in score["policy_provenance"]])
            self.assertEqual([], score["source_provenance"])
            self.assertEqual(["seed"], score["lineage"]["parents"])
            self.assertEqual("State what this candidate is testing.", score["hypothesis"])
            self.assertEqual("runs/sample/candidates/baseline/TRACE.jsonl", score["candidate_trace"])
            self.assertIn("runs/sample/candidates/baseline/TRACE.jsonl", score["trace_paths"])
            self.assertIn("runs/sample/candidates/baseline/policy/README.md", score["artifact_paths"])
            self.assertIn("runs/sample/candidates/baseline/source/README.md", score["artifact_paths"])
            self.assertEqual({}, score["mechanism_metrics"])
            self.assertEqual("unscored", score["pareto_status"])

    def test_initialize_candidate_refuses_to_overwrite_existing_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = _write_manifest(root)
            initialize_candidate(manifest_path, "baseline", root=root)

            with self.assertRaises(FileExistsError):
                initialize_candidate(manifest_path, "baseline", root=root)

    def test_initialize_candidate_uses_manifest_parent_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = _write_manifest(root, run_prefix=("vendor", "proofline", "runs"))

            result = initialize_candidate(manifest_path, "baseline", root=root)

            candidate_dir = root / "vendor" / "proofline" / "runs" / "sample" / "candidates" / "baseline"
            self.assertEqual(candidate_dir, result.candidate_dir)
            score = json.loads((candidate_dir / "score.json").read_text(encoding="utf-8"))
            self.assertEqual("vendor/proofline/runs/sample/candidates/baseline/TRACE.jsonl", score["candidate_trace"])

    def test_initialize_source_candidate_records_source_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = _write_manifest(root)

            initialize_candidate(
                manifest_path,
                "source-candidate",
                root=root,
                changed_modules=["runner"],
                change_class="source",
            )

            candidate_dir = root / "runs" / "sample" / "candidates" / "source-candidate"
            score = json.loads((candidate_dir / "score.json").read_text(encoding="utf-8"))
            self.assertEqual("source", score["ablation"]["changed_class"])
            self.assertEqual(["source:runner"], score["ablation"]["changed_dimensions"])
            self.assertEqual(1, len(score["source_provenance"]))
            snapshot = score["source_provenance"][0]
            self.assertEqual("runs/sample/candidates/source-candidate/source/README.md", snapshot["path"])
            self.assertTrue(snapshot["exists"])
            self.assertTrue(snapshot["sha256"].startswith("sha256:"))
            self.assertTrue(snapshot["loaded_at"])

    def test_initialize_candidate_rejects_unsafe_candidate_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = _write_manifest(root)

            with self.assertRaises(ValueError):
                initialize_candidate(manifest_path, "../escape", root=root)

    def test_init_candidate_script_runs_when_executed_by_file_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = _write_manifest(root)
            repo_root = Path(__file__).resolve().parents[1]

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/init_candidate.py",
                    str(manifest_path),
                    "cli-candidate",
                    "--root",
                    str(root),
                    "--changed-module",
                    "reports",
                    "--parent",
                    "seed",
                    "--source-path",
                    "runs/sample/candidates/cli-candidate/source/README.md",
                ],
                cwd=repo_root,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("Created CIPH candidate: runs/sample/candidates/cli-candidate", completed.stdout)
            self.assertTrue((root / "runs" / "sample" / "candidates" / "cli-candidate" / "score.json").is_file())


def _write_manifest(root: Path, run_prefix: tuple[str, ...] = ("runs",)) -> Path:
    manifest_path = root.joinpath(*run_prefix, "sample", "MANIFEST.json")
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "ciph.manifest.v1",
                "task_id": "sample",
                "objective": "Track candidate traces and scores.",
                "deliverables": [
                    {
                        "id": "candidate",
                        "requirement": "Create candidate records.",
                        "artifact_paths": ["scripts/init_candidate.py"],
                        "evidence_paths": ["runs/sample/artifacts/checks/candidate-tests.txt"],
                    }
                ],
                "artifacts": [
                    {
                        "path": "scripts/init_candidate.py",
                        "description": "Candidate initializer.",
                        "required": True,
                    }
                ],
                "checks": [
                    {
                        "name": "candidate-tests",
                        "command": "python3 -m unittest tests.test_init_candidate",
                        "required": True,
                        "evidence": "runs/sample/artifacts/checks/candidate-tests.txt",
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
