import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CAPSULE = REPO_ROOT / "capsule.py"


class CapsuleCliTests(unittest.TestCase):
    def test_create_writes_manifest_digests_redactions_files_and_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "README.md", "# Demo\n")
            _write(root / "docs" / "guide.md", "# Guide\n")

            completed = _run_capsule(
                "create",
                "--root",
                str(root),
                "--id",
                "docs-context",
                "--include",
                "README.md",
                "--include",
                "docs/**/*.md",
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            capsule_dir = root / "capsules" / "docs-context"
            self.assertTrue((capsule_dir / "CAPSULE.json").is_file())
            self.assertTrue((capsule_dir / "FILES.txt").is_file())
            self.assertTrue((capsule_dir / "DIGESTS.json").is_file())
            self.assertTrue((capsule_dir / "REDACTIONS.json").is_file())
            self.assertTrue((capsule_dir / "capsule.html").is_file())

            files = (capsule_dir / "FILES.txt").read_text(encoding="utf-8").splitlines()
            self.assertEqual(["README.md", "docs/guide.md"], files)

            manifest = json.loads((capsule_dir / "CAPSULE.json").read_text(encoding="utf-8"))
            self.assertEqual("capsule.v1", manifest["schema_version"])
            self.assertEqual("docs-context", manifest["capsule_id"])
            self.assertEqual(["README.md", "docs/**/*.md"], manifest["selection_rules"]["include"])
            self.assertEqual("DIGESTS.json", manifest["digests_path"])
            self.assertEqual("REDACTIONS.json", manifest["redactions_path"])

    def test_verify_passes_then_fails_after_included_file_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "README.md"
            _write(source, "first\n")

            create = _run_capsule("create", "--root", str(root), "--id", "sample", "--include", "README.md")
            self.assertEqual(create.returncode, 0, create.stderr)

            verify = _run_capsule("verify", str(root / "capsules" / "sample" / "CAPSULE.json"))
            self.assertEqual(verify.returncode, 0, verify.stderr)

            source.write_text("second\n", encoding="utf-8")

            changed = _run_capsule("verify", str(root / "capsules" / "sample" / "CAPSULE.json"))
            self.assertNotEqual(changed.returncode, 0)
            self.assertIn("digest mismatch", changed.stdout + changed.stderr)

    def test_secret_like_warning_records_type_without_leaking_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            secret_value = "sk-test-1234567890abcdef"
            _write(root / "config.env", f"OPENAI_API_KEY={secret_value}\n")

            completed = _run_capsule("create", "--root", str(root), "--id", "secrets", "--include", "config.env")

            self.assertEqual(completed.returncode, 0, completed.stderr)
            redactions_text = (root / "capsules" / "secrets" / "REDACTIONS.json").read_text(encoding="utf-8")
            self.assertNotIn(secret_value, redactions_text)
            redactions = json.loads(redactions_text)
            self.assertEqual(1, len(redactions["warnings"]))
            self.assertEqual("secret-like-content", redactions["warnings"][0]["kind"])
            self.assertEqual("config.env", redactions["warnings"][0]["path"])

    def test_inspect_prints_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "README.md", "# Demo\n")
            create = _run_capsule("create", "--root", str(root), "--id", "sample", "--include", "README.md")
            self.assertEqual(create.returncode, 0, create.stderr)

            inspect = _run_capsule("inspect", str(root / "capsules" / "sample" / "CAPSULE.json"))

            self.assertEqual(inspect.returncode, 0, inspect.stderr)
            self.assertIn("capsule: sample", inspect.stdout)
            self.assertIn("files: 1", inspect.stdout)
            self.assertIn("warnings: 0", inspect.stdout)

    def test_ignore_patterns_exclude_selected_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "keep.txt", "keep\n")
            _write(root / "skip.txt", "skip\n")

            completed = _run_capsule(
                "create",
                "--root",
                str(root),
                "--id",
                "ignored",
                "--include",
                "*.txt",
                "--ignore",
                "skip.txt",
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            files = (root / "capsules" / "ignored" / "FILES.txt").read_text(encoding="utf-8").splitlines()
            self.assertEqual(["keep.txt"], files)


def _run_capsule(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CAPSULE), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
