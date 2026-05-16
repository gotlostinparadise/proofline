# CIPH Closeout Checklist

Task: ciph-v0.8-repo-gate
Objective: Add one deterministic repository health gate for CIPH.
Manifest: runs/ciph-v0.8-repo-gate/MANIFEST.json
Root: .

## Prompt-to-Artifact Checklist

- [COVERED] repo-gate-command: Add scripts/check_repo.py as a deterministic repo health gate.
  - Artifacts: scripts/check_repo.py
  - Evidence: runs/ciph-v0.8-repo-gate/artifacts/checks/focused-repo-gate-tests.txt
- [COVERED] repo-gate-tests: Add tests for clean pass, unit-test failure propagation, missing closeout failure, skip-diff behavior, and direct CLI execution.
  - Artifacts: tests/test_check_repo.py
  - Evidence: runs/ciph-v0.8-repo-gate/artifacts/checks/focused-repo-gate-tests.txt
- [COVERED] docs-flow: Document the repo gate as the default development check.
  - Artifacts: README.md, harness/CIPH.md
  - Evidence: runs/ciph-v0.8-repo-gate/artifacts/checks/full-unit-tests.txt
- [COVERED] dogfood-gate: Run the gate against this checkout and record evidence.
  - Artifacts: runs/ciph-v0.8-repo-gate/artifacts/status.md, runs/ciph-v0.8-repo-gate/artifacts/closeout.md
  - Evidence: runs/ciph-v0.8-repo-gate/artifacts/checks/repo-gate-check.txt
## Required Checks

- [COVERED] focused-repo-gate-tests
  - Command: python3 -m unittest tests.test_check_repo
  - Evidence: runs/ciph-v0.8-repo-gate/artifacts/checks/focused-repo-gate-tests.txt
- [COVERED] full-unit-tests
  - Command: python3 -m unittest discover
  - Evidence: runs/ciph-v0.8-repo-gate/artifacts/checks/full-unit-tests.txt
- [COVERED] repo-gate-check
  - Command: python3 scripts/check_repo.py --skip-diff-check
  - Evidence: runs/ciph-v0.8-repo-gate/artifacts/checks/repo-gate-check.txt

## Risks

- None recorded.

## Manifest Validation

- COVERED: manifest validation passed.
