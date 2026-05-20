# Agent Harness

This repository contains CIPH, the Complex Implementation Project Harness. CIPH is a small file-backed harness for complex coding projects. It keeps the objective, deliverables, artifacts, checks, evidence, and closeout audit in the repository.

## Quick Start

Create a run:

```bash
python3 scripts/init_run.py my-run --objective "Describe the coding task here."
```

Edit the generated files:

```text
runs/my-run/
  TASK.html
  MANIFEST.json
  TRACE.jsonl
  artifacts/
```

Record each explicit requirement from the prompt in `MANIFEST.json`. Point each requirement at concrete artifact paths and evidence paths.
Research-grade runs also declare active `policy_modules` and trace metadata in `MANIFEST.json`.

Lint the manifest for weak contracts:

```bash
python3 scripts/lint_manifest.py runs/my-run/MANIFEST.json --root .
```

Run executable checks and write fresh evidence:

```bash
python3 scripts/run_checks.py runs/my-run/MANIFEST.json --root .
```

Validate the manifest:

```bash
python3 scripts/verify_manifest.py runs/my-run/MANIFEST.json --root .
```

Lint a research trace ledger:

```bash
python3 scripts/lint_trace.py runs/my-run/TRACE.jsonl --root .
```

Render mechanism metrics from the manifest and trace:

```bash
python3 scripts/trace_metrics.py runs/my-run/MANIFEST.json --root . --output runs/my-run/artifacts/mechanism-metrics.html
```

Render the closeout checklist:

```bash
python3 scripts/closeout_check.py runs/my-run/MANIFEST.json --root .
```

Write reusable reports:

```bash
python3 scripts/run_status.py runs/my-run/MANIFEST.json --root . --output runs/my-run/artifacts/status.html
python3 scripts/closeout_check.py runs/my-run/MANIFEST.json --root . --output runs/my-run/artifacts/closeout.html
```

Create a bounded child task packet:

```bash
python3 scripts/init_child_task.py runs/my-run/MANIFEST.json docs-worker --owner worker-docs --write-scope README.md
```

Create and summarize candidates:

```bash
python3 scripts/init_candidate.py runs/my-run/MANIFEST.json baseline --changed-module verification
python3 scripts/validate_candidate.py runs/my-run/candidates/baseline --root . --output runs/my-run/artifacts/candidate-validation.html
python3 scripts/candidate_summary.py runs/my-run --output runs/my-run/artifacts/candidate-summary.html
```

Validate an evaluation protocol:

```bash
python3 scripts/validate_evaluation.py runs/my-run --root . --output runs/my-run/artifacts/evaluation-report.html
```

Release holdout only after frontier selection and validation are clean:

```bash
python3 scripts/release_holdout.py runs/my-run --root . --released-at 2026-05-20T04:00:00Z --output runs/my-run/artifacts/holdout-release.html
```

Ingest holdout scores and render the final comparison:

```bash
python3 scripts/ingest_holdout_scores.py runs/my-run runs/my-run/artifacts/frontier-holdout-input.json --root . --output runs/my-run/artifacts/holdout-ingest.html
python3 scripts/validate_score_provenance.py runs/my-run --root . --output runs/my-run/artifacts/score-provenance.html
python3 scripts/validate_score_integrity.py runs/my-run --root . --output runs/my-run/artifacts/score-integrity.html
python3 scripts/validate_evaluator_replay.py runs/my-run --root . --output runs/my-run/artifacts/evaluator-replay.html
python3 scripts/execute_evaluator_replay.py runs/my-run --root . --receipt-dir runs/my-run/replay_receipts --output runs/my-run/artifacts/evaluator-replay-dry-run.html
python3 scripts/execute_evaluator_replay.py runs/my-run --root . --execute --allow-argv0 python3 --timeout-seconds 30 --receipt-dir runs/my-run/replay_receipts --output runs/my-run/artifacts/evaluator-replay-execution.html
python3 scripts/final_comparison.py runs/my-run --root . --output runs/my-run/artifacts/final-comparison.html
```

Query prior run experience:

