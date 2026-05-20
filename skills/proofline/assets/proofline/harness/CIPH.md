# Complex Implementation Project Harness

CIPH is a file-backed harness for complex coding work. It keeps the project objective, implementation plan, required artifacts, verification evidence, and closeout checklist in the repository so future agents can inspect the actual work state instead of relying on chat memory.

## Lifecycle

1. Intake: capture the user objective, constraints, permissions, volatile facts, and required deliverables.
2. Scope: map every explicit requirement to planned artifacts, evidence, commands, or known blockers.
3. Design: choose the smallest architecture that can satisfy the objective and record non-goals.
4. Execute: implement within the agreed write boundaries and preserve material decisions.
5. Verify: run evaluator-aligned commands and record evidence paths in the manifest.
6. Close: compare the original objective to concrete artifacts and evidence before claiming completion.

## Contracts

### Task Contract

Each new run starts with `TASK.html`. It records the original objective, acceptance object, constraints, non-goals, volatile facts that require source verification, and intended deliverables. Older `TASK.md` runs remain valid historical records.

### Artifact Contract

Each required artifact is listed in `MANIFEST.json` with a path, description, and required flag. Required artifacts must exist before closeout.

### Evidence Contract

Every required check must have an evidence path. Evidence can be a local file or an external source reference. Local evidence paths are verified by `scripts/verify_manifest.py`.

### Fact Contract

Facts about APIs, configuration keys, CLI flags, pricing, schemas, product behavior, or other volatile details must be sourced from the most authoritative available documentation before code or setup instructions depend on them.

### Policy Module Contract

Research-grade runs declare active `policy_modules` in `MANIFEST.json`. Policy modules live under `harness/policies/` and describe editable strategy for state, context, verification, recovery, delegation, candidate search, and stopping. They are not exact validators; deterministic scripts own exact behavior.

### Trace Contract

Research-grade runs include `TRACE.jsonl` with schema version `ciph.trace.v1`. The trace ledger records raw events, while status and closeout reports are derived views. Validate trace ledgers with `scripts/lint_trace.py` before closeout. Use `--strict` when the trace is a closeout control: strict mode rejects duplicate event IDs, unsafe local references, and sequencing regressions such as completion before start. Runs opt into strict manifest enforcement with `trace.strict: true`; historical runs can remain non-strict until repaired. Use `scripts/trace_strictness_report.py` to list strict-ready runs and runs needing trace repair, then `scripts/repair_trace_strictness.py` to generate report-only repair suggestions.

### Mechanism Metrics Contract

Research-grade runs can derive mechanism metrics from `MANIFEST.json` and `TRACE.jsonl` with `scripts/trace_metrics.py`. Metrics expose harness behavior, including artifact coverage, stage coverage, ordered workflow, tool success, handoff recall, validation coverage, model result coverage, context token totals, wall-time span, cost proxy, and recovery completeness. Metrics are diagnostic reports, not substitutes for manifest validation or closeout evidence.

### Candidate Lab Contract

Candidate records live under `runs/<run-id>/candidates/<candidate-id>/`. Each record keeps `score.json`, `NOTES.md`, `patch.diff`, candidate-level `TRACE.jsonl`, policy/source notes, artifact storage, policy provenance snapshots, ablation class metadata, and legacy trace files. Validate candidate records with `scripts/validate_candidate.py` before relying on their scores or summaries.

### Evaluation Protocol Contract

Research-grade optimization runs can include `EVALUATION.json` at the run root. It records baseline candidate, search-set IDs, sealed holdout IDs, fixed budget, current phase, selected frontier candidates, release history, candidate score paths, and post-release holdout score paths. Validate it with `scripts/validate_evaluation.py` before holdout release or final comparison. Transition from `search` to `holdout_released` only through `scripts/release_holdout.py`; do not manually flip phase or unseal holdout state. After release, ingest externally produced holdout score files through `scripts/ingest_holdout_scores.py`; keep search scores and holdout scores as separate records.

### Score Provenance Contract

Research-grade score records can include `score_provenance` pointing to an evaluator manifest under `runs/<run-id>/evaluators/`. The manifest records evaluator ID, phase, command, inputs, outputs, evidence paths, and metric keys. Validate provenance with `scripts/validate_score_provenance.py` before relying on score values in summaries or final comparisons.

