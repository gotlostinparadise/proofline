# Harness Policy Modules

## Policy ID

`policy.index`

## Version

`v0.12`

## Purpose

Define the readable policy-module layer for research-grade harness optimization. Policy modules describe editable harness strategy. Deterministic scripts still own exact validation, parsing, scoring, and evidence checks.

## Trigger

Use these modules when a run is research-grade, evidence-sensitive, delegated, candidate-based, or intended for later ablation and comparison.

## State

Policy modules are declared by path in the run manifest and reopened before relevant stages. Runtime state remains in run files such as `TASK.html`, `MANIFEST.json`, artifacts, traces, and candidate directories.

## Evidence

Evidence comes from concrete artifacts, check outputs, trace events, and closeout reports. Policy text is not evidence by itself.

## Ablation

Each module is designed to be removed, swapped, or revised independently so research runs can compare mechanism effects.

## Deterministic Hooks

Use `scripts/lint_manifest.py`, `scripts/run_checks.py`, `scripts/verify_manifest.py`, `scripts/closeout_check.py`, and future trace/metric scripts for exact behavior.
