---
name: proofline
description: Use when starting, managing, reviewing, delegating, or closing out multi-step coding work that needs durable scope, artifacts, verification evidence, run manifests, child task packets, candidate comparison, independent review, or auditability across context handoffs.
---

# Proofline

## Overview

Proofline is a repo-native harness for evidence-backed agent work. Use it to make complex coding tasks inspectable by recording the objective, deliverables, artifacts, checks, evidence, and closeout in the repository before claiming completion.

For research-grade runs, Proofline also records policy modules and a raw `TRACE.jsonl` ledger. Policy modules describe editable harness strategy; deterministic scripts still own exact validation, scoring, trace linting, mechanism metrics, and closeout checks.

## Decision

Use Proofline for multi-step, high-risk, delegated, review-heavy, or evidence-sensitive work. For a one-line typo or trivial local edit, keep the workflow lightweight unless the user explicitly asks for Proofline.

If the repo already has `vendor/proofline/scripts/init_run.py`, use the vendored harness. If not, install bundled assets first:

```bash
python3 <skill-dir>/scripts/install_proofline.py --target .
```

This installs Proofline under `vendor/proofline` so product files stay separate from harness files. Use `--force` only when the user has approved overwriting existing files under `vendor/proofline`.

## Start A Run

Create a run before implementation:

```bash
python3 vendor/proofline/scripts/init_run.py <run-id> --root . --proofline-root vendor/proofline --objective "<objective>"
```

Then fill in:

- `vendor/proofline/runs/<run-id>/TASK.html`: objective, acceptance object, constraints, volatile facts, deliverables, risks, closeout commands.
- `vendor/proofline/runs/<run-id>/MANIFEST.json`: every explicit requirement mapped to project-root-relative artifact paths, evidence paths, required checks, policy modules, and trace metadata.
- `vendor/proofline/runs/<run-id>/TRACE.jsonl`: raw research trace events; it may start empty.

Lint the contract before coding:

```bash
python3 vendor/proofline/scripts/lint_manifest.py vendor/proofline/runs/<run-id>/MANIFEST.json --root .
python3 vendor/proofline/scripts/lint_trace.py vendor/proofline/runs/<run-id>/TRACE.jsonl --root .
```

Show the user the run contract for approval when the user asked to approve plans or when the scope is ambiguous. Otherwise proceed if they clearly asked for implementation.

## Execute

Implement only inside the agreed scope. When work needs delegated agents, create bounded child packets:

```bash
python3 vendor/proofline/scripts/init_child_task.py vendor/proofline/runs/<run-id>/MANIFEST.json <child-id> --owner <role> --write-scope <path>
```

Child-agent self-report is not evidence. Inspect returned changes and verify them locally.

For competing approaches, scaffold and validate candidates:

```bash
python3 vendor/proofline/scripts/init_candidate.py vendor/proofline/runs/<run-id>/MANIFEST.json <candidate-id> --changed-module <module>
python3 vendor/proofline/scripts/validate_candidate.py vendor/proofline/runs/<run-id>/candidates/<candidate-id> --root . --output vendor/proofline/runs/<run-id>/artifacts/candidate-validation.html
python3 vendor/proofline/scripts/candidate_summary.py vendor/proofline/runs/<run-id> --output vendor/proofline/runs/<run-id>/artifacts/candidate-summary.html
```

For search-set / holdout research runs, validate the evaluation protocol and release holdout only through the gate:

