# Context Policy

## Policy ID

`policy.context`

## Version

`v0.12`

## Purpose

Control what an agent reads at each stage so work starts from repo truth and later decisions can be tied to inspected artifacts.

## Trigger

Apply at run start, before implementation, before handoff, before verification, and after any recovery event.

## State

Required context starts with the run task, manifest, implementation plan, relevant source files, relevant tests, and recent evidence. Optional context includes prior candidates and traces when candidate search is active.

## Evidence

Context-sensitive claims should reference files read, commands run, source citations, or trace events. Summaries are useful views, not authoritative context.

## Ablation

Disable bootstrapped context or candidate-history access to measure wasted exploration, stage coverage, and task success changes.

## Deterministic Hooks

Use repository search tools, run manifests, status reports, and future trace metrics to inspect loaded context and context cost.
