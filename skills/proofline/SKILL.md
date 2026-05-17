---
name: proofline
description: Use when starting, managing, reviewing, delegating, or closing out multi-step coding work that needs durable scope, artifacts, verification evidence, run manifests, child task packets, candidate comparison, independent review, or auditability across context handoffs.
---

# Proofline

## Overview

Proofline is a repo-native harness for evidence-backed agent work. Use it to make complex coding tasks inspectable by recording the objective, deliverables, artifacts, checks, evidence, and closeout in the repository before claiming completion.

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
- `vendor/proofline/runs/<run-id>/MANIFEST.json`: every explicit requirement mapped to project-root-relative artifact paths, evidence paths, and required checks.

Lint the contract before coding:

```bash
python3 vendor/proofline/scripts/lint_manifest.py vendor/proofline/runs/<run-id>/MANIFEST.json --root .
```

Show the user the run contract for approval when the user asked to approve plans or when the scope is ambiguous. Otherwise proceed if they clearly asked for implementation.

## Execute

Implement only inside the agreed scope. When work needs delegated agents, create bounded child packets:

```bash
python3 vendor/proofline/scripts/init_child_task.py vendor/proofline/runs/<run-id>/MANIFEST.json <child-id> --owner <role> --write-scope <path>
```

Child-agent self-report is not evidence. Inspect returned changes and verify them locally.

For competing approaches, scaffold candidates:

```bash
python3 vendor/proofline/scripts/init_candidate.py vendor/proofline/runs/<run-id>/MANIFEST.json <candidate-id> --changed-module <module>
python3 vendor/proofline/scripts/candidate_summary.py vendor/proofline/runs/<run-id> --output vendor/proofline/runs/<run-id>/artifacts/candidate-summary.html
```

## Verify And Close

Run required checks and write evidence:

```bash
python3 vendor/proofline/scripts/run_checks.py vendor/proofline/runs/<run-id>/MANIFEST.json --root .
python3 vendor/proofline/scripts/verify_manifest.py vendor/proofline/runs/<run-id>/MANIFEST.json --root .
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
| Treating chat or child-agent output as proof | Record command evidence or source references in the manifest. |
| Forgetting generated reports | Write `status.html` and `closeout.html` before final verification. |
| Installing over an existing harness casually | Use installer `--force` only with explicit approval. |
