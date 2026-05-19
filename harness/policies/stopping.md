# Stopping Policy

## Policy ID

`policy.stopping`

## Version

`v0.12`

## Purpose

Define when a run may end as success, blocker, budget exhaustion, or unsafe-to-continue.

## Trigger

Apply before final answers, before closeout, when budgets are exhausted, when required evidence is missing, or when safety constraints block progress.

## State

Stop state belongs in closeout artifacts, check evidence, trace events, and any blocker notes referenced by the manifest.

## Evidence

Success requires all required artifacts and evidence to exist. Blockers require a concrete reason, affected requirement, and the evidence or source that proves the blocker.

## Ablation

Relax or tighten stopping gates to measure task success, false success, defect escape, cost, and wall time.

## Deterministic Hooks

Use `scripts/verify_manifest.py`, `scripts/closeout_check.py`, `scripts/check_repo.py`, and future budget or trace metrics.
