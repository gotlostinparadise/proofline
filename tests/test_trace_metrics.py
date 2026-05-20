import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.trace_metrics import calculate_metrics


class TraceMetricsTests(unittest.TestCase):
    def test_calculate_metrics_from_manifest_and_trace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = _write_manifest(root)
            _write_existing_paths(root)
            trace_path = root / "runs" / "sample" / "TRACE.jsonl"
            _write_trace(
                trace_path,
                [
                    _event("stage.started", stage="inspect"),
                    _event("stage.completed", stage="inspect", status="PASS"),
                    _event("stage.started", stage="verify"),
                    _event("model.call", role="planner", input_ref="runs/sample/artifacts/input.json", context_tokens=40),
                    _event("model.result", role="planner", output_ref="runs/sample/artifacts/output.json", output_tokens=10),
                    _event("tool.result", tool="pytest", exit_code=0),
                    _event("tool.result", tool="lint", exit_code=2),
                    _event("stage.completed", stage="verify", status="PASS"),
                    _event("handoff.created", child_id="reviewer", task_path="runs/sample/children/reviewer/TASK.html"),
                    _event("handoff.returned", child_id="reviewer", response_path="runs/sample/children/reviewer/RESPONSE.html"),
                    _event("handoff.reviewed", child_id="reviewer", status="PASS"),
                    _event("validation.completed", check_name="unit-tests", status="PASS", evidence_path="runs/sample/artifacts/checks/unit-tests.txt"),
                    _event("recovery.attempted", strategy="rerun", status="completed", evidence_path="runs/sample/artifacts/checks/unit-tests.txt"),
                ],
            )

            metrics = calculate_metrics(manifest_path, root=root)

            self.assertEqual(1.0, metrics["artifact_contract_compliance"])
            self.assertEqual(1.0, metrics["stage_coverage"])
            self.assertEqual(1.0, metrics["ordered_workflow_compliance"])
            self.assertEqual(0.5, metrics["tool_call_success"])
            self.assertEqual(1.0, metrics["failed_tool_continuation"])
            self.assertEqual(1.0, metrics["handoff_recall"])
            self.assertEqual(1.0, metrics["validation_coverage"])
            self.assertEqual(1.0, metrics["recovery_completion"])
            self.assertEqual(1.0, metrics["model_result_coverage"])
            self.assertEqual(50.0, metrics["context_token_total"])
            self.assertEqual(250.0, metrics["cost_proxy"])
            self.assertEqual(0.0, metrics["declared_runtime_seconds"])
            self.assertEqual(0.0, metrics["declared_cost_total"])
            self.assertEqual(1.0, metrics["recovery_evidence_coverage"])

    def test_calculate_metrics_reads_nested_usage_runtime_and_cost(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = _write_manifest(root)
            _write_existing_paths(root)
            trace_path = root / "runs" / "sample" / "TRACE.jsonl"
            _write_trace(
                trace_path,
                [
                    _event(
                        "model.result",
                        usage={"prompt_tokens": 100, "completion_tokens": 25, "total_tokens": 125},
                        metrics={"runtime_ms": 1500, "estimated_cost_usd": 0.42},
                    ),
                    _event(
                        "tool.result",
                        exit_code=0,
                        metrics={"duration_seconds": 2.0, "cost_usd": 0.08},
                    ),
                ],
            )

            metrics = calculate_metrics(manifest_path, root=root)

            self.assertEqual(125.0, metrics["context_token_total"])
            self.assertEqual(225.0, metrics["cost_proxy"])
            self.assertEqual(3.5, metrics["declared_runtime_seconds"])
            self.assertEqual(0.5, metrics["declared_cost_total"])

    def test_metrics_detect_missing_artifacts_unfinished_stages_and_missing_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = _write_manifest(root)
            (root / "artifact.txt").write_text("artifact", encoding="utf-8")
            trace_path = root / "runs" / "sample" / "TRACE.jsonl"
            _write_trace(
                trace_path,
                [
                    _event("stage.started", stage="inspect"),
                    _event("stage.started", stage="verify"),
                    _event("stage.completed", stage="inspect", status="PASS"),
                    _event("handoff.created", child_id="reviewer", task_path="runs/sample/children/reviewer/TASK.html"),
                ],
            )

            metrics = calculate_metrics(manifest_path, root=root)

            self.assertEqual(0.0, metrics["artifact_contract_compliance"])
            self.assertEqual(0.5, metrics["stage_coverage"])
            self.assertEqual(1.0, metrics["ordered_workflow_compliance"])
            self.assertEqual(0.0, metrics["handoff_recall"])
            self.assertEqual(0.0, metrics["validation_coverage"])

    def test_ordered_workflow_detects_completion_before_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = _write_manifest(root)
            _write_existing_paths(root)
            trace_path = root / "runs" / "sample" / "TRACE.jsonl"
            _write_trace(
                trace_path,
                [
                    _event("stage.completed", stage="verify", status="PASS"),
                    _event("stage.started", stage="verify"),
                ],
            )

            metrics = calculate_metrics(manifest_path, root=root)

            self.assertEqual(0.0, metrics["ordered_workflow_compliance"])

    def test_trace_metrics_script_prints_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = _write_manifest(root)
            _write_existing_paths(root)
            _write_trace(root / "runs" / "sample" / "TRACE.jsonl", [_event("closeout.completed", status="PASS")])
            repo_root = Path(__file__).resolve().parents[1]

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/trace_metrics.py",
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
            payload = json.loads(completed.stdout)
            self.assertIn("artifact_contract_compliance", payload)

    def test_trace_metrics_script_writes_html_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = _write_manifest(root)
            _write_existing_paths(root)
            _write_trace(root / "runs" / "sample" / "TRACE.jsonl", [_event("closeout.completed", status="PASS")])
            output_path = root / "runs" / "sample" / "artifacts" / "mechanism-metrics.html"
            repo_root = Path(__file__).resolve().parents[1]

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/trace_metrics.py",
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
            self.assertIn(f"Wrote CIPH mechanism metrics: {output_path}", completed.stdout)
            html = output_path.read_text(encoding="utf-8")
            self.assertTrue(html.startswith("<!doctype html>"))
            self.assertIn('data-proofline-report="mechanism-metrics"', html)
            self.assertIn("Artifact Contract Compliance", html)

    def test_trace_metrics_script_writes_json_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = _write_manifest(root)
            _write_existing_paths(root)
            _write_trace(root / "runs" / "sample" / "TRACE.jsonl", [_event("closeout.completed", status="PASS")])
            output_path = root / "runs" / "sample" / "artifacts" / "mechanism-metrics.json"
            repo_root = Path(__file__).resolve().parents[1]

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/trace_metrics.py",
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
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertIn("stage_coverage", payload)


def _write_manifest(root: Path) -> Path:
    manifest_path = root / "runs" / "sample" / "MANIFEST.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "ciph.manifest.v1",
        "task_id": "sample",
        "objective": "Measure a sample trace.",
        "trace": {
            "schema_version": "ciph.trace.v1",
            "path": "runs/sample/TRACE.jsonl",
        },
        "deliverables": [
            {
                "id": "artifact",
                "requirement": "Keep artifact and evidence paths.",
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
                "command": "python3 -m unittest",
                "required": True,
                "evidence": "runs/sample/artifacts/checks/unit-tests.txt",
            }
        ],
        "risks": [],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


def _write_existing_paths(root: Path) -> None:
    (root / "artifact.txt").write_text("artifact", encoding="utf-8")
    evidence = root / "runs" / "sample" / "artifacts" / "checks" / "unit-tests.txt"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text("pass", encoding="utf-8")


def _event(event_type: str, **fields):
    payload = {
        "schema_version": "ciph.trace.v1",
        "event_id": f"evt-{event_type}-{len(fields)}",
        "occurred_at": "2026-05-20T00:00:00Z",
        "event_type": event_type,
    }
    payload.update(fields)
    return payload


def _write_trace(path: Path, events: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(event, sort_keys=True) for event in events) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
