import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.query_experience_store import query_experience_store


class QueryExperienceStoreTests(unittest.TestCase):
    def test_query_indexes_manifest_trace_closeout_and_replay_receipts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_run(root, "alpha", objective="Replay receipt milestone", closeout_status="PASS", receipt_status="PASS")

            payload = query_experience_store(root=root, runs_dir=root / "runs")

            self.assertEqual(payload["schema_version"], "ciph.experience-store.v1")
            self.assertEqual(payload["summary"]["total_runs"], 1)
            record = payload["runs"][0]
            self.assertEqual(record["run_id"], "alpha")
            self.assertEqual(record["objective"], "Replay receipt milestone")
            self.assertEqual(record["closeout_status"], "PASS")
            self.assertEqual(record["trace_event_count"], 3)
            self.assertIn("validation.completed", record["event_types"])
            self.assertIn("verification", record["stages"])
            self.assertEqual(record["deliverable_count"], 1)
            self.assertEqual(record["check_count"], 1)
            self.assertEqual(record["required_artifact_count"], 1)
            self.assertEqual(record["replay_receipts"][0]["status"], "PASS")

    def test_filters_by_status_event_text_replay_receipts_and_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_run(root, "alpha", objective="Replay receipt milestone", closeout_status="PASS", receipt_status="PASS")
            _write_run(root, "beta", objective="Candidate search milestone", closeout_status="FAIL")

            payload = query_experience_store(
                root=root,
                runs_dir=root / "runs",
                status="PASS",
                event_type="validation.completed",
                contains="receipt",
                has_replay_receipts=True,
                limit=1,
            )

            self.assertEqual([record["run_id"] for record in payload["runs"]], ["alpha"])
            self.assertEqual(payload["summary"]["filtered_runs"], 1)

    def test_query_does_not_serialize_check_evidence_bodies(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_run(root, "alpha", objective="Secret-safe evidence", closeout_status="PASS")
            evidence = root / "runs" / "alpha" / "artifacts" / "checks" / "unit-tests.txt"
            evidence.write_text("SECRET_TOKEN=do-not-copy\nstdout body\n", encoding="utf-8")

            payload = query_experience_store(root=root, runs_dir=root / "runs")
            serialized = json.dumps(payload)

            self.assertIn("runs/alpha/artifacts/checks/unit-tests.txt", serialized)
            self.assertNotIn("SECRET_TOKEN", serialized)
            self.assertNotIn("stdout body", serialized)

    def test_cli_writes_json_and_html_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_run(root, "alpha", objective="CLI query milestone", closeout_status="PASS", receipt_status="DRY_RUN")
            repo_root = Path(__file__).resolve().parents[1]
            json_output = root / "experience-store.json"
            html_output = root / "experience-store.html"

            json_completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/query_experience_store.py",
                    "--root",
                    str(root),
                    "--runs-dir",
                    str(root / "runs"),
                    "--status",
                    "PASS",
                    "--format",
                    "json",
                    "--output",
                    str(json_output),
                ],
                cwd=repo_root,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(json_completed.returncode, 0, json_completed.stderr)
            self.assertIn(f"Wrote CIPH experience store query: {json_output}", json_completed.stdout)
            payload = json.loads(json_output.read_text(encoding="utf-8"))
            self.assertEqual(payload["runs"][0]["run_id"], "alpha")

            html_completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/query_experience_store.py",
                    "--root",
                    str(root),
                    "--runs-dir",
                    str(root / "runs"),
                    "--has-replay-receipts",
                    "--format",
                    "html",
                    "--output",
                    str(html_output),
                ],
                cwd=repo_root,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(html_completed.returncode, 0, html_completed.stderr)
            html = html_output.read_text(encoding="utf-8")
            self.assertTrue(html.startswith("<!doctype html>"))
            self.assertIn('data-proofline-report="experience-store"', html)
            self.assertIn("CLI query milestone", html)


def _write_run(
    root: Path,
    run_id: str,
    *,
    objective: str,
    closeout_status: str,
    receipt_status: str | None = None,
) -> None:
    run_dir = root / "runs" / run_id
    checks_dir = run_dir / "artifacts" / "checks"
    checks_dir.mkdir(parents=True)
    artifact = run_dir / "artifacts" / "report.html"
    artifact.write_text("<!doctype html><title>report</title>\n", encoding="utf-8")
    evidence_path = checks_dir / "unit-tests.txt"
    evidence_path.write_text("CIPH-CHECK-EVIDENCE v1\n{}\n\nOK\n", encoding="utf-8")
    manifest = {
        "schema_version": "ciph.manifest.v1",
        "task_id": run_id,
        "objective": objective,
        "trace": {
            "schema_version": "ciph.trace.v1",
            "path": f"runs/{run_id}/TRACE.jsonl",
        },
        "deliverables": [
            {
                "id": "report",
                "requirement": "Write a report.",
                "artifact_paths": [f"runs/{run_id}/artifacts/report.html"],
                "evidence_paths": [f"runs/{run_id}/artifacts/checks/unit-tests.txt"],
            }
        ],
        "artifacts": [
            {
                "path": f"runs/{run_id}/artifacts/report.html",
                "description": "Report artifact.",
                "required": True,
            }
        ],
        "checks": [
            {
                "name": "unit-tests",
                "command": "python3 -m unittest discover",
                "required": True,
                "evidence": f"runs/{run_id}/artifacts/checks/unit-tests.txt",
            }
        ],
        "risks": [],
    }
    (run_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    events = [
        _event("stage.started", "stage-started", stage="verification"),
        _event("validation.completed", "validation", check_name="unit-tests", status=closeout_status),
        _event("closeout.completed", "closeout", status=closeout_status),
    ]
    (run_dir / "TRACE.jsonl").write_text("\n".join(json.dumps(event, sort_keys=True) for event in events) + "\n", encoding="utf-8")
    if receipt_status is not None:
        receipts = run_dir / "replay_receipts"
        receipts.mkdir()
        (receipts / "search-evaluator-dry-run.json").write_text(
            json.dumps(
                {
                    "schema_version": "ciph.replay-receipt.v1",
                    "evaluator_id": "search-evaluator",
                    "mode": "dry-run",
                    "status": receipt_status,
                    "sandbox_mode": "none",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )


def _event(event_type: str, event_id: str, **fields):
    payload = {
        "schema_version": "ciph.trace.v1",
        "event_id": event_id,
        "occurred_at": "2026-05-21T00:00:00Z",
        "event_type": event_type,
    }
    payload.update(fields)
    return payload


if __name__ == "__main__":
    unittest.main()
