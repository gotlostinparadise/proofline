# CIPH Task

## Objective

Add run_checks to execute manifest checks and write structured evidence for CIPH v0.3.

## Acceptance Object

The work is acceptable when `scripts/run_checks.py` executes manifest checks, writes structured evidence, required failing checks fail the runner, `verify_manifest.py` rejects malformed or stale runner evidence, docs/templates explain the flow, and this dogfood run closes out with runner-produced evidence.

## Constraints

- Repository rules: keep CIPH file-backed and Python-stdlib-only.
- Files or areas in scope: scripts, tests, templates, README, harness docs, plans, and this run directory.
- Files or areas out of scope: scheduler, parallel execution, timeout policy, remote execution, and custom agent runtime.
- Permissions: local shell command execution from manifest checks.
- Secrets handling: checks must not print secrets into evidence files.

## Volatile Facts To Verify

No external API, pricing, product-limit, or schema fact is required. The feature depends on Python standard-library modules and local repository files.

## Deliverables

| ID | Requirement | Artifact paths | Evidence paths |
| --- | --- | --- | --- |
| run-checks-command | Add `scripts/run_checks.py` to execute manifest checks and write structured evidence. | `scripts/run_checks.py` | `runs/ciph-v0.3-run-checks/artifacts/checks/focused-run-checks-tests.txt` |
| strict-evidence-validation | Make `verify_manifest.py` reject malformed, failed, or stale `run_checks` evidence. | `scripts/verify_manifest.py` | `runs/ciph-v0.3-run-checks/artifacts/checks/focused-run-checks-tests.txt` |
| runner-tests | Add tests for passing checks, failing checks, stale evidence rejection, and direct CLI execution. | `tests/test_run_checks.py` | `runs/ciph-v0.3-run-checks/artifacts/checks/focused-run-checks-tests.txt` |
| docs-and-templates | Document the new run-checks flow and update generated manifest evidence paths. | `README.md`, `harness/CIPH.md`, `templates/MANIFEST.json`, `templates/TASK.md` | `runs/ciph-v0.3-run-checks/artifacts/checks/full-unit-tests.txt` |
| dogfood-run | Dogfood v0.3 with this generated run and runner-produced evidence. | `runs/ciph-v0.3-run-checks/TASK.md`, `runs/ciph-v0.3-run-checks/MANIFEST.json` | `runs/ciph-v0.3-run-checks/artifacts/checks/run-checks-help.txt` |

## Risks And Blockers

- None yet.

## Closeout Commands

```bash
python3 scripts/run_checks.py runs/ciph-v0.3-run-checks/MANIFEST.json --root .
python3 scripts/verify_manifest.py runs/ciph-v0.3-run-checks/MANIFEST.json --root .
python3 scripts/closeout_check.py runs/ciph-v0.3-run-checks/MANIFEST.json --root .
```
