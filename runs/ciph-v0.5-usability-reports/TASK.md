# CIPH Task

## Objective

Add closeout report file output and concise run status reporting for CIPH usability.

## Acceptance Object

The work is acceptable when closeout checklists can be written to files, `scripts/run_status.py` renders and writes concise run status reports, docs/templates show the report flow, and this run produces `status.md` and `closeout.md` artifacts.

## Constraints

- Repository rules: keep reports Markdown, file-backed, and stdlib-only.
- Files or areas in scope: closeout script, status script, tests, README, harness docs, templates, and this run.
- Files or areas out of scope: HTML reports, databases, and automatic check execution from status rendering.
- Permissions: local file writes only.
- Secrets handling: status and closeout reports must not introduce secret collection.

## Volatile Facts To Verify

No external API, pricing, product-limit, or schema fact is required. The feature depends on local repository files and Python standard-library behavior.

## Deliverables

| ID | Requirement | Artifact paths | Evidence paths |
| --- | --- | --- | --- |
| closeout-output | Add `--output` support to `scripts/closeout_check.py`. | `scripts/closeout_check.py` | `runs/ciph-v0.5-usability-reports/artifacts/checks/focused-closeout-tests.txt` |
| run-status | Add `scripts/run_status.py` for concise run status reports. | `scripts/run_status.py` | `runs/ciph-v0.5-usability-reports/artifacts/checks/focused-status-tests.txt` |
| report-tests | Add tests for report rendering and file output. | `tests/test_run_status.py`, `tests/test_closeout_check.py` | `runs/ciph-v0.5-usability-reports/artifacts/checks/full-unit-tests.txt` |
| docs-flow | Document reusable status and closeout reports. | `README.md`, `harness/CIPH.md`, `templates/TASK.md` | `runs/ciph-v0.5-usability-reports/artifacts/checks/full-unit-tests.txt` |
| dogfood-reports | Generate status and closeout report artifacts for this run. | `runs/ciph-v0.5-usability-reports/artifacts/status.md`, `runs/ciph-v0.5-usability-reports/artifacts/closeout.md` | `runs/ciph-v0.5-usability-reports/artifacts/checks/status-help.txt` |

## Risks And Blockers

- None yet.

## Closeout Commands

```bash
python3 scripts/lint_manifest.py runs/ciph-v0.5-usability-reports/MANIFEST.json --root .
python3 scripts/run_checks.py runs/ciph-v0.5-usability-reports/MANIFEST.json --root .
python3 scripts/verify_manifest.py runs/ciph-v0.5-usability-reports/MANIFEST.json --root .
python3 scripts/closeout_check.py runs/ciph-v0.5-usability-reports/MANIFEST.json --root .
python3 scripts/run_status.py runs/ciph-v0.5-usability-reports/MANIFEST.json --root . --output runs/ciph-v0.5-usability-reports/artifacts/status.md
python3 scripts/closeout_check.py runs/ciph-v0.5-usability-reports/MANIFEST.json --root . --output runs/ciph-v0.5-usability-reports/artifacts/closeout.md
```
