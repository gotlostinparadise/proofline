# CIPH Task

## Objective

Add bounded child-task packet and workspace scaffolding for delegated CIPH work.

## Acceptance Object

The work is acceptable when `scripts/init_child_task.py` creates bounded child packets, ownership metadata, child work directories, and response templates; docs explain the command; and this run includes a dogfood child packet.

## Constraints

- Repository rules: create scaffolding only; do not spawn actual agents.
- Files or areas in scope: child task script, child templates, tests, README, harness docs, and this run.
- Files or areas out of scope: agent execution, merge automation, and concurrent work scheduling.
- Permissions: local file writes only.
- Secrets handling: no secrets are required.

## Volatile Facts To Verify

No external API, pricing, product-limit, or schema fact is required. The feature depends on local repository files and Python standard-library behavior.

## Deliverables

| ID | Requirement | Artifact paths | Evidence paths |
| --- | --- | --- | --- |
| child-command | Add `scripts/init_child_task.py` to create child task packets. | `scripts/init_child_task.py` | `runs/ciph-v0.6-child-tasks/artifacts/checks/focused-child-tests.txt` |
| child-templates | Add child task and response templates. | `templates/CHILD_TASK.md`, `templates/CHILD_RESPONSE.md` | `runs/ciph-v0.6-child-tasks/artifacts/checks/full-unit-tests.txt` |
| child-tests | Add tests for creation, overwrite refusal, unsafe IDs, and direct CLI execution. | `tests/test_init_child_task.py` | `runs/ciph-v0.6-child-tasks/artifacts/checks/focused-child-tests.txt` |
| docs-flow | Document child task creation. | `README.md`, `harness/CIPH.md` | `runs/ciph-v0.6-child-tasks/artifacts/checks/full-unit-tests.txt` |
| dogfood-child | Create a bounded child packet for this run. | `runs/ciph-v0.6-child-tasks/children/docs-worker/TASK.md`, `runs/ciph-v0.6-child-tasks/children/docs-worker/RESPONSE.md`, `runs/ciph-v0.6-child-tasks/children/docs-worker/OWNERSHIP.json` | `runs/ciph-v0.6-child-tasks/artifacts/checks/child-help.txt` |

## Risks And Blockers

- None yet.

## Closeout Commands

```bash
python3 scripts/lint_manifest.py runs/ciph-v0.6-child-tasks/MANIFEST.json --root .
python3 scripts/run_checks.py runs/ciph-v0.6-child-tasks/MANIFEST.json --root .
python3 scripts/verify_manifest.py runs/ciph-v0.6-child-tasks/MANIFEST.json --root .
python3 scripts/closeout_check.py runs/ciph-v0.6-child-tasks/MANIFEST.json --root .
python3 scripts/run_status.py runs/ciph-v0.6-child-tasks/MANIFEST.json --root . --output runs/ciph-v0.6-child-tasks/artifacts/status.md
python3 scripts/closeout_check.py runs/ciph-v0.6-child-tasks/MANIFEST.json --root . --output runs/ciph-v0.6-child-tasks/artifacts/closeout.md
```
