# Candidate Search Policy

## Policy ID

`policy.candidate-search`

## Version

`v0.12`

## Purpose

Support Meta-Harness-style optimization by preserving candidate hypotheses, parent lineage, source or policy changes, raw traces, scores, and failure notes.

## Trigger

Apply when competing harness policies, scripts, prompts, workflows, or module ablations are evaluated.

## State

Each candidate records `score.json`, `NOTES.md`, `patch.diff`, trace files, parent IDs, changed modules, and artifacts under its candidate directory.

## Evidence

Candidate claims require raw traces, score records, failure notes when applicable, and comparison output such as a Pareto summary.

## Ablation

Remove one named policy module or deterministic hook at a time. Do not mix unrelated changes into a single ablation candidate.

## Deterministic Hooks

Use `scripts/init_candidate.py`, `scripts/candidate_summary.py`, candidate score JSON, and future metric scripts.
