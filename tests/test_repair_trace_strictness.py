import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.repair_trace_strictness import build_trace_repair_plan


class RepairTraceStrictnessTests(unittest.TestCase):
    def test_repair_plan_suggests_candidate_and_validation_inserts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = root / "strictness.json"
            report.write_text(
                json.dumps(
                    {
                        "schema_version": "ciph.trace-strictness-report.v1",
                        "runs": [
                            {
                                "run_id": "sample",
                                "trace_path": "runs/sample/TRACE.jsonl",
                                "strict_status": "FAIL",
                                "errors": ["line 4 candidate scored before creation: frontier"],
                                "warnings": ["line 8 validation completed without validation.started: unit-tests"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            payload = build_trace_repair_plan(report)
            suggestions = payload["repairs"][0]["suggestions"]

            self.assertEqual("ciph.trace-repair-plan.v1", payload["schema_version"])
            self.assertEqual(2, payload["summary"]["suggestions"])
            self.assertEqual("candidate.created", suggestions[0]["event_type"])
            self.assertEqual({"candidate_id": "frontier"}, suggestions[0]["event_fields"])
            self.assertEqual("validation.started", suggestions[1]["event_type"])
            self.assertEqual({"check_name": "unit-tests"}, suggestions[1]["event_fields"])

    def test_repair_plan_cli_writes_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = root / "strictness.json"
            output = root / "repair.html"
            report.write_text(
                json.dumps(
                    {
                        "schema_version": "ciph.trace-strictness-report.v1",
                        "runs": [
                            {
                                "run_id": "sample",
                                "trace_path": "runs/sample/TRACE.jsonl",
                                "strict_status": "FAIL",
                                "errors": ["line 2 candidate scored before creation: frontier"],
                                "warnings": [],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/repair_trace_strictness.py",
                    str(report),
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
            self.assertIn(f"Wrote CIPH trace repair plan: {output}", completed.stdout)
            self.assertIn('data-proofline-report="trace-repair-plan"', output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
