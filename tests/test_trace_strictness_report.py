import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.trace_strictness_report import build_trace_strictness_report


class TraceStrictnessReportTests(unittest.TestCase):
    def test_report_lists_strict_ready_and_strict_error_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_run(root, "ready", strict=True, events=[_event("candidate.created", candidate_id="frontier"), _event("candidate.scored", candidate_id="frontier", score_path="runs/ready/candidates/frontier/score.json")])
            _write_run(root, "needs-repair", strict=False, events=[_event("candidate.scored", candidate_id="frontier", score_path="runs/needs-repair/candidates/frontier/score.json")])

            payload = build_trace_strictness_report(root=root, runs_dir=root / "runs")
            by_id = {record["run_id"]: record for record in payload["runs"]}

            self.assertEqual("ciph.trace-strictness-report.v1", payload["schema_version"])
            self.assertEqual("PASS", by_id["ready"]["strict_status"])
            self.assertEqual("FAIL", by_id["needs-repair"]["strict_status"])
            self.assertEqual(1, payload["summary"]["strict_opt_in_runs"])
            self.assertEqual(1, payload["summary"]["strict_error_runs"])

    def test_cli_writes_html_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_run(root, "ready", strict=True, events=[])
            output = root / "strictness.html"

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/trace_strictness_report.py",
                    "--root",
                    str(root),
                    "--runs-dir",
                    str(root / "runs"),
                    "--format",
                    "html",
                    "--output",
                    str(output),
                ],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn(f"Wrote CIPH trace strictness report: {output}", completed.stdout)
            self.assertIn('data-proofline-report="trace-strictness"', output.read_text(encoding="utf-8"))


def _write_run(root: Path, run_id: str, *, strict: bool, events: list[dict[str, object]]) -> None:
    run_dir = root / "runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "TRACE.jsonl").write_text(
        "\n".join(json.dumps(event, sort_keys=True) for event in events) + ("\n" if events else ""),
        encoding="utf-8",
    )
    (run_dir / "MANIFEST.json").write_text(
        json.dumps(
            {
                "schema_version": "ciph.manifest.v1",
                "task_id": run_id,
                "objective": "Report strictness readiness.",
                "trace": {
                    "schema_version": "ciph.trace.v1",
                    "path": f"runs/{run_id}/TRACE.jsonl",
                    "strict": strict,
                },
                "deliverables": [],
                "artifacts": [],
                "checks": [],
                "risks": [],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _event(event_type: str, **fields):
    payload = {
        "schema_version": "ciph.trace.v1",
        "event_id": f"evt-{event_type}-{len(fields)}",
        "occurred_at": "2026-05-20T00:00:00Z",
        "event_type": event_type,
    }
    payload.update(fields)
    return payload


if __name__ == "__main__":
    unittest.main()
