---
name: proofline
description: Use when starting, managing, reviewing, delegating, or closing out multi-step coding work that needs durable scope, artifacts, verification evidence, run manifests, child task packets, candidate comparison, independent review, or auditability across context handoffs.
---

# Proofline

## Overview

Proofline is a repo-native harness for evidence-backed agent work. Use it to make complex coding tasks inspectable by recording the objective, deliverables, artifacts, checks, evidence, and closeout in the repository before claiming completion.

## Decision

Use Proofline for multi-step, high-risk, delegated, review-heavy, or evidence-sensitive work. For a one-line typo or trivial local edit, keep the workflow lightweight unless the user explicitly asks for Proofline.

If the repo already has `scripts/init_run.py`, `templates/MANIFEST.json`, and `harness/CIPH.md`, use the installed harness. If not, install bundled assets first:

```bash
python3 <skill-dir>/scripts/install_proofline.py --target .
```

Use `--force` only when the user has approved overwriting existing `harness/`, `scripts/`, or `templates/` files.

## Start A Run

Create a run before implementation:

```bash
python3 scripts/init_run.py <run-id> --objective "<objective>"
```

Then fill in:

- `runs/<run-id>/TASK.md`: objective, acceptance object, constraints, volatile facts, deliverables, risks, closeout commands.
- `runs/<run-id>/MANIFEST.json`: every explicit requirement mapped to artifact paths, evidence paths, and required checks.

Lint the contract before coding:

```bash
python3 scripts/lint_manifest.py runs/<run-id>/MANIFEST.json --root .
```

Show the user the run contract for approval when the user asked to approve plans or when the scope is ambiguous. Otherwise proceed if they clearly asked for implementation.

## Execute

Implement only inside the agreed scope. When work needs delegated agents, create bounded child packets:

```bash
python3 scripts/init_child_task.py runs/<run-id>/MANIFEST.json <child-id> --owner <role> --write-scope <path>
```

Child-agent self-report is not evidence. Inspect returned changes and verify them locally.

For competing approaches, scaffold candidates:

```bash
python3 scripts/init_candidate.py runs/<run-id>/MANIFEST.json <candidate-id> --changed-module <module>
python3 scripts/candidate_summary.py runs/<run-id> --output runs/<run-id>/artifacts/candidate-summary.md
```

## Verify And Close

Run required checks and write evidence:

```bash
python3 scripts/run_checks.py runs/<run-id>/MANIFEST.json --root .
python3 scripts/verify_manifest.py runs/<run-id>/MANIFEST.json --root .
python3 scripts/run_status.py runs/<run-id>/MANIFEST.json --root . --output runs/<run-id>/artifacts/status.md
python3 scripts/closeout_check.py runs/<run-id>/MANIFEST.json --root . --output runs/<run-id>/artifacts/closeout.md
```

Finish with the repository gate when available:

```bash
python3 scripts/check_repo.py
```

Only claim completion when closeout maps every explicit requirement to existing artifacts and evidence, or when remaining gaps are recorded as blockers.

## Common Mistakes

| Mistake | Fix |
| --- | --- |
| Coding before `TASK.md` and `MANIFEST.json` exist | Create and lint the run contract first. |
| Listing vague deliverables | Use concrete file paths and exact evidence paths. |
| Treating chat or child-agent output as proof | Record command evidence or source references in the manifest. |
| Forgetting generated reports | Write `status.md` and `closeout.md` before final verification. |
| Installing over an existing harness casually | Use installer `--force` only with explicit approval. |
