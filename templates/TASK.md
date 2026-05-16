# CIPH Task

## Objective

State the original user request in concrete terms.

## Acceptance Object

Describe what proves the work is acceptable. Prefer exact files, commands, UI states, test results, or external evaluator behavior.

## Constraints

- Repository rules:
- Files or areas in scope:
- Files or areas out of scope:
- Permissions:
- Secrets handling:

## Volatile Facts To Verify

List API shapes, CLI flags, config keys, pricing, product limits, schemas, required fields, or other facts that need authoritative sources before implementation depends on them.

## Deliverables

| ID | Requirement | Artifact paths | Evidence paths |
| --- | --- | --- | --- |
| example | Replace this row. | `path/to/artifact` | `path/to/evidence.md` |

## Risks And Blockers

- None yet.

## Closeout Commands

```bash
python3 scripts/lint_manifest.py runs/<run-id>/MANIFEST.json --root .
python3 scripts/run_checks.py runs/<run-id>/MANIFEST.json --root .
python3 scripts/verify_manifest.py runs/<run-id>/MANIFEST.json --root .
python3 scripts/closeout_check.py runs/<run-id>/MANIFEST.json --root .
python3 scripts/run_status.py runs/<run-id>/MANIFEST.json --root . --output runs/<run-id>/artifacts/status.md
python3 scripts/closeout_check.py runs/<run-id>/MANIFEST.json --root . --output runs/<run-id>/artifacts/closeout.md
```
