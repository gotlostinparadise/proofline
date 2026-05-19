# Delegation Policy

## Policy ID

`policy.delegation`

## Version

`v0.12`

## Purpose

Make parent and child work boundaries explicit so delegated output can be audited, reviewed, and compared.

## Trigger

Apply when work is split across child agents, reviewers, candidate workers, or any bounded external contributor.

## State

Each child needs a task packet, owner, allowed write scope, expected output, and verification expectation. The parent keeps orchestration, evidence promotion, and final closeout authority.

## Evidence

Child self-report is not completion evidence. Completion requires returned artifacts, parent inspection, local verification, and handoff trace events.

## Ablation

Disable delegation or remove parent review to measure handoff recall, defect escape, cost, and wall time.

## Deterministic Hooks

Use `scripts/init_child_task.py`, child packet templates, manifest evidence paths, and future handoff trace validation.
