import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.diagnose_experience_store import diagnose_experience_store


class DiagnoseExperienceStoreTests(unittest.TestCase):
    def test_diagnose_reports_failed_required_checks_and_todo_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_run(
                root,
                run_id="alpha",
                objective="TODO placeholder objective",
                include_trace=True,
                closeout_status="PASS",
                validations=[{"check_name": "unit-tests", "status": "FAIL"}],
            )

            payload = diagnose_experience_store(root=root, runs_dir=root / "runs", min_severity="low")
            finding_ids = {finding["id"] for finding in payload["findings"]}
            recommendations = {rec["id"] for rec in payload["recommendations"]}

            self.assertIn("required-check-failed", finding_ids)
            self.assertIn("weak-contract", finding_ids)
            self.assertIn("recover-check-failures", recommendations)
            self.assertEqual("BLOCKED", payload["execution_control"]["status"])

    def test_diagnose_filters_out_low_findings_when_min_severity_is_medium(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_run(
                root,
                run_id="alpha",
                objective="TODO placeholder objective",
                include_trace=True,
                include_missing_artifact=True,
            )

            medium = diagnose_experience_store(root=root, runs_dir=root / "runs", min_severity="medium")
            finding_ids = {finding["id"] for finding in medium["findings"]}

            self.assertIn("artifact-missing", finding_ids)
            self.assertNotIn("weak-contract", finding_ids)

    def test_diagnose_detects_evaluation_without_replay_receipts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_run(
                root,
                run_id="beta",
                objective="Replay readiness check",
                include_trace=True,
                closeout_status="PASS",
                evaluation=True,
                include_replay_receipt=False,
            )

            payload = diagnose_experience_store(root=root, runs_dir=root / "runs", min_severity="low")
            findings = payload["findings"]

            self.assertIn(
                "evaluation-no-replay-receipts",
                {finding["id"] for finding in findings},
            )
            self.assertIn(
                "replay-readiness",
                {finding["recommendation_id"] for finding in findings},
            )

    def test_cli_writes_json_and_html_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_run(
                root,
                run_id="gamma",
                objective="Diagnostics CLI milestone",
                include_trace=False,
            )
            json_output = root / "diagnostics.json"
            html_output = root / "diagnostics.html"

            completed_json = subprocess.run(
                [
                    sys.executable,
                    "scripts/diagnose_experience_store.py",
                    "--root",
                    str(root),
                    "--runs-dir",
                    str(root / "runs"),
                    "--format",
                    "json",
                    "--output",
                    str(json_output),
                ],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed_json.returncode, 0, completed_json.stderr)
            self.assertEqual(completed_json.stdout.strip(), f"Wrote CIPH experience diagnostics: {json_output}")
            payload = json.loads(json_output.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], "ciph.experience-diagnostics.v1")
            self.assertTrue(payload["findings"])

            completed_html = subprocess.run(
                [
                    sys.executable,
                    "scripts/diagnose_experience_store.py",
                    "--root",
                    str(root),
                    "--runs-dir",
                    str(root / "runs"),
                    "--min-severity",
                    "medium",
                    "--format",
                    "html",
                    "--output",
                    str(html_output),
                ],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed_html.returncode, 0, completed_html.stderr)
            self.assertEqual(completed_html.stdout.strip(), f"Wrote CIPH experience diagnostics: {html_output}")
            html = html_output.read_text(encoding="utf-8")
            self.assertTrue(html.startswith("<!doctype html>"))
            self.assertIn('data-proofline-report="experience-diagnostics"', html)

    def test_cli_fail_on_high_blocks_closeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_run(root, run_id="blocked", objective="Missing trace", include_trace=False)
            output = root / "diagnostics.json"

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/diagnose_experience_store.py",
                    "--root",
                    str(root),
                    "--runs-dir",
                    str(root / "runs"),
                    "--fail-on-high",
                    "--output",
                    str(output),
                ],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 2, completed.stdout + completed.stderr)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual("BLOCKED", payload["execution_control"]["status"])
            self.assertIn("High-severity diagnostics findings exist", completed.stdout)


