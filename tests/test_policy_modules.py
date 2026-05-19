import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_DIR = REPO_ROOT / "harness" / "policies"
POLICY_FILES = [
    "README.md",
    "state.md",
    "context.md",
    "verification.md",
    "recovery.md",
    "delegation.md",
    "candidate-search.md",
    "stopping.md",
]
REQUIRED_MARKERS = [
    "Policy ID",
    "Version",
    "Purpose",
    "Trigger",
    "State",
    "Evidence",
    "Ablation",
    "Deterministic Hooks",
]


class PolicyModuleTests(unittest.TestCase):
    def test_policy_modules_exist_with_required_sections(self):
        for filename in POLICY_FILES:
            with self.subTest(filename=filename):
                path = POLICY_DIR / filename
                self.assertTrue(path.is_file(), f"missing policy module: {path}")
                content = path.read_text(encoding="utf-8")
                for marker in REQUIRED_MARKERS:
                    self.assertIn(marker, content)


if __name__ == "__main__":
    unittest.main()
