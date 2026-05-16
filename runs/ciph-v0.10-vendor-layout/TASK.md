# CIPH Task

## Objective

Make Proofline install and operate from a vendored project directory by default.

## Acceptance Object

The work is acceptable when Proofline can install into `vendor/proofline` by default, create runs in vendored state while checking project-root artifacts, scan vendored run directories in the repo gate, and the local Codex skill reflects the new vendor workflow.

## Constraints

- Repository rules: preserve backward compatibility for existing root-layout Proofline repos.
- Files or areas in scope: Proofline scripts, skill instructions, bundled skill assets, tests, and this run.
- Files or areas out of scope: changing Staffroom product code, changing third-party package managers, and removing root-layout support.
- Permissions: local filesystem writes, tests, commit, push, and local Codex skill update.
- Secrets handling: no secrets are required.

## Volatile Facts To Verify

No external API, pricing, product-limit, or schema facts are required. The change depends on local Python stdlib behavior and Codex skill file layout already present in this repo.

## Deliverables

| ID | Requirement | Artifact paths | Evidence paths |
| --- | --- | --- | --- |
| vendor-init | Support creating runs under a separate Proofline root such as `vendor/proofline`. | `scripts/init_run.py`, `tests/test_init_run.py`, `skills/proofline/assets/proofline/scripts/init_run.py` | `runs/ciph-v0.10-vendor-layout/artifacts/checks/vendor-layout-tests.txt` |
| vendor-gate | Support repo health checks against a custom runs directory. | `scripts/check_repo.py`, `tests/test_check_repo.py`, `skills/proofline/assets/proofline/scripts/check_repo.py` | `runs/ciph-v0.10-vendor-layout/artifacts/checks/vendor-layout-tests.txt` |
| vendor-lint | Derive required check evidence paths from the manifest location instead of assuming root-level `runs/`. | `scripts/lint_manifest.py`, `skills/proofline/assets/proofline/scripts/lint_manifest.py` | `runs/ciph-v0.10-vendor-layout/artifacts/checks/vendor-layout-tests.txt` |
| skill-vendor-install | Make the Proofline Codex skill install into `vendor/proofline` and document vendor commands. | `skills/proofline/SKILL.md`, `skills/proofline/scripts/install_proofline.py`, `tests/test_proofline_skill.py` | `runs/ciph-v0.10-vendor-layout/artifacts/checks/skill-quick-validate.txt`, `runs/ciph-v0.10-vendor-layout/artifacts/checks/vendor-layout-tests.txt` |
| local-skill-refresh | Refresh `/home/bm/.codex/skills/proofline` from the canonical skill source. | `skills/proofline/SKILL.md` | `runs/ciph-v0.10-vendor-layout/artifacts/checks/local-skill-install.txt` |
| run-closeout | Record status and closeout for the vendor-layout run. | `runs/ciph-v0.10-vendor-layout/artifacts/status.md`, `runs/ciph-v0.10-vendor-layout/artifacts/closeout.md` | `runs/ciph-v0.10-vendor-layout/artifacts/checks/vendor-layout-tests.txt` |

## Risks And Blockers

- None yet.

## Closeout Commands

```bash
python3 scripts/lint_manifest.py runs/ciph-v0.10-vendor-layout/MANIFEST.json --root .
python3 scripts/run_checks.py runs/ciph-v0.10-vendor-layout/MANIFEST.json --root .
python3 scripts/verify_manifest.py runs/ciph-v0.10-vendor-layout/MANIFEST.json --root .
python3 scripts/check_repo.py --skip-diff-check
python3 scripts/closeout_check.py runs/ciph-v0.10-vendor-layout/MANIFEST.json --root .
python3 scripts/run_status.py runs/ciph-v0.10-vendor-layout/MANIFEST.json --root . --output runs/ciph-v0.10-vendor-layout/artifacts/status.md
python3 scripts/closeout_check.py runs/ciph-v0.10-vendor-layout/MANIFEST.json --root . --output runs/ciph-v0.10-vendor-layout/artifacts/closeout.md
```
