import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify_manifest import validate_manifest


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def valid_manifest():
    return {
        "schema_version": "ciph.manifest.v1",
        "task_id": "sample",
        "objective": "Build and verify a sample artifact.",
        "deliverables": [
            {
                "id": "html-artifact",
                "requirement": "Produce structured HTML.",
                "artifact_paths": ["index.html"],
                "evidence_paths": ["runs/sample/artifacts/verification.md"],
            }
        ],
        "artifacts": [
            {
                "path": "index.html",
                "description": "Structured HTML artifact.",
                "required": True,
            }
        ],
        "checks": [
            {
                "name": "html-parse",
                "command": "python3 -m unittest",
                "required": True,
                "evidence": "runs/sample/artifacts/verification.md",
            }
        ],
        "risks": [],
    }


class ValidateManifestTests(unittest.TestCase):
    def test_complete_manifest_with_existing_artifact_and_evidence_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / "runs" / "sample" / "MANIFEST.json"
            evidence_path = root / "runs" / "sample" / "artifacts" / "verification.md"
            artifact_path = root / "index.html"
            evidence_path.parent.mkdir(parents=True)
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text("<!doctype html><title>Sample</title>", encoding="utf-8")
            evidence_path.write_text("HTML parse ok", encoding="utf-8")
            write_json(manifest_path, valid_manifest())

            result = validate_manifest(manifest_path, root)

            self.assertTrue(result.ok, result.messages)
            self.assertEqual([], result.errors)

    def test_missing_required_artifact_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / "MANIFEST.json"
            evidence_path = root / "runs" / "sample" / "artifacts" / "verification.md"
            evidence_path.parent.mkdir(parents=True)
            evidence_path.write_text("HTML parse ok", encoding="utf-8")
            write_json(manifest_path, valid_manifest())

            result = validate_manifest(manifest_path, root)

            self.assertFalse(result.ok)
            self.assertIn("Missing required artifact: index.html", result.errors)

    def test_missing_required_check_evidence_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / "MANIFEST.json"
            (root / "index.html").write_text("<!doctype html>", encoding="utf-8")
            write_json(manifest_path, valid_manifest())

            result = validate_manifest(manifest_path, root)

            self.assertFalse(result.ok)
            self.assertIn(
                "Missing required check evidence for html-parse: runs/sample/artifacts/verification.md",
                result.errors,
            )


if __name__ == "__main__":
    unittest.main()