def _write_run(
    root: Path,
    run_id: str,
    *,
    objective: str,
    include_trace: bool = False,
    closeout_status: str = "PASS",
    validations: list[dict[str, str]] | None = None,
    include_missing_artifact: bool = False,
    include_evidence: bool = True,
    evaluation: bool = False,
    include_replay_receipt: bool = True,
) -> None:
    run_dir = root / "runs" / run_id
    checks_dir = run_dir / "artifacts" / "checks"
    checks_dir.mkdir(parents=True)
    report = run_dir / "artifacts" / "diagnostics.html"
    report.write_text("<html><body>diagnostics</body></html>\n", encoding="utf-8")
    evidence = checks_dir / "unit-tests.txt"
    if include_evidence:
        evidence.write_text("CIPH-CHECK-EVIDENCE v1\n{}\n", encoding="utf-8")

    checks = [
        {
            "name": "unit-tests",
            "command": "python3 -m unittest discover",
            "required": True,
            "evidence": f"runs/{run_id}/artifacts/checks/unit-tests.txt",
        }
    ]
    deliverable = {
        "id": "diagnostics",
        "requirement": "Produce diagnostics outputs and report quality signals.",
        "artifact_paths": [f"runs/{run_id}/artifacts/diagnostics.html"],
        "evidence_paths": [f"runs/{run_id}/artifacts/checks/unit-tests.txt"],
    }
    artifact_list = [
        {
            "path": f"runs/{run_id}/artifacts/diagnostics.html",
            "description": "Diagnostics artifact.",
            "required": True,
        }
    ]
    if include_missing_artifact:
        artifact_list.append(
            {
                "path": f"runs/{run_id}/artifacts/missing.txt",
                "description": "Missing artifact.",
                "required": True,
            }
        )
        deliverable["artifact_paths"].append(f"runs/{run_id}/artifacts/missing.txt")

    manifest = {
        "schema_version": "ciph.manifest.v1",
        "task_id": run_id,
        "objective": objective,
        "trace": {
            "schema_version": "ciph.trace.v1",
            "path": f"runs/{run_id}/TRACE.jsonl",
        },
        "policy_modules": ["harness/policies/state.md"],
        "deliverables": [deliverable],
        "artifacts": artifact_list,
        "checks": checks,
        "risks": [],
    }
    (run_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    if include_trace:
        events = [
            {
                "schema_version": "ciph.trace.v1",
                "event_id": "start",
                "occurred_at": "2026-05-21T00:00:00Z",
                "event_type": "stage.started",
                "stage": "verification",
            }
        ]
        events.extend(
            {
                "schema_version": "ciph.trace.v1",
                "event_id": f"validation-{index}",
                "occurred_at": f"2026-05-21T00:00:0{index}Z",
                "event_type": "validation.completed",
                "check_name": validation["check_name"],
                "status": validation["status"],
            }
            for index, validation in enumerate(validations or [], start=1)
        )
        events.append(
            {
                "schema_version": "ciph.trace.v1",
                "event_id": "closeout",
                "occurred_at": "2026-05-21T00:03:00Z",
                "event_type": "closeout.completed",
                "status": closeout_status,
            }
        )
        (run_dir / "TRACE.jsonl").write_text(
            "\n".join(json.dumps(event) for event in events) + "\n",
            encoding="utf-8",
        )

    if evaluation:
        (run_dir / "EVALUATION.json").write_text(
            json.dumps(
                {
                    "schema_version": "ciph.evaluation.v1",
                    "run_id": run_id,
                    "phase": "search",
                    "frontier_candidate_ids": [],
                    "candidates": [
                        {
                            "candidate_id": "baseline",
                            "evaluation_phase": "search",
                            "score_path": f"runs/{run_id}/candidates/baseline/score.json",
                        }
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    if include_replay_receipt and evaluation:
        receipts_dir = run_dir / "replay_receipts"
        receipts_dir.mkdir()
        (receipts_dir / "search-evaluator-dry-run.json").write_text(
            json.dumps(
                {
                    "schema_version": "ciph.replay-receipt.v1",
                    "evaluator_id": "search-evaluator",
                    "mode": "dry-run",
                    "status": "DRY_RUN",
                    "sandbox_mode": "none",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
