# Complex Implementation Project Harness (CIPH)

`Proofline` is the public-facing workflow for this repository. Internally, this harness implementation is `CIPH`.

## Core Proofline Workflow

1. Create a new run:

```bash
python3 scripts/init_run.py <run-id> --objective "Describe the coding task."
```

2. Map every explicit requirement from the prompt into `TASK.html` and `MANIFEST.json`:

- concrete deliverables
- concrete evidence paths
- required checks and commands

3. Execute required checks and write structured evidence:

```bash
python3 scripts/run_checks.py runs/<run-id>/MANIFEST.json --root .
```

4. Verify manifest contract:

```bash
python3 scripts/lint_manifest.py runs/<run-id>/MANIFEST.json --root .
python3 scripts/verify_manifest.py runs/<run-id>/MANIFEST.json --root .
```

5. Render and record closeout evidence:

```bash
python3 scripts/run_status.py runs/<run-id>/MANIFEST.json --root . --output runs/<run-id>/artifacts/status.html
python3 scripts/closeout_check.py runs/<run-id>/MANIFEST.json --root . --output runs/<run-id>/artifacts/closeout.html
```

6. Run repository gate when complete:

```bash
python3 scripts/check_repo.py
```

Only checks marked `"required": true` are hard-gating closeout obligations by default.

Current campaign posture (2026-05-21):

- `proofline-real-task-campaign-v3` produced **0/5** high-severity catches against a 2/5 practical threshold.
- Keep candidate/evaluation/replay workflows as optional research-only tooling until the threshold is met.

## When Not to Use Proofline

- one-line typo fixes
- trivial/local edits that do not change persistent behavior
- throwaway experimentation where durable evidence is not needed

## Research Layer (Optional)

Use the following only when running candidate and optimization workflows:

```bash
python3 scripts/init_candidate.py runs/<run-id>/MANIFEST.json <candidate-id> --changed-module <module>
python3 scripts/init_candidate.py runs/<run-id>/MANIFEST.json <candidate-id> --change-class source --changed-module <module> --source-path runs/<run-id>/candidates/<candidate-id>/source/README.md
python3 scripts/validate_candidate.py runs/<run-id>/candidates/<candidate-id> --root . --output runs/<run-id>/artifacts/candidate-validation.html
python3 scripts/candidate_summary.py runs/<run-id> --output runs/<run-id>/artifacts/candidate-summary.html
python3 scripts/validate_evaluation.py runs/<run-id> --root . --output runs/<run-id>/artifacts/evaluation-report.html
python3 scripts/release_holdout.py runs/<run-id> --root . --released-at 2026-05-20T04:00:00Z --output runs/<run-id>/artifacts/holdout-release.html
python3 scripts/ingest_holdout_scores.py runs/<run-id> runs/<run-id>/artifacts/frontier-holdout-input.json --root . --output runs/<run-id>/artifacts/holdout-ingest.html
python3 scripts/final_comparison.py runs/<run-id> --root . --output runs/<run-id>/artifacts/final-comparison.html
```

```bash
python3 scripts/trace_metrics.py runs/<run-id>/MANIFEST.json --root . --output runs/<run-id>/artifacts/mechanism-metrics.html
python3 scripts/validate_score_provenance.py runs/<run-id> --root . --output runs/<run-id>/artifacts/score-provenance.html
python3 scripts/validate_score_integrity.py runs/<run-id> --root . --output runs/<run-id>/artifacts/score-integrity.html
python3 scripts/validate_evaluator_replay.py runs/<run-id> --root . --output runs/<run-id>/artifacts/evaluator-replay.html
python3 scripts/execute_evaluator_replay.py runs/<run-id> --root . --receipt-dir runs/<run-id>/replay_receipts --output runs/<run-id>/artifacts/evaluator-replay-dry-run.html
python3 scripts/execute_evaluator_replay.py runs/<run-id> --root . --execute --allow-argv0 python3 --timeout-seconds 30 --receipt-dir runs/<run-id>/replay_receipts --output runs/<run-id>/artifacts/evaluator-replay-execution.html
```

```bash
python3 scripts/query_experience_store.py --root . --runs-dir runs --status PASS --format json --output runs/<run-id>/artifacts/experience-store.json
python3 scripts/diagnose_experience_store.py --root . --runs-dir runs --min-severity medium --format json --output runs/<run-id>/artifacts/experience-diagnostics.json
python3 scripts/diagnose_experience_store.py --root . --runs-dir runs --min-severity high --include-legacy-runs
python3 scripts/diagnose_experience_store.py --root . --runs-dir runs --min-severity high --format html --output runs/<run-id>/artifacts/experience-diagnostics.html
python3 scripts/plan_next_candidates.py runs/<run-id>/artifacts/experience-diagnostics.json --format html --output runs/<run-id>/artifacts/next-candidates.html
```

`--include-legacy-runs` should be used explicitly for history review and repair work; it is not part of the default core path.

`diagnose_experience_store --fail-on-high` is reserved for explicit cleanup/research runs.

## Command Reference

```bash
python3 scripts/lint_trace.py runs/<run-id>/TRACE.jsonl --root .
python3 scripts/query_experience_store.py --root . --runs-dir runs --format html --output runs/<run-id>/artifacts/experience-store.html
```

```bash
python3 scripts/closeout_check.py runs/<run-id>/MANIFEST.json --root .
```

## Minimal Run Layout

```text
runs/<run-id>/
  TASK.html
  MANIFEST.json
  TRACE.jsonl
  artifacts/
    checks/
      <check-name>.txt
```
