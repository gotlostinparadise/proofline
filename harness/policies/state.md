# State Policy

## Policy ID

`policy.state`

## Version

`v0.12`

## Purpose

Make long-running work inspectable by preserving the information needed to resume, audit, delegate, retry, and compare harness candidates.

## Trigger

Apply when a run has more than one stage, uses children or candidates, records recovery attempts, or may be resumed after context loss.

## State

Write durable state under the run directory. The authoritative state carriers are `TASK.html`, `MANIFEST.json`, `TRACE.jsonl`, generated artifacts, child packets, candidate records, and closeout reports. Do not rely on chat memory for required state.

## Evidence

State claims require a concrete path and, for research runs, a `state.written` or `state.loaded` trace event.

## Ablation

Disable this module by forbidding new state files beyond the manifest and comparing outcome, handoff recall, and recovery quality.

## Deterministic Hooks

`scripts/verify_manifest.py` validates required local paths. `scripts/lint_trace.py` validates state trace events once trace linting exists.