```bash
python3 vendor/proofline/scripts/validate_evaluation.py vendor/proofline/runs/<run-id> --root . --output vendor/proofline/runs/<run-id>/artifacts/evaluation-report.html
python3 vendor/proofline/scripts/release_holdout.py vendor/proofline/runs/<run-id> --root . --released-at 2026-05-20T04:00:00Z --output vendor/proofline/runs/<run-id>/artifacts/holdout-release.html
python3 vendor/proofline/scripts/ingest_holdout_scores.py vendor/proofline/runs/<run-id> vendor/proofline/runs/<run-id>/artifacts/frontier-holdout-input.json --root . --output vendor/proofline/runs/<run-id>/artifacts/holdout-ingest.html
python3 vendor/proofline/scripts/validate_score_provenance.py vendor/proofline/runs/<run-id> --root . --output vendor/proofline/runs/<run-id>/artifacts/score-provenance.html
python3 vendor/proofline/scripts/validate_score_integrity.py vendor/proofline/runs/<run-id> --root . --output vendor/proofline/runs/<run-id>/artifacts/score-integrity.html
python3 vendor/proofline/scripts/validate_evaluator_replay.py vendor/proofline/runs/<run-id> --root . --output vendor/proofline/runs/<run-id>/artifacts/evaluator-replay.html
python3 vendor/proofline/scripts/final_comparison.py vendor/proofline/runs/<run-id> --root . --output vendor/proofline/runs/<run-id>/artifacts/final-comparison.html
```

## Verify And Close

Run required checks and write evidence:

```bash
python3 vendor/proofline/scripts/run_checks.py vendor/proofline/runs/<run-id>/MANIFEST.json --root .
python3 vendor/proofline/scripts/lint_trace.py vendor/proofline/runs/<run-id>/TRACE.jsonl --root .
python3 vendor/proofline/scripts/verify_manifest.py vendor/proofline/runs/<run-id>/MANIFEST.json --root .
python3 vendor/proofline/scripts/trace_metrics.py vendor/proofline/runs/<run-id>/MANIFEST.json --root . --output vendor/proofline/runs/<run-id>/artifacts/mechanism-metrics.html
python3 vendor/proofline/scripts/run_status.py vendor/proofline/runs/<run-id>/MANIFEST.json --root . --output vendor/proofline/runs/<run-id>/artifacts/status.html
python3 vendor/proofline/scripts/closeout_check.py vendor/proofline/runs/<run-id>/MANIFEST.json --root . --output vendor/proofline/runs/<run-id>/artifacts/closeout.html
```

Finish with the repository gate when available:

```bash
python3 vendor/proofline/scripts/check_repo.py --root . --runs-dir vendor/proofline/runs
```

Only claim completion when closeout maps every explicit requirement to existing artifacts and evidence, or when remaining gaps are recorded as blockers.

## Common Mistakes

| Mistake | Fix |
| --- | --- |
| Coding before `TASK.html` and `MANIFEST.json` exist | Create and lint the run contract first. |
| Listing vague deliverables | Use concrete file paths and exact evidence paths. |
| Forgetting trace linting on research-grade runs | Run `lint_trace.py` against `TRACE.jsonl`. |
| Treating mechanism metrics as completion proof | Run `trace_metrics.py` for diagnostics, then keep `verify_manifest.py` and closeout evidence authoritative. |
| Summarizing candidate scores before validating records | Run `validate_candidate.py` for each candidate first. |
| Releasing holdout scores during search | Record split state in `EVALUATION.json`, run `validate_evaluation.py`, then use `release_holdout.py`. |
| Manually flipping `phase` or `holdout_set.sealed` | Use `release_holdout.py` so frontier validation, release budget, and release history are checked. |
| Writing holdout scores into `score.json` | Use `ingest_holdout_scores.py` so search and holdout records stay separate. |
| Treating score numbers as self-proving | Add evaluator manifests and run `validate_score_provenance.py`. |
| Treating evaluator artifacts as immutable | Add SHA-256 integrity maps and run `validate_score_integrity.py`. |
| Treating replay as safe because a command string exists | Add metadata-only replay contracts and run `validate_evaluator_replay.py`. |
| Picking a final winner from search scores | Use `final_comparison.py` after holdout score ingestion. |
| Treating chat or child-agent output as proof | Record command evidence or source references in the manifest. |
| Forgetting generated reports | Write `status.html` and `closeout.html` before final verification. |
| Installing over an existing harness casually | Use installer `--force` only with explicit approval. |
