# CIPH Task

## Objective

Add a quick-start README and init_run command for CIPH v0.2.

## Acceptance Object

The work is acceptable when the repository has a quick-start README, an `init_run.py` command that creates a run from templates, tests for the initializer, and a dogfood run that maps the v0.2 objective to artifacts and evidence.

## Constraints

- Repository rules: keep the harness file-backed and stdlib-only.
- Files or areas in scope: `README.md`, `scripts/init_run.py`, tests, harness docs, and this run directory.
- Files or areas out of scope: custom agent runtime, benchmark optimizer, automatic MCP calls.
- Permissions: local file creation only.
- Secrets handling: no secrets are required.

## Volatile Facts To Verify

No API, pricing, product-limit, or external schema fact is required. Behavior depends only on local Python stdlib APIs and repository files.

## Deliverables

| ID | Requirement | Artifact paths | Evidence paths |
| --- | --- | --- | --- |
| readme-quick-start | Add a README with the exact quick-start flow. | `README.md` | `runs/ciph-v0.2-init-run/artifacts/verification.md` |
| init-run-command | Add `scripts/init_run.py <run-id>` to create a run directory. | `scripts/init_run.py` | `runs/ciph-v0.2-init-run/artifacts/verification.md` |
| init-run-tests | Add tests for init behavior and direct CLI execution. | `tests/test_init_run.py` | `runs/ciph-v0.2-init-run/artifacts/verification.md` |
| dogfood-run | Dogfood the initializer by creating this run. | `runs/ciph-v0.2-init-run/TASK.md`, `runs/ciph-v0.2-init-run/MANIFEST.json` | `runs/ciph-v0.2-init-run/artifacts/verification.md` |

## Risks And Blockers

- None yet.

## Closeout Commands

```bash
python3 scripts/verify_manifest.py runs/ciph-v0.2-init-run/MANIFEST.json --root .
python3 scripts/closeout_check.py runs/ciph-v0.2-init-run/MANIFEST.json --root .
```