```bash
python3 scripts/query_experience_store.py --root . --runs-dir runs --status PASS --format json --output runs/my-run/artifacts/experience-store.json
python3 scripts/query_experience_store.py --root . --runs-dir runs --has-replay-receipts --format html --output runs/my-run/artifacts/experience-store.html
```

## Files

- `harness/CIPH.md`: harness lifecycle and contracts.
- `harness/runtime-charter.md`: runtime rules for facts, evidence, delegation, and closeout.
- `harness/policies/`: natural-language policy modules for state, context, verification, recovery, delegation, candidate search, and stopping.
- `templates/TASK.html`: HTML-first task template used by the initializer.
- `templates/TASK.md`: legacy Markdown fallback task template.
- `templates/MANIFEST.json`: manifest template used by the initializer.
- `scripts/init_run.py`: creates a run directory from templates.
- `scripts/init_child_task.py`: creates a bounded child task packet.
- `scripts/init_candidate.py`: creates Meta-Harness candidate records.
- `scripts/validate_candidate.py`: validates candidate records and writes validation reports.
- `scripts/validate_evaluation.py`: validates search-set versus holdout evaluation protocols.
- `scripts/release_holdout.py`: gates the transition from search to holdout release.
- `scripts/ingest_holdout_scores.py`: links released holdout score records into the evaluation protocol.
- `scripts/validate_score_provenance.py`: validates score provenance and evaluator manifests.
- `scripts/validate_score_integrity.py`: validates evaluator manifest hashes for score inputs, evidence, and outputs.
- `scripts/validate_evaluator_replay.py`: validates evaluator replay readiness metadata without executing evaluator commands.
- `scripts/execute_evaluator_replay.py`: dry-runs or explicitly executes approved local replay commands with no-network isolation, output hash verification, and replay receipt JSON.
- `scripts/query_experience_store.py`: queries prior run manifests, traces, closeout status, checks, and replay receipts as JSON or HTML.
- `scripts/final_comparison.py`: writes final search-versus-holdout comparison reports.
- `scripts/candidate_summary.py`: writes a candidate score summary.
- `scripts/check_repo.py`: runs the repository health gate.
- `scripts/lint_manifest.py`: catches placeholders and weak manifest contracts.
- `scripts/lint_trace.py`: validates research trace JSONL event contracts.
- `scripts/trace_metrics.py`: derives mechanism metrics from run manifests and traces.
- `scripts/run_checks.py`: runs manifest checks and writes structured evidence.
- `scripts/html_report.py`: renders shared self-contained HTML report structure.
- `scripts/verify_manifest.py`: validates manifest structure and required local paths.
- `scripts/run_status.py`: writes a concise run status report.
- `scripts/closeout_check.py`: prints the prompt-to-artifact closeout checklist.

## Research Harness Layer

Policy modules under `harness/policies/` describe editable harness strategy. They are intentionally readable and ablatable; exact checks remain in scripts. `TRACE.jsonl` stores raw research events such as stage, state, tool, handoff, validation, candidate, recovery, budget, and closeout events. Candidate records under `runs/<run-id>/candidates/` preserve policy snapshots, source notes, raw candidate traces, score contracts, and artifacts. `EVALUATION.json` records baseline, search-set, holdout-set, budget, frontier, release budget, holdout score paths, and candidate phase state. Evaluator manifests under `runs/<run-id>/evaluators/` describe the command, inputs, outputs, evidence, metric keys, optional SHA-256 integrity hashes, and optional metadata-only replay readiness behind score records. Validate traces with `scripts/lint_trace.py`, candidates with `scripts/validate_candidate.py`, evaluation protocols with `scripts/validate_evaluation.py`, score provenance with `scripts/validate_score_provenance.py`, score integrity with `scripts/validate_score_integrity.py`, evaluator replay readiness with `scripts/validate_evaluator_replay.py`, and local replay execution with `scripts/execute_evaluator_replay.py`. The executor dry-runs by default; actual execution requires `--execute`, exact `--allow-argv0` approval, Bubblewrap no-network isolation, and post-run output hash verification. Replay receipts under `runs/<run-id>/replay_receipts/` record machine-readable status, command digest, sandbox mode, timeout, env allowlist names, pre/post output hashes, exit code, and output byte counts without storing env values or command output. `scripts/query_experience_store.py` projects prior runs into queryable JSON/HTML records without reading or serializing raw evidence bodies. Release holdout with `scripts/release_holdout.py`, ingest released scores with `scripts/ingest_holdout_scores.py`, then compare final outcomes with `scripts/final_comparison.py`; generated reports are views over manifest and trace evidence.