### Score Integrity Contract

Evaluator manifests can include an `integrity` object with schema `ciph.evaluator-integrity.v1`, algorithm `sha256`, and digest maps for `input_hashes`, `evidence_hashes`, and `output_hashes`. Each digest uses `sha256:<hex>`. Validate integrity with `scripts/validate_score_integrity.py` to detect drift in evaluator inputs, evidence, or score outputs after evaluation. Integrity is local tamper evidence, not a signature or trusted timestamp.

### Evaluator Replay Readiness Contract

Evaluator manifests can include a `replay` object with schema `ciph.evaluator-replay.v1`, mode `metadata-only`, a local `working_directory`, command metadata with `argv` and `shell: false`, an `env_allowlist` of variable names, `external_effect_policy: local-only`, and `expected_output_hashes`. Validate replay readiness with `scripts/validate_evaluator_replay.py`. The validator preflights metadata and hashes only; it does not execute evaluator commands or call providers.

### Evaluator Replay Execution Contract

Local replay execution is explicit and fail-closed. `scripts/execute_evaluator_replay.py` dry-runs by default. Actual execution requires `--execute`, at least one exact `--allow-argv0` approval, `shell: false`, `external_effect_policy: local-only`, a repository-local working directory, and a positive timeout. Executed commands run through Bubblewrap with `--unshare-net`; if the sandbox is unavailable, execution fails. Reports suppress command stdout/stderr content, record only byte counts, and verify declared output hashes after execution.

### Replay Receipt Contract

Replay dry-runs and executions write JSON receipts with schema `ciph.replay-receipt.v1` under `runs/<run-id>/replay_receipts/` by default, or under `--receipt-dir`. Receipts record evaluator ID, manifest path, mode, status, command digest, sandbox mode, timeout, env allowlist names, expected/pre/post output hashes, exit code, output byte counts, errors, report path, and timestamps. Receipts must not contain environment values or command stdout/stderr content.

### Queryable Experience Store

Prior runs are queried through a read-only projection, not a mutable database. `scripts/query_experience_store.py` scans run manifests, traces, closeout events, check paths, artifact paths, and replay receipts, then emits schema `ciph.experience-store.v1` as JSON or HTML. Use filters such as `--status PASS`, `--event-type validation.completed`, `--contains replay`, `--has-replay-receipts`, and `--limit 10` to inspect accumulated harness experience. The projection must not serialize raw evidence bodies, command stdout/stderr content, or environment values.

### Diagnostic Experience Review

Use `scripts/diagnose_experience_store.py` to periodically score accumulated runs for contract quality and recovery readiness. Diagnostics emit `ciph.experience-diagnostics.v1` and prioritize findings with severity, evidence paths, linked recommendations, and an `execution_control` block. `--fail-on-high` returns non-zero when high-severity findings exist so closeout can fail closed. `scripts/plan_next_candidates.py` consumes diagnostics JSON and emits candidate IDs, changed modules, changed classes, and rationale for the next bounded experiment; it does not execute candidates.

### Delegation Contract

Delegated work requires a bounded task packet, clear write ownership, expected output paths, and local verification after return. Child-agent self-report is not completion evidence.

### Stop Contract

A run is complete only when the closeout checklist maps every explicit requirement to existing artifacts and evidence, or when remaining gaps are recorded as concrete blockers.

## Commands

Create a run:

```bash
python3 scripts/init_run.py <run-id> --objective "Describe the coding task."
```

Lint the manifest:

```bash
python3 scripts/lint_manifest.py runs/<run-id>/MANIFEST.json --root .
```

Lint manifests before running checks so placeholders, missing evidence links, and weak required-check evidence paths fail early.

Lint a trace ledger:

```bash
python3 scripts/lint_trace.py runs/<run-id>/TRACE.jsonl --root .
python3 scripts/lint_trace.py runs/<run-id>/TRACE.jsonl --root . --strict
python3 scripts/trace_strictness_report.py --root . --runs-dir runs --format html --output runs/<run-id>/artifacts/trace-strictness.html
python3 scripts/repair_trace_strictness.py runs/<run-id>/artifacts/trace-strictness.json --format html --output runs/<run-id>/artifacts/trace-repair-plan.html
```

