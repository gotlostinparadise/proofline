# Proofline

Proofline is the public-facing workflow for durable, inspectable agent-assisted coding work in this repository. The internal runtime is still the CIPH (Complex Implementation Project Harness).

## Quick Start: Core Proofline Path

Use this for real work:

```bash
python3 scripts/init_run.py proofline-core-task --objective "Describe the coding task."
```

Fill the generated run artifacts:

```text
runs/proofline-core-task/
  TASK.html
  MANIFEST.json
  TRACE.jsonl
  artifacts/
```

1. Create a concrete requirement map in `TASK.html` and `MANIFEST.json`.
2. Add required checks and evidence paths in the manifest.
3. Execute required checks and write evidence:

   ```bash
   python3 scripts/run_checks.py runs/proofline-core-task/MANIFEST.json --root .
   ```

4. Validate the manifest contract:

   ```bash
   python3 scripts/lint_manifest.py runs/proofline-core-task/MANIFEST.json --root .
   python3 scripts/verify_manifest.py runs/proofline-core-task/MANIFEST.json --root .
   ```

5. Render closeout artifacts:

   ```bash
   python3 scripts/run_status.py runs/proofline-core-task/MANIFEST.json --root . --output runs/proofline-core-task/artifacts/status.html
   python3 scripts/closeout_check.py runs/proofline-core-task/MANIFEST.json --root . --output runs/proofline-core-task/artifacts/closeout.html
   ```

6. Run the repository gate when ready to finish:

   ```bash
   python3 scripts/check_repo.py
   ```

Use this gate as the default health signal for all Proofline work.

Current boundary (as of 2026-05-21):

- `proofline-real-task-campaign` ran 5 real historical tasks and caught 0 high-severity misses against a practical threshold of 2/5.
- Default stance remains minimal Proofline core only.
- Candidate/evaluation/replay commands are explicitly research-layer and non-default.

## When Not to Use Proofline

- Single-file typo fixes.
- One-off throwaway edits that do not change public-facing behavior.
- Temporary experiments where no durable trace, manifest, or closeout evidence is needed.

For heavier, repeatable, or long-running research effort, use the research layer below only when explicitly needed.

## Research Layer (Optional)

The following are optional research-grade tools and commands and should be used only when you are intentionally running optimization loops:

```bash
python3 scripts/init_candidate.py runs/<run-id>/MANIFEST.json <candidate-id> --changed-module <module>
python3 scripts/init_candidate.py runs/<run-id>/MANIFEST.json <candidate-id> --change-class source --changed-module <module> --source-path runs/<run-id>/candidates/<candidate-id>/source/README.md
python3 scripts/validate_candidate.py runs/<run-id>/candidates/<candidate-id> --root . --output runs/<run-id>/artifacts/candidate-validation.html
python3 scripts/candidate_summary.py runs/<run-id> --output runs/<run-id>/artifacts/candidate-summary.html
python3 scripts/validate_evaluation.py runs/<run-id> --root . --output runs/<run-id>/artifacts/evaluation-report.html
python3 scripts/release_holdout.py runs/<run-id> --root . --released-at 2026-05-20T04:00:00Z --output runs/<run-id>/artifacts/holdout-release.html
python3 scripts/ingest_holdout_scores.py runs/<run-id> runs/<run-id>/artifacts/frontier-holdout-input.json --root . --output runs/<run-id>/artifacts/holdout-ingest.html
python3 scripts/final_comparison.py runs/<run-id> --root . --output runs/<run-id>/artifacts/final-comparison.html
python3 scripts/validate_score_provenance.py runs/<run-id> --root . --output runs/<run-id>/artifacts/score-provenance.html
python3 scripts/validate_score_integrity.py runs/<run-id> --root . --output runs/<run-id>/artifacts/score-integrity.html
python3 scripts/validate_evaluator_replay.py runs/<run-id> --root . --output runs/<run-id>/artifacts/evaluator-replay.html
python3 scripts/execute_evaluator_replay.py runs/<run-id> --root . --receipt-dir runs/<run-id>/replay_receipts --output runs/<run-id>/artifacts/evaluator-replay-dry-run.html
python3 scripts/execute_evaluator_replay.py runs/<run-id> --root . --execute --allow-argv0 python3 --timeout-seconds 30 --receipt-dir runs/<run-id>/replay_receipts --output runs/<run-id>/artifacts/evaluator-replay-execution.html
python3 scripts/trace_metrics.py runs/<run-id>/MANIFEST.json --root . --output runs/<run-id>/artifacts/mechanism-metrics.html
```

Research history tooling should be treated as optional:

```bash
python3 scripts/query_experience_store.py --root . --runs-dir runs --status PASS --format json --output runs/<run-id>/artifacts/experience-store.json
python3 scripts/diagnose_experience_store.py --root . --runs-dir runs --min-severity medium --format json --output runs/<run-id>/artifacts/experience-diagnostics.json
python3 scripts/diagnose_experience_store.py --root . --runs-dir runs --min-severity high --format html --output runs/<run-id>/artifacts/experience-diagnostics.html
python3 scripts/diagnose_experience_store.py --root . --runs-dir runs --min-severity high --include-legacy-runs
python3 scripts/plan_next_candidates.py runs/<run-id>/artifacts/experience-diagnostics.json --format html --output runs/<run-id>/artifacts/next-candidates.html
```

> `diagnose_experience_store` defaults to skipping legacy historical runs with no trace; use `--include-legacy-runs` only for historical clean-up.

## Files

- `harness/CIPH.md`: high-level Proofline lifecycle and contracts.
- `harness/runtime-charter.md`: runtime rules for facts, evidence, delegation, and closeout.
- `harness/policies/`: policy modules for state, context, verification, recovery, delegation, candidate-search, and stopping.
- `templates/TASK.html`: HTML-first task template.
- `templates/TASK.md`: legacy markdown task template.
- `templates/MANIFEST.json`: manifest template.
- `scripts/init_run.py`: creates a run.
- `scripts/run_checks.py`: executes manifest checks and writes evidence.
- `scripts/lint_manifest.py`: manifest linting.
- `scripts/verify_manifest.py`: manifest validation against local evidence.
- `scripts/run_status.py`: writes a concise status artifact.
- `scripts/closeout_check.py`: writes the closeout artifact.
- `scripts/check_repo.py`: default repository health gate.
- `skills/proofline/SKILL.md`: Proofline user-facing skill guidance.

## Trace, Replay, and Experience Commands

```bash
python3 scripts/lint_trace.py runs/<run-id>/TRACE.jsonl --root .
python3 scripts/query_experience_store.py --root . --runs-dir runs --status PASS --format json
python3 scripts/query_experience_store.py --root . --runs-dir runs --has-replay-receipts --format html
```

The repository gate is the default gate. Treat `diagnose_experience_store --include-legacy-runs` as a research command unless explicitly part of a history-cleanup pass.

## Development Checks

Default repo gate:

```bash
python3 scripts/check_repo.py
```

Extended validation commands:

```bash
python3 -m unittest discover
python3 scripts/lint_manifest.py runs/example-harness-design/MANIFEST.json --root .
python3 scripts/verify_manifest.py runs/example-harness-design/MANIFEST.json --root .
python3 scripts/run_status.py runs/example-harness-design/MANIFEST.json --root .
python3 scripts/closeout_check.py runs/example-harness-design/MANIFEST.json --root .
```
