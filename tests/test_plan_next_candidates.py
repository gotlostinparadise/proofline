import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.plan_next_candidates import plan_next_candidates


class PlanNextCandidatesTests(unittest.TestCase):
    def test_plan_next_candidates_uses_diagnostics_recommendations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            diagnostics = root / "diagnostics.json"
            diagnostics.write_text(
                json.dumps(
                    {
                        "schema_version": "ciph.experience-diagnostics.v1",
                        "findings": [{"id": "trace-missing", "severity": "high"}],
                        "recommendations": [
                            {
                                "id": "trace-contract",
                                "severity": "high",
                                "run_ids": ["alpha"],
                                "suggested_next_action": "Repair trace coverage.",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            payload = plan_next_candidates(diagnostics)

            self.assertEqual("ciph.next-candidate-plan.v1", payload["schema_version"])
            self.assertEqual("next-1-trace-contract", payload["candidate_stubs"][0]["candidate_id"])
            self.assertEqual("state", payload["candidate_stubs"][0]["changed_module"])

    def test_plan_next_candidates_cli_writes_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            diagnostics = root / "diagnostics.json"
            output = root / "plan.html"
            diagnostics.write_text(
                json.dumps(
                    {
                        "schema_version": "ciph.experience-diagnostics.v1",
                        "findings": [],
                        "recommendations": [
                            {
                                "id": "validation-coverage",
                                "severity": "medium",
                                "run_ids": ["alpha"],
                                "suggested_next_action": "Add validation events.",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/plan_next_candidates.py",
                    str(diagnostics),
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
            self.assertIn(f"Wrote CIPH next candidate plan: {output}", completed.stdout)
            self.assertIn('data-proofline-report="next-candidate-plan"', output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