Render mechanism metrics:

```bash
python3 scripts/trace_metrics.py runs/<run-id>/MANIFEST.json --root . --output runs/<run-id>/artifacts/mechanism-metrics.html
```

Run executable checks:

```bash
python3 scripts/run_checks.py runs/<run-id>/MANIFEST.json --root .
```

Run checks before manifest validation when checks use `evidence_producer: "run_checks"`.

Validate a run manifest:

```bash
python3 scripts/verify_manifest.py runs/<run-id>/MANIFEST.json --root .
```

Render a closeout checklist:

```bash
python3 scripts/closeout_check.py runs/<run-id>/MANIFEST.json --root .
```

Write reusable reports:

```bash
python3 scripts/run_status.py runs/<run-id>/MANIFEST.json --root . --output runs/<run-id>/artifacts/status.html
python3 scripts/closeout_check.py runs/<run-id>/MANIFEST.json --root . --output runs/<run-id>/artifacts/closeout.html
```

Create a bounded child task packet:

```bash
python3 scripts/init_child_task.py runs/<run-id>/MANIFEST.json <child-id> --owner <role> --write-scope <path>
```

Create and summarize candidates:

```bash
python3 scripts/init_candidate.py runs/<run-id>/MANIFEST.json <candidate-id> --changed-module <module>
python3 scripts/validate_candidate.py runs/<run-id>/candidates/<candidate-id> --root . --output runs/<run-id>/artifacts/candidate-validation.html
python3 scripts/candidate_summary.py runs/<run-id> --output runs/<run-id>/artifacts/candidate-summary.html
```

Validate evaluation protocol:

```bash
python3 scripts/validate_evaluation.py runs/<run-id> --root . --output runs/<run-id>/artifacts/evaluation-report.html
```

Release holdout:

```bash
python3 scripts/release_holdout.py runs/<run-id> --root . --released-at 2026-05-20T04:00:00Z --output runs/<run-id>/artifacts/holdout-release.html
```

Ingest holdout scores and compare finalists:

```bash
python3 scripts/ingest_holdout_scores.py runs/<run-id> runs/<run-id>/artifacts/frontier-holdout-input.json --root . --output runs/<run-id>/artifacts/holdout-ingest.html
python3 scripts/validate_score_provenance.py runs/<run-id> --root . --output runs/<run-id>/artifacts/score-provenance.html
python3 scripts/validate_score_integrity.py runs/<run-id> --root . --output runs/<run-id>/artifacts/score-integrity.html
python3 scripts/validate_evaluator_replay.py runs/<run-id> --root . --output runs/<run-id>/artifacts/evaluator-replay.html
python3 scripts/execute_evaluator_replay.py runs/<run-id> --root . --receipt-dir runs/<run-id>/replay_receipts --output runs/<run-id>/artifacts/evaluator-replay-dry-run.html
python3 scripts/execute_evaluator_replay.py runs/<run-id> --root . --execute --allow-argv0 python3 --timeout-seconds 30 --receipt-dir runs/<run-id>/replay_receipts --output runs/<run-id>/artifacts/evaluator-replay-execution.html
python3 scripts/final_comparison.py runs/<run-id> --root . --output runs/<run-id>/artifacts/final-comparison.html
python3 scripts/query_experience_store.py --root . --runs-dir runs --status PASS --format json --output runs/<run-id>/artifacts/experience-store.json
python3 scripts/diagnose_experience_store.py --root . --runs-dir runs --min-severity medium --format json --output runs/<run-id>/artifacts/experience-diagnostics.json
python3 scripts/diagnose_experience_store.py --root . --runs-dir runs --min-severity high --format html --output runs/<run-id>/artifacts/experience-diagnostics.html
python3 scripts/diagnose_experience_store.py --root . --runs-dir runs --min-severity high --fail-on-high
python3 scripts/plan_next_candidates.py runs/<run-id>/artifacts/experience-diagnostics.json --format html --output runs/<run-id>/artifacts/next-candidates.html
```

Run the repository gate:

```bash
python3 scripts/check_repo.py
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

Use `templates/TASK.html` and `templates/MANIFEST.json` as starting points. `templates/TASK.md` remains as a legacy fallback for older installs.
