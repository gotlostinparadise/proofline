---
name: proofline
description: Use when starting, managing, reviewing, delegating, or closing out multi-step coding work that needs durable scope, artifacts, verification evidence, run manifests, and closeout across context handoffs.
---

# Proofline

## Overview

Proofline is the repo-native workflow for evidence-backed agent work. Use it to keep the task objective, deliverables, checks, evidence, and closeout artifacts in-repo and verify that completion is real.

For core work, use `TASK` + `MANIFEST` + checks, then closeout evidence. Do not default to optimizer tooling until explicit research tasks require it.

Current proofline boundary (2026-05-21):

- `proofline-real-task-campaign-v3` completed 5 recent real tasks with `0/5` high-severity catches against a practical threshold of `2/5`.
- Keep candidate/evaluation/replay as research-only tooling unless a milestone explicitly requires optimization.

## Decision

Use Proofline for:

- multi-step maintenance work
- delegated tasks with clear handoffs
- scope-boundary changes
- review-required changes

Use lightweight local edits for:

- one-line fixes
- exploratory throwaway experiments

## Start A Run

```bash
python3 vendor/proofline/scripts/init_run.py <run-id> --root . --proofline-root vendor/proofline --objective "<objective>"
```

## Core Quick Path

1. Fill `vendor/proofline/runs/<run-id>/TASK.html` and `MANIFEST.json`.
2. Run required checks:

```bash
python3 vendor/proofline/scripts/run_checks.py vendor/proofline/runs/<run-id>/MANIFEST.json --root .
```

3. Validate manifest contracts:

```bash
python3 vendor/proofline/scripts/lint_manifest.py vendor/proofline/runs/<run-id>/MANIFEST.json --root .
python3 vendor/proofline/scripts/verify_manifest.py vendor/proofline/runs/<run-id>/MANIFEST.json --root .
```

4. Render closeout evidence:

```bash
python3 vendor/proofline/scripts/run_status.py vendor/proofline/runs/<run-id>/MANIFEST.json --root . --output vendor/proofline/runs/<run-id>/artifacts/status.html
python3 vendor/proofline/scripts/closeout_check.py vendor/proofline/runs/<run-id>/MANIFEST.json --root . --output vendor/proofline/runs/<run-id>/artifacts/closeout.html
python3 vendor/proofline/scripts/lint_trace.py vendor/proofline/runs/<run-id>/TRACE.jsonl --root .
python3 vendor/proofline/scripts/trace_metrics.py vendor/proofline/runs/<run-id>/MANIFEST.json --root .
```

5. Run repo gate:

```bash
python3 vendor/proofline/scripts/check_repo.py --root . --runs-dir vendor/proofline/runs
```

Only checks marked `"required": true` are hard closeout gates by default. Optional checks are for research/history analysis and should not block a core path finish.

## Research Layer (Optional)

Candidate, evaluation, and replay commands are optional and should be used only for explicit research/optimization tasks:

```bash
python3 vendor/proofline/scripts/init_candidate.py vendor/proofline/runs/<run-id>/MANIFEST.json <candidate-id> --changed-module <module>
python3 vendor/proofline/scripts/init_candidate.py vendor/proofline/runs/<run-id>/MANIFEST.json <candidate-id> --change-class source --changed-module <module> --source-path vendor/proofline/runs/<run-id>/candidates/<candidate-id>/source/README.md
python3 vendor/proofline/scripts/release_holdout.py vendor/proofline/runs/<run-id> --root . --released-at 2026-05-20T04:00:00Z --output vendor/proofline/runs/<run-id>/artifacts/holdout-release.html
python3 vendor/proofline/scripts/ingest_holdout_scores.py vendor/proofline/runs/<run-id> vendor/proofline/runs/<run-id>/artifacts/frontier-holdout-input.json --root . --output vendor/proofline/runs/<run-id>/artifacts/holdout-ingest.html
python3 vendor/proofline/scripts/final_comparison.py vendor/proofline/runs/<run-id> --root . --output vendor/proofline/runs/<run-id>/artifacts/final-comparison.html
python3 vendor/proofline/scripts/validate_candidate.py vendor/proofline/runs/<run-id>/candidates/<candidate-id> --root . --output vendor/proofline/runs/<run-id>/artifacts/candidate-validation.html
python3 vendor/proofline/scripts/candidate_summary.py vendor/proofline/runs/<run-id> --output vendor/proofline/runs/<run-id>/artifacts/candidate-summary.html
python3 vendor/proofline/scripts/validate_evaluation.py vendor/proofline/runs/<run-id> --root . --output vendor/proofline/runs/<run-id>/artifacts/evaluation-report.html
python3 vendor/proofline/scripts/query_experience_store.py --root . --runs-dir vendor/proofline/runs --status PASS --format json --output vendor/proofline/runs/<run-id>/artifacts/experience-store.json
python3 vendor/proofline/scripts/query_experience_store.py --root . --runs-dir vendor/proofline/runs --has-replay-receipts --format html --output vendor/proofline/runs/<run-id>/artifacts/experience-store.html
python3 vendor/proofline/scripts/diagnose_experience_store.py --root . --runs-dir vendor/proofline/runs --min-severity medium --format json --output vendor/proofline/runs/<run-id>/artifacts/experience-diagnostics.json
python3 vendor/proofline/scripts/diagnose_experience_store.py --root . --runs-dir vendor/proofline/runs --min-severity high --include-legacy-runs
python3 vendor/proofline/scripts/plan_next_candidates.py vendor/proofline/runs/<run-id>/artifacts/experience-diagnostics.json --format html --output vendor/proofline/runs/<run-id>/artifacts/next-candidates.html
```

