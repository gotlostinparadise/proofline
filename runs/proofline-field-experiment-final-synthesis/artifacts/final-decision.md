# Proofline Field Experiment Final Decision

Date: 2026-05-21

## Final decision

Keep Proofline core.

Keep optimizer tooling research-only.

## Evidence Summary

- Trials recorded: 6
- Core Proofline concrete catches: 5/6
- Optimizer-layer practical wins: 0

## What Proofline Core Proved

Proofline core helped with:

- scope-control during Capsule design
- trace-contract validation during Capsule design closeout
- scope-control during Capsule MVP planning
- weak-evidence detection during Capsule plan review
- unclear-handoff repair during final synthesis
- generated-evidence ordering and secret-risk checks during Capsule MVP implementation

## What The Optimizer Layer Did Not Prove

The retrospective campaign produced `0/5` high-severity catches against a `2/5` threshold.

That is not enough evidence to make candidate/evaluation/replay/optimizer tooling part of the default path.

## Product Boundary

Default Proofline should remain:

- task contract
- manifest
- trace
- required checks
- status
- closeout
- repo gate

Research tooling remains optional and explicit.

## Capsule Outcome

Capsule MVP implementation is complete.

Delivered:

- `capsule.py`
- `tests/test_capsule.py`
- `docs/capsule.md`
- `capsules/docs-context/CAPSULE.json`

Next work is integration closeout, then real-use Capsule trials if needed.
