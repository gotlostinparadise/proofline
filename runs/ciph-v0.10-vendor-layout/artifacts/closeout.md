# CIPH Closeout Checklist

Task: ciph-v0.10-vendor-layout
Objective: Make Proofline install and operate from a vendored project directory by default.
Manifest: runs/ciph-v0.10-vendor-layout/MANIFEST.json
Root: .

## Prompt-to-Artifact Checklist

- [COVERED] vendor-init: Support creating runs under a separate Proofline root such as vendor/proofline.
  - Artifacts: scripts/init_run.py, tests/test_init_run.py, skills/proofline/assets/proofline/scripts/init_run.py
  - Evidence: runs/ciph-v0.10-vendor-layout/artifacts/checks/vendor-layout-tests.txt
- [COVERED] vendor-gate: Support repo health checks against a custom runs directory.
  - Artifacts: scripts/check_repo.py, tests/test_check_repo.py, skills/proofline/assets/proofline/scripts/check_repo.py
  - Evidence: runs/ciph-v0.10-vendor-layout/artifacts/checks/vendor-layout-tests.txt
- [COVERED] vendor-lint: Derive required check evidence paths from the manifest location instead of assuming root-level runs/.
  - Artifacts: scripts/lint_manifest.py, skills/proofline/assets/proofline/scripts/lint_manifest.py
  - Evidence: runs/ciph-v0.10-vendor-layout/artifacts/checks/vendor-layout-tests.txt
- [COVERED] skill-vendor-install: Make the Proofline Codex skill install into vendor/proofline and document vendor commands.
  - Artifacts: skills/proofline/SKILL.md, skills/proofline/scripts/install_proofline.py, tests/test_proofline_skill.py
  - Evidence: runs/ciph-v0.10-vendor-layout/artifacts/checks/skill-quick-validate.txt, runs/ciph-v0.10-vendor-layout/artifacts/checks/vendor-layout-tests.txt
- [COVERED] local-skill-refresh: Refresh the local Codex Proofline skill from the canonical skill source.
  - Artifacts: skills/proofline/SKILL.md
  - Evidence: runs/ciph-v0.10-vendor-layout/artifacts/checks/local-skill-install.txt
- [COVERED] run-closeout: Record status and closeout for the vendor-layout run.
  - Artifacts: runs/ciph-v0.10-vendor-layout/artifacts/status.md, runs/ciph-v0.10-vendor-layout/artifacts/closeout.md
  - Evidence: runs/ciph-v0.10-vendor-layout/artifacts/checks/vendor-layout-tests.txt
## Required Checks

- [COVERED] vendor-layout-tests
  - Command: python3 -m unittest tests.test_init_run tests.test_check_repo tests.test_lint_manifest tests.test_proofline_skill
  - Evidence: runs/ciph-v0.10-vendor-layout/artifacts/checks/vendor-layout-tests.txt
- [COVERED] skill-quick-validate
  - Command: python3 /home/bm/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/proofline
  - Evidence: runs/ciph-v0.10-vendor-layout/artifacts/checks/skill-quick-validate.txt
- [COVERED] local-skill-install
  - Command: test -f /home/bm/.codex/skills/proofline/SKILL.md && grep -q "vendor/proofline" /home/bm/.codex/skills/proofline/SKILL.md
  - Evidence: runs/ciph-v0.10-vendor-layout/artifacts/checks/local-skill-install.txt

## Risks

- None recorded.

## Manifest Validation

- COVERED: manifest validation passed.
