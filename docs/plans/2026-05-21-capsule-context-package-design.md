# Capsule Context Package Design

Date: 2026-05-21

## Capsule Thesis

Capsule is a dependency-free, file-backed context packaging tool for AI agent work.

It answers one question:

> What exact context did the agent receive, where did it come from, and can we reproduce it?

Capsule should not become an agent framework, task runner, eval harness, or workflow system. Its value is narrower: make the input context boundary explicit, deterministic, inspectable, and reproducible.

## Product Boundary

Capsule owns input context.

It should collect selected files, record file metadata and digests, flag obvious context risks, and render a human-readable report. It should produce artifacts that any agent workflow can reference without depending on a hosted service, database, package manager, or runtime framework.

The core noun is `context package`, not task, review, memory, candidate, or tool.

## Proofline Relationship

Proofline owns task proof: requirements, checks, evidence, handoff, and closeout.

Capsule owns context proof: selected inputs, source paths, digests, redactions, and reproducibility.

Proofline can reference a `CAPSULE.json` as optional input evidence, but Capsule must remain useful outside Proofline. This keeps Scopepack, Review Gate, and Effect Ledger inside Proofline later, while preserving Capsule as a true sibling project with a different core noun.

## MVP

The minimal dependency-free Capsule should support:

- deterministic file selection from explicit paths and simple glob patterns
- path allowlists and ignore patterns
- SHA-256 digests for every included file
- total byte counts and simple line counts
- secret-like content warnings without printing secret values
- redaction records for excluded or masked content
- a machine-readable `CAPSULE.json`
- a plain `FILES.txt`
- a `DIGESTS.json`
- a `REDACTIONS.json`
- a human-readable `capsule.html`
- `create`, `inspect`, and `verify` commands

The first CLI shape should be:

```bash
python3 capsule.py create --root . --include README.md --include "docs/**/*.md"
python3 capsule.py inspect capsules/<id>/CAPSULE.json
python3 capsule.py verify capsules/<id>/CAPSULE.json
```

## Non-Goals

Capsule should not:

- manage tasks or closeout
- run tests or repo gates
- call LLM APIs
- implement memory retrieval
- choose what the agent should do next
- authorize side effects
- compare candidate implementations
- require MCP, Docker, SQLite, GitHub, LangChain, or any hosted service

Those capabilities either belong in Proofline or in separate infrastructure with a different core noun.

## Data Model Sketch

`CAPSULE.json` should contain:

- schema version
- capsule id
- created timestamp
- root path fingerprint
- selection rules
- included files
- excluded files
- per-file digest references
- redaction references
- risk summary
- generator version

`DIGESTS.json` should map normalized relative paths to SHA-256, byte count, and line count.

`REDACTIONS.json` should record what was omitted or masked and why, without exposing secret values.

`capsule.html` should be readable by a human reviewer and should not be required for machine verification.

## Success Test

Capsule is worth continuing if, across 5 real agent tasks, it catches at least 2 concrete context problems:

- missing required file
- stale file included
- oversized context
- secret-like content risk
- mismatch between expected and actual context
- non-reproducible handoff

If it does not catch practical context failures, keep the idea as a small utility and do not turn it into a platform.

## Open Questions

- Should Capsule use only explicit include patterns at first, or offer repo-aware presets?
- Should secret scanning be simple pattern-based only, or support pluggable detectors later?
- Should a Capsule record include the prompt text, or only files and context sources?
- Should Proofline require a Capsule reference for high-risk runs, or keep it optional until field evidence proves value?
