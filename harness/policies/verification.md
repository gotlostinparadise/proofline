# Verification Policy

## Policy ID

`policy.verification`

## Version

`v0.12`

## Purpose

Ensure completion claims are backed by evaluator-aligned checks, concrete evidence paths, and closeout coverage.

## Trigger

Apply before claiming success, before committing a behavior change, after child return, after recovery, and during final closeout.

## State

Required checks live in `MANIFEST.json`. Evidence lives under the run artifacts directory unless the manifest points to an external source reference.

## Evidence

Passing evidence must include the exact command, exit code, generated-by marker when produced by `run_checks.py`, and a path referenced by a deliverable.

## Ablation

Disable independent verification or reduce required checks to measure defect escape and artifact-contract compliance.

## Deterministic Hooks

Use `scripts/run_checks.py`, `scripts/verify_manifest.py`, `scripts/run_status.py`, `scripts/closeout_check.py`, and `scripts/check_repo.py`.
