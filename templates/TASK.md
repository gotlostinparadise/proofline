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

## Core Proofline Workflow

Use this path for real scoped work.

1. Add explicit requirements to this task and `MANIFEST.json` deliverables.
2. Add required checks and evidence paths in `MANIFEST.json`.
3. Execute checks and write evidence with:

   ```bash
   python3 scripts/run_checks.py runs/<run-id>/MANIFEST.json --root .
   ```

4. Validate manifest contracts:

   ```bash
   python3 scripts/lint_manifest.py runs/<run-id>/MANIFEST.json --root .
   python3 scripts/verify_manifest.py runs/<run-id>/MANIFEST.json --root .
   ```

5. Render closeout artifacts:

   ```bash
   python3 scripts/run_status.py runs/<run-id>/MANIFEST.json --root . --output runs/<run-id>/artifacts/status.html
   python3 scripts/closeout_check.py runs/<run-id>/MANIFEST.json --root . --output runs/<run-id>/artifacts/closeout.html
   ```

6. Run repository gate when the work is complete:

   ```bash
   python3 scripts/check_repo.py
   ```

## Policy Modules

List any active harness policy modules from `harness/policies/`. Policy modules describe strategy; deterministic scripts still own exact validation and scoring.

## Trace Ledger

Proofline core runs use `runs/<run-id>/TRACE.jsonl` for raw events. Validate it with `scripts/lint_trace.py` before closeout.

## Mechanism Metrics

Research runs can derive mechanism metrics with `scripts/trace_metrics.py`. Use them to inspect harness behavior; keep manifest validation and closeout evidence as the source of completion truth.

## Deliverables

| ID | Requirement | Artifact paths | Evidence paths |
| --- | --- | --- | --- |
| example | Replace this row. | `path/to/artifact` | `path/to/evidence.md` |

## When Not to Use Proofline

- One-line typo fixes.
- Trivial local-only edits with no durable handoff.
- Throwaway experimentation with no evidence dependency.

## Research Layer (Optional)

Use candidate/evaluation/replay tooling only for explicit research passes:

```bash
python3 scripts/init_candidate.py runs/<run-id>/MANIFEST.json <candidate-id> --changed-module <module>
python3 scripts/init_candidate.py runs/<run-id>/MANIFEST.json <candidate-id> --change-class source --changed-module <module> --source-path runs/<run-id>/candidates/<candidate-id>/source/README.md
python3 scripts/validate_candidate.py runs/<run-id>/candidates/<candidate-id> --root . --output runs/<run-id>/artifacts/candidate-validation.html
python3 scripts/candidate_summary.py runs/<run-id> --output runs/<run-id>/artifacts/candidate-summary.html
python3 scripts/validate_evaluation.py runs/<run-id> --root . --output runs/<run-id>/artifacts/evaluation-report.html
python3 scripts/final_comparison.py runs/<run-id> --root . --output runs/<run-id>/artifacts/final-comparison.html
python3 scripts/validate_score_provenance.py runs/<run-id> --root . --output runs/<run-id>/artifacts/score-provenance.html
python3 scripts/validate_score_integrity.py runs/<run-id> --root . --output runs/<run-id>/artifacts/score-integrity.html
python3 scripts/validate_evaluator_replay.py runs/<run-id> --root . --output runs/<run-id>/artifacts/evaluator-replay.html
python3 scripts/execute_evaluator_replay.py runs/<run-id> --root . --receipt-dir runs/<run-id>/replay_receipts --output runs/<run-id>/artifacts/evaluator-replay-execution.html
```

```bash
python3 scripts/diagnose_experience_store.py --root . --runs-dir runs --min-severity medium --format json --output runs/<run-id>/artifacts/experience-diagnostics.json
python3 scripts/diagnose_experience_store.py --root . --runs-dir runs --min-severity high --format html --output runs/<run-id>/artifacts/experience-diagnostics.html
python3 scripts/diagnose_experience_store.py --root . --runs-dir runs --min-severity high --include-legacy-runs
```

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
python3 scripts/check_repo.py
```