```bash
python3 vendor/proofline/scripts/validate_score_provenance.py vendor/proofline/runs/<run-id> --root . --output vendor/proofline/runs/<run-id>/artifacts/score-provenance.html
python3 vendor/proofline/scripts/validate_score_integrity.py vendor/proofline/runs/<run-id> --root . --output vendor/proofline/runs/<run-id>/artifacts/score-integrity.html
python3 vendor/proofline/scripts/validate_evaluator_replay.py vendor/proofline/runs/<run-id> --root . --output vendor/proofline/runs/<run-id>/artifacts/evaluator-replay.html
python3 vendor/proofline/scripts/execute_evaluator_replay.py vendor/proofline/runs/<run-id> --root . --receipt-dir vendor/proofline/runs/<run-id>/replay_receipts --output vendor/proofline/runs/<run-id>/artifacts/evaluator-replay-dry-run.html
python3 vendor/proofline/scripts/execute_evaluator_replay.py vendor/proofline/runs/<run-id> --root . --execute --allow-argv0 python3 --timeout-seconds 30 --receipt-dir vendor/proofline/runs/<run-id>/replay_receipts --output vendor/proofline/runs/<run-id>/artifacts/evaluator-replay-execution.html
python3 vendor/proofline/scripts/trace_strictness_report.py vendor/proofline/runs/<run-id>/MANIFEST.json --root . --output vendor/proofline/runs/<run-id>/artifacts/trace-strictness-report.json
python3 vendor/proofline/scripts/repair_trace_strictness.py vendor/proofline/runs/<run-id>/artifacts/trace-strictness-report.json --format json --output vendor/proofline/runs/<run-id>/artifacts/trace-repair-plan.json --strict
python3 vendor/proofline/scripts/query_experience_store.py --root . --runs-dir vendor/proofline/runs --min-severity high --fail-on-high --include-legacy-runs --format json --output vendor/proofline/runs/<run-id>/artifacts/source_provenance.json
```

## When Not to Use Proofline

- one-line typo fixes
- trivial local-only changes with no durable evidence
- throwaway work where no downstream handoff depends on an audit trail

## Verify and Close

```bash
python3 vendor/proofline/scripts/run_checks.py vendor/proofline/runs/<run-id>/MANIFEST.json --root .
python3 vendor/proofline/scripts/verify_manifest.py vendor/proofline/runs/<run-id>/MANIFEST.json --root .
python3 vendor/proofline/scripts/closeout_check.py vendor/proofline/runs/<run-id>/MANIFEST.json --root . --output vendor/proofline/runs/<run-id>/artifacts/closeout.html
```

## Common Mistakes

| Mistake | Fix |
| --- | --- |
| Starting Proofline for trivial edits | Use a lightweight edit path unless durability is required. |
| Using optimization tooling by default | Reserve candidate/evaluation/replay for explicit research tasks. |
| Treating diagnostics as mandatory for normal core runs | `diagnose_experience_store` is optional and research-oriented by default unless history repair is active. |
| Running diagnostics without explicit legacy intent | Use `--include-legacy-runs` only when intentionally reviewing historical runs. |
| Failing high-severity diagnostics as default gate control | Use `--fail-on-high` only in explicit cleanup or research runs. |
