# Proofline Field Trials

Date: 2026-05-21

## Purpose

This register tracks whether Proofline helps during real agent-assisted work.

The evaluation question is:

> Does Proofline prevent lost scope, weak evidence, premature closeout, unclear handoff, or scope drift in real tasks?

This register is for field evidence. It is not a marketing page, roadmap, or optimizer benchmark.

## Counting Rules

A task counts as a concrete Proofline catch only when all of these are true:

- the issue appeared during real work
- the issue maps to a practical failure category
- a repo artifact records the issue
- a check, manifest, trace, or closeout artifact made the issue visible or forced correction

Do not count general good feelings, cleaner narration, or chat-only observations.

Keep optimizer, candidate, evaluation, and replay tooling separate from core Proofline field trials unless the task explicitly tests that research layer.

## Final Register

| Trial | Work Type | Proofline Layer | Source Evidence | Concrete Catch | Category | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| `proofline-real-task-campaign-v3` | retrospective campaign over 5 recent runs | core diagnostics over historical run evidence | `runs/proofline-real-task-campaign-v3/artifacts/campaign-summary.md` | no; `0/5` high-severity hits against `2/5` threshold | none | keep optimizer tooling research-only |
| `proofline-capsule-design-field-test` | live dependency-free infrastructure design | core task/manifest/trace/checks/closeout | `runs/proofline-capsule-design-field-test/artifacts/proofline-field-test.md` | yes | scope-control, trace-contract | core Proofline was useful for serious design work |
| `proofline-capsule-mvp-plan-field-test` | live implementation planning | core task/manifest/trace/checks/closeout | `runs/proofline-capsule-mvp-plan-field-test/artifacts/proofline-field-test.md` | yes | scope-control | core Proofline kept broad approval from turning into premature implementation |
| `proofline-capsule-plan-review-field-test` | live plan review and hardening | core task/manifest/trace/checks/closeout | `runs/proofline-capsule-plan-review-field-test/artifacts/proofline-field-test.md` | yes | weak-evidence | core Proofline caught missing deterministic id behavior before implementation |
| `proofline-field-experiment-final-synthesis` | final experiment synthesis | core task/manifest/trace/checks/closeout | `runs/proofline-field-experiment-final-synthesis/artifacts/proofline-field-test.md` | yes | unclear-handoff | core Proofline converted unclear results into a final decision and audit |
| `capsule-mvp-implementation` | Capsule MVP implementation | core task/manifest/trace/checks/closeout | `runs/capsule-mvp-implementation/artifacts/proofline-field-test.md` | yes | scope-control, weak-evidence | core Proofline kept generated example evidence ordered and secret-risk behavior tested |

## Final Readout

The field experiment is complete enough to decide the current product boundary.

Results:

- total trials recorded: 6
- concrete core Proofline catches: 5
- optimizer/research-layer wins: 0
- threshold for preserving core Proofline: met
- threshold for promoting optimizer tooling: not met

The retrospective campaign did not justify promoting optimizer tooling. It produced `0/5` high-severity catches and supports keeping candidate/evaluation/replay tools as research-only.

The live field trials did justify preserving the minimal Proofline core. The useful catches were scope-control, weak evidence, trace-contract validation, and unclear handoff.

Final decision:

- keep the default Proofline path minimal
- do not promote the optimizer layer
- use Proofline for serious agent-infrastructure design, planning, review, and closeout
- keep counting only repo-backed catches
- Capsule MVP implementation is complete
- next project step is integration closeout, then future Capsule hardening only if real use exposes gaps

## Capsule Implementation Outcome

Capsule MVP has been implemented.

Delivered artifacts:

- `capsule.py`
- `tests/test_capsule.py`
- `docs/capsule.md`
- `capsules/docs-context/CAPSULE.json`
- `capsules/docs-context/FILES.txt`
- `capsules/docs-context/DIGESTS.json`
- `capsules/docs-context/REDACTIONS.json`
- `capsules/docs-context/capsule.html`

Verified behavior:

- `create` writes all MVP capsule artifacts
- `inspect` prints a concise summary
- `verify` passes on fresh capsules and fails after included files change
- secret-like warnings do not print matched values
- deterministic `--id docs-context` is part of the contract

## Next Work

No more Proofline product expansion is needed for this phase.

The next useful work after integration closeout is to use Capsule on real agent tasks and record whether it catches concrete context problems.

## Stop Rule Outcome

The stop rule has fired.

Core Proofline produced at least 2 concrete repo-backed catches across the field trials. Keep the minimal core.

Optimizer tooling did not produce practical field wins. Keep it research-only.
