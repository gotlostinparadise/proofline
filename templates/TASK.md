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

## Policy Modules

List any active harness policy modules from `harness/policies/`. Policy modules describe strategy; deterministic scripts still own exact validation and scoring.

## Trace Ledger

Research runs use `runs/<run-id>/TRACE.jsonl` for raw events. Validate it with `scripts/lint_trace.py` before closeout.

## Mechanism Metrics

Research runs can derive mechanism metrics with `scripts/trace_metrics.py`. Use them to inspect harness behavior; keep manifest validation and closeout evidence as the source of completion truth.

## Deliverables

| ID | Requirement | Artifact paths | Evidence paths |
| --- | --- | --- | --- |
| example | Replace this row. | `path/to/artifact` | `path/to/evidence.md` |

## Risks And Blockers

- None yet.

## Closeout Commands

```bash
python3 scripts/lint_manifest.py runs/<run-id>/MANIFEST.json --root .
python3 scripts/lint_trace.py runs/<run-id>/TRACE.jsonl --root .
python3 scripts/run_checks.py runs/<run-id>/MANIFEST.json --root .
python3 scripts/verify_manifest.py runs/<run-id>/MANIFEST.json --root .
python3 scripts/trace_metrics.py runs/<run-id>/MANIFEST.json --root . --output runs/<run-id>/artifacts/mechanism-metrics.html
python3 scripts/run_status.py runs/<run-id>/MANIFEST.json --root . --output runs/<run-id>/artifacts/status.html
python3 scripts/closeout_check.py runs/<run-id>/MANIFEST.json --root . --output runs/<run-id>/artifacts/closeout.html
```
