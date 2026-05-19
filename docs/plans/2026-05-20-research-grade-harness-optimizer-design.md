# Research-Grade Harness Optimizer Design

## Goal

Turn CIPH / Proofline into a research-grade harness optimizer from the start, without discarding the existing repo-native proof workflow. The project should support daily evidence-backed agent work and also support controlled harness research: explicit policy modules, raw traces, candidate search, mechanism metrics, ablation, and holdout-safe evaluation.

## Source Baseline

This design is grounded in two papers:

- Natural-Language Agent Harnesses: harness policy should be an explicit, editable natural-language object interpreted by a thin runtime, while exact tools, validators, parsers, and safety controls stay in code.
- Meta-Harness: harness optimization should expose source, scores, and raw execution traces through the filesystem so a proposer can diagnose prior candidates instead of relying on compressed summaries.

## Current Repo Fit

The current repository already has the right substrate:

- `TASK.html` and `MANIFEST.json` provide durable task contracts.
- `scripts/run_checks.py`, `scripts/verify_manifest.py`, and `scripts/closeout_check.py` provide exact evidence and closeout gates.
- `scripts/init_child_task.py` provides bounded delegation packets.
- `scripts/init_candidate.py` and `scripts/candidate_summary.py` provide an early candidate and Pareto scaffold.
- `skills/proofline/` provides a portable Codex skill bundle.

The missing layer is research structure: named policy modules, strict trace events, mechanism metrics, search-set / holdout discipline, and tools for comparing candidate harnesses.

## Architecture

### 1. Proofline Core

The existing CIPH workflow remains the execution floor. It owns task intake, manifest contracts, exact checks, artifact existence, evidence files, closeout reports, and repository health gates. This layer must stay simple and deterministic.

### 2. NLAH Policy Layer

Add natural-language harness policy documents under `harness/policies/`. Each policy is a readable module with an ID, version, purpose, trigger conditions, required state, evidence requirements, ablation switch, and related deterministic hooks.

Initial modules:

- `state`: what persists across stages, retries, children, and resumed sessions.
- `context`: what must be loaded at run start and before each stage.
- `verification`: when checks run and what evidence is sufficient.
- `recovery`: how failures, missing evidence, and partial work are classified.
- `delegation`: parent / child boundaries, ownership, handoff, and review rules.
- `candidate-search`: how candidate hypotheses, parent lineage, traces, and scores are recorded.
- `stopping`: success, blocker, budget exhaustion, and unsafe-to-continue gates.

### 3. Runtime Semantics

Add a fixed runtime charter that defines how agents interpret policy modules. It should not encode task-specific strategy. It should define shared meanings for state roots, trace roots, stage names, parent / child boundaries, evidence promotion, budgets, retries, and completion.

### 4. Trace Ledger

Every research run should include a strict `TRACE.jsonl` ledger. Events should be machine-readable and linted before closeout. Required event families:

- `stage.started`, `stage.completed`
- `state.written`, `state.loaded`
- `model.call`, `model.result`
- `tool.call`, `tool.result`
- `handoff.created`, `handoff.returned`, `handoff.reviewed`
- `validation.started`, `validation.completed`
- `candidate.created`, `candidate.scored`
- `failure.classified`, `recovery.attempted`
- `budget.updated`
- `closeout.completed`

Trace events are not summaries. Summary HTML reports are views over the ledger.

### 5. Mechanism Metrics

Add deterministic metric calculation over manifests and traces:

- Artifact contract compliance
- Stage coverage
- Ordered workflow compliance
- Tool-call success
- Failed-tool continuation
- Handoff recall
- Validation coverage
- Recovery completion
- Context cost
- Wall time
- Defect escape rate

These metrics should feed candidate scoring alongside task success.

### 6. Meta-Harness Lab

Extend candidate directories into full research records:

```text
runs/<run-id>/candidates/<candidate-id>/
  policy/
  source/
  patch.diff
  score.json
  TRACE.jsonl
  NOTES.md
  artifacts/
```

The candidate lab must preserve parent lineage, hypotheses, changed modules, raw traces, scores, and diffs. The proposer should be able to query this filesystem with normal tools such as `rg`, `sed`, and small helper CLIs.

### 7. Evaluation Protocol

Research-grade runs need split discipline:

- A baseline harness is evaluated first.
- Search candidates score only on the search set.
- Holdout results are hidden until frontier selection.
- Budgets are fixed and recorded.
- Ablations remove or swap one named policy module at a time.
- Final reports distinguish search-set scores from holdout scores.

## Non-Goals

- Do not replace deterministic validation with natural language.
- Do not hide raw traces behind summaries.
- Do not force every daily Proofline run through optimizer machinery.
- Do not implement provider-specific model APIs inside this repository unless a later milestone explicitly requires it.
- Do not make the proposer responsible for running final evaluation; external scripts score candidates and write results.

## First Milestone

Start with `v0.12 Policy Modules + Trace Schema`.

This creates the research-grade skeleton without requiring a full optimizer loop. Once policy modules and traces are lintable, later milestones can add mechanism metrics, candidate comparison tools, and search / holdout evaluation.

## Success Criteria

- The repo contains named policy modules that are readable, versioned, and ablatable.
- A new run can declare which policy modules apply.
- A research run can write `TRACE.jsonl` events with strict validation.
- Trace linting fails on malformed events, unknown event types, missing required fields, and invalid candidate references.
- Reports can treat trace data as authoritative and summaries as derived views.
