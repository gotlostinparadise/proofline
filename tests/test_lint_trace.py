import json
import subprocess
import sys
import tempfile
import unittest
from importlib import import_module
from pathlib import Path


def _lint_trace(path: Path, root: Path):
    try:
        module = import_module("scripts.lint_trace")
    except ModuleNotFoundError as exc:
        raise AssertionError("scripts.lint_trace must be importable") from exc
    return module.lint_trace(path, root)


def _lint_trace_strict(path: Path, root: Path):
    try:
        module = import_module("scripts.lint_trace")
    except ModuleNotFoundError as exc:
        raise AssertionError("scripts.lint_trace must be importable") from exc
    return module.lint_trace(path, root, strict=True)


class LintTraceTests(unittest.TestCase):
    def test_valid_trace_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trace_path = root / "runs" / "sample" / "TRACE.jsonl"
            _write_trace(
                trace_path,
                [
                    _event("stage.started", stage="inspect"),
                    _event("tool.result", tool="python3", exit_code=0),
                    _event("validation.completed", check_name="unit-tests", status="PASS", evidence_path="runs/sample/evidence.txt"),
                ],
            )

            result = _lint_trace(trace_path, root)

            self.assertTrue(result.ok, result.errors)
            self.assertEqual([], result.errors)

    def test_empty_trace_passes_for_new_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trace_path = root / "runs" / "sample" / "TRACE.jsonl"
            trace_path.parent.mkdir(parents=True)
            trace_path.write_text("", encoding="utf-8")

            result = _lint_trace(trace_path, root)

            self.assertTrue(result.ok, result.errors)

    def test_invalid_json_is_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trace_path = root / "TRACE.jsonl"
            trace_path.write_text("{bad json}\n", encoding="utf-8")

            result = _lint_trace(trace_path, root)

            self.assertFalse(result.ok)
            self.assertTrue(any("line 1 invalid JSON" in error for error in result.errors))

    def test_unknown_event_type_is_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trace_path = root / "TRACE.jsonl"
            _write_trace(trace_path, [_event("unknown.event")])

            result = _lint_trace(trace_path, root)

            self.assertIn("line 1 event_type is unknown: unknown.event", result.errors)

    def test_required_top_level_fields_are_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trace_path = root / "TRACE.jsonl"
            _write_trace(trace_path, [{"event_type": "stage.started", "stage": "inspect"}])

            result = _lint_trace(trace_path, root)

            self.assertIn("line 1 schema_version must be ciph.trace.v1", result.errors)
            self.assertIn("line 1 event_id must be a non-empty string", result.errors)
            self.assertIn("line 1 occurred_at must be a non-empty string", result.errors)

    def test_missing_event_type_is_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trace_path = root / "TRACE.jsonl"
            event = _event("stage.started", stage="inspect")
            del event["event_type"]
            _write_trace(trace_path, [event])

            result = _lint_trace(trace_path, root)

            self.assertIn("line 1 event_type must be a non-empty string", result.errors)

    def test_event_specific_required_fields_are_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trace_path = root / "TRACE.jsonl"
            _write_trace(trace_path, [_event("validation.completed", check_name="unit-tests")])

            result = _lint_trace(trace_path, root)

            self.assertIn("line 1 validation.completed.status must be present", result.errors)
            self.assertIn("line 1 validation.completed.evidence_path must be present", result.errors)

    def test_lint_trace_script_runs_when_executed_by_file_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trace_path = root / "runs" / "sample" / "TRACE.jsonl"
            _write_trace(trace_path, [_event("closeout.completed", status="PASS")])
            repo_root = Path(__file__).resolve().parents[1]

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/lint_trace.py",
                    str(trace_path),
                    "--root",
                    str(root),
                ],
                cwd=repo_root,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("PASS trace", completed.stdout)

    def test_strict_mode_rejects_duplicate_event_ids_and_unsafe_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trace_path = root / "runs" / "sample" / "TRACE.jsonl"
            _write_trace(
                trace_path,
                [
                    _event("state.written", event_id="same", path="runs/sample/state.json"),
                    _event("state.loaded", event_id="same", path="../state.json"),
                ],
            )

            result = _lint_trace_strict(trace_path, root)

            self.assertFalse(result.ok)
            self.assertTrue(any("event_id duplicates line 1" in error for error in result.errors))
            self.assertIn("line 2 path must be a local path under the root: ../state.json", result.errors)

    def test_strict_mode_rejects_sequence_regressions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trace_path = root / "runs" / "sample" / "TRACE.jsonl"
            _write_trace(
                trace_path,
                [
                    _event("stage.completed", stage="verify", status="PASS"),
                    _event("candidate.scored", candidate_id="frontier", score_path="runs/sample/candidates/frontier/score.json"),
                ],
            )

            result = _lint_trace_strict(trace_path, root)

            self.assertFalse(result.ok)
            self.assertIn("line 1 stage completed before start: verify", result.errors)
            self.assertIn("line 2 candidate scored before creation: frontier", result.errors)


def _event(event_type: str, **fields):
    payload = {
        "schema_version": "ciph.trace.v1",
        "event_id": f"evt-{event_type}",
        "occurred_at": "2026-05-20T00:00:00Z",
        "event_type": event_type,
    }
    event_id = fields.pop("event_id", None)
    if event_id is not None:
        payload["event_id"] = event_id
    payload.update(fields)
    return payload


def _write_trace(path: Path, events: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(event, sort_keys=True) for event in events) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
