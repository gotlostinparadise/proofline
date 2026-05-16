# CIPH Task

## Objective

Add candidate trace and scoring scaffolding for CIPH optimization.

## Acceptance Object

The work is acceptable when candidate records include score files, trace files, notes, and patch placeholders; candidate summaries compute Pareto status; docs explain the workflow; and this run includes scored dogfood candidates plus a generated summary.

## Constraints

- Repository rules: create scaffolding only; do not run benchmark optimization automatically.
- Files or areas in scope: candidate scripts, tests, README, harness docs, and this run.
- Files or areas out of scope: model optimization, benchmark execution, and automatic score mutation.
- Permissions: local file writes only.
- Secrets handling: no secrets are required.

## Volatile Facts To Verify

No external API, pricing, product-limit, or schema fact is required. The feature depends on local repository files and Python standard-library behavior.

## Deliverables

| ID | Requirement | Artifact paths | Evidence paths |
| --- | --- | --- | --- |
| candidate-command | Add `scripts/init_candidate.py` to create candidate records. | `scripts/init_candidate.py` | `runs/ciph-v0.7-candidates/artifacts/checks/focused-candidate-tests.txt` |
| candidate-summary | Add `scripts/candidate_summary.py` to summarize scores and Pareto status. | `scripts/candidate_summary.py` | `runs/ciph-v0.7-candidates/artifacts/checks/focused-summary-tests.txt` |
| candidate-tests | Add tests for candidate creation and score summary behavior. | `tests/test_init_candidate.py`, `tests/test_candidate_summary.py` | `runs/ciph-v0.7-candidates/artifacts/checks/full-unit-tests.txt` |
| docs-flow | Document candidate creation and summary commands. | `README.md`, `harness/CIPH.md` | `runs/ciph-v0.7-candidates/artifacts/checks/full-unit-tests.txt` |
| dogfood-candidates | Create scored dogfood candidates and a summary report. | `runs/ciph-v0.7-candidates/candidates/baseline/score.json`, `runs/ciph-v0.7-candidates/candidates/weaker/score.json`, `runs/ciph-v0.7-candidates/artifacts/candidate-summary.md` | `runs/ciph-v0.7-candidates/artifacts/checks/summary-help.txt` |

## Risks And Blockers

- None yet.

## Closeout Commands

```bash
python3 scripts/lint_manifest.py runs/ciph-v0.7-candidates/MANIFEST.json --root .
python3 scripts/run_checks.py runs/ciph-v0.7-candidates/MANIFEST.json --root .
python3 scripts/verify_manifest.py runs/ciph-v0.7-candidates/MANIFEST.json --root .
python3 scripts/closeout_check.py runs/ciph-v0.7-candidates/MANIFEST.json --root .
python3 scripts/candidate_summary.py runs/ciph-v0.7-candidates --output runs/ciph-v0.7-candidates/artifacts/candidate-summary.md
python3 scripts/run_status.py runs/ciph-v0.7-candidates/MANIFEST.json --root . --output runs/ciph-v0.7-candidates/artifacts/status.md
python3 scripts/closeout_check.py runs/ciph-v0.7-candidates/MANIFEST.json --root . --output runs/ciph-v0.7-candidates/artifacts/closeout.md
```
