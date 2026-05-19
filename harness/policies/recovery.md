# Recovery Policy

## Policy ID

`policy.recovery`

## Version

`v0.12`

## Purpose

Classify failures and guide retries without erasing evidence or collapsing blockers into success.

## Trigger

Apply when a command fails, evidence is missing, a child handoff is incomplete, a trace is malformed, requirements conflict, or the worktree becomes ambiguous.

## State

Record failure class, attempted strategy, changed files, and remaining blocker state in the run artifacts or trace. Preserve failed evidence instead of overwriting it silently.

## Evidence

Recovery requires the original failure output, a stated classification, the attempted fix or blocker, and a later validation event or check result.

## Ablation

Disable structured recovery and compare failed-tool continuation, stage completion, and defect escape.

## Deterministic Hooks

Use command evidence from `scripts/run_checks.py`, trace events from `scripts/lint_trace.py`, and closeout output from `scripts/closeout_check.py`.
