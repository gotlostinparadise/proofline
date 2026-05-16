# CIPH Task

## Objective

Add one deterministic repository health gate for CIPH.

## Acceptance Object

The work is acceptable when `scripts/check_repo.py` runs unit tests, lints every manifest, verifies every manifest, rejects missing closeout coverage, optionally runs `git diff --check`, and this run records gate evidence.

## Constraints

- Repository rules: keep the gate deterministic and stdlib-only.
- Files or areas in scope: repo gate script, tests, README, harness docs, and this run.
- Files or areas out of scope: CI provider configuration and automatic evidence regeneration.
- Permissions: local command execution only.
- Secrets handling: no secrets are required.

## Volatile Facts To Verify

No external API, pricing, product-limit, or schema fact is required. The feature depends on local repository files, git, and Python standard-library behavior.

## Deliverables

| ID | Requirement | Artifact paths | Evidence paths |
| --- | --- | --- | --- |
| repo-gate-command | Add `scripts/check_repo.py` as a deterministic repo health gate. | `scripts/check_repo.py` | `runs/ciph-v0.8-repo-gate/artifacts/checks/focused-repo-gate-tests.txt` |
| repo-gate-tests | Add tests for clean pass, missing closeout failure, and direct CLI execution. | `tests/test_check_repo.py` | `runs/ciph-v0.8-repo-gate/artifacts/checks/focused-repo-gate-tests.txt` |
| docs-flow | Document the repo gate as the default development check. | `README.md`, `harness/CIPH.md` | `runs/ciph-v0.8-repo-gate/artifacts/checks/full-unit-tests.txt` |
| dogfood-gate | Run the gate against this checkout and record evidence. | `runs/ciph-v0.8-repo-gate/artifacts/status.md`, `runs/ciph-v0.8-repo-gate/artifacts/closeout.md` | `runs/ciph-v0.8-repo-gate/artifacts/checks/repo-gate-help.txt` |

## Risks And Blockers

- None yet.

## Closeout Commands

```bash
python3 scripts/lint_manifest.py runs/ciph-v0.8-repo-gate/MANIFEST.json --root .
python3 scripts/run_checks.py runs/ciph-v0.8-repo-gate/MANIFEST.json --root .
python3 scripts/verify_manifest.py runs/ciph-v0.8-repo-gate/MANIFEST.json --root .
python3 scripts/check_repo.py --skip-diff-check
python3 scripts/closeout_check.py runs/ciph-v0.8-repo-gate/MANIFEST.json --root .
python3 scripts/run_status.py runs/ciph-v0.8-repo-gate/MANIFEST.json --root . --output runs/ciph-v0.8-repo-gate/artifacts/status.md
python3 scripts/closeout_check.py runs/ciph-v0.8-repo-gate/MANIFEST.json --root . --output runs/ciph-v0.8-repo-gate/artifacts/closeout.md
```