## Development Checks

Default repo gate:

```bash
python3 scripts/check_repo.py
```

Expanded commands:

```bash
python3 -m unittest discover
python3 scripts/lint_manifest.py runs/example-harness-design/MANIFEST.json --root .
python3 scripts/lint_manifest.py runs/ciph-v0.2-init-run/MANIFEST.json --root .
python3 scripts/lint_manifest.py runs/ciph-v0.3-run-checks/MANIFEST.json --root .
python3 scripts/lint_manifest.py runs/ciph-v0.4-manifest-lint/MANIFEST.json --root .
python3 scripts/lint_manifest.py runs/ciph-v0.5-usability-reports/MANIFEST.json --root .
python3 scripts/lint_manifest.py runs/ciph-v0.6-child-tasks/MANIFEST.json --root .
python3 scripts/lint_manifest.py runs/ciph-v0.7-candidates/MANIFEST.json --root .
python3 scripts/lint_manifest.py runs/ciph-v0.8-repo-gate/MANIFEST.json --root .
python3 scripts/run_checks.py runs/ciph-v0.3-run-checks/MANIFEST.json --root .
python3 scripts/run_checks.py runs/ciph-v0.4-manifest-lint/MANIFEST.json --root .
python3 scripts/run_checks.py runs/ciph-v0.5-usability-reports/MANIFEST.json --root .
python3 scripts/run_checks.py runs/ciph-v0.6-child-tasks/MANIFEST.json --root .
python3 scripts/run_checks.py runs/ciph-v0.7-candidates/MANIFEST.json --root .
python3 scripts/run_checks.py runs/ciph-v0.8-repo-gate/MANIFEST.json --root .
python3 scripts/verify_manifest.py runs/example-harness-design/MANIFEST.json --root .
python3 scripts/verify_manifest.py runs/ciph-v0.2-init-run/MANIFEST.json --root .
python3 scripts/verify_manifest.py runs/ciph-v0.3-run-checks/MANIFEST.json --root .
python3 scripts/verify_manifest.py runs/ciph-v0.4-manifest-lint/MANIFEST.json --root .
python3 scripts/verify_manifest.py runs/ciph-v0.5-usability-reports/MANIFEST.json --root .
python3 scripts/verify_manifest.py runs/ciph-v0.6-child-tasks/MANIFEST.json --root .
python3 scripts/verify_manifest.py runs/ciph-v0.7-candidates/MANIFEST.json --root .
python3 scripts/verify_manifest.py runs/ciph-v0.8-repo-gate/MANIFEST.json --root .
python3 scripts/run_status.py runs/ciph-v0.5-usability-reports/MANIFEST.json --root .
python3 scripts/run_status.py runs/ciph-v0.6-child-tasks/MANIFEST.json --root .
python3 scripts/run_status.py runs/ciph-v0.7-candidates/MANIFEST.json --root .
python3 scripts/run_status.py runs/ciph-v0.8-repo-gate/MANIFEST.json --root .
python3 scripts/closeout_check.py runs/example-harness-design/MANIFEST.json --root .
python3 scripts/closeout_check.py runs/ciph-v0.2-init-run/MANIFEST.json --root .
python3 scripts/closeout_check.py runs/ciph-v0.3-run-checks/MANIFEST.json --root .
python3 scripts/closeout_check.py runs/ciph-v0.4-manifest-lint/MANIFEST.json --root .
python3 scripts/closeout_check.py runs/ciph-v0.5-usability-reports/MANIFEST.json --root .
python3 scripts/closeout_check.py runs/ciph-v0.6-child-tasks/MANIFEST.json --root .
python3 scripts/closeout_check.py runs/ciph-v0.7-candidates/MANIFEST.json --root .
python3 scripts/closeout_check.py runs/ciph-v0.8-repo-gate/MANIFEST.json --root .
```
