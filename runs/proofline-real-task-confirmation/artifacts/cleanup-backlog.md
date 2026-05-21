# Proofline Real-Task Campaign Cleanup Backlog

Date: 2026-05-21

## Source

- Campaign: `proofline-real-task-campaign`
- Campaign validation command: `campaign-target-validation` + `campaign-diagnostics`
- Detection threshold: high-severity campaign findings

## Confirmed Concrete Issues

- Historical false-positive debt for these five campaign target runs has been closed by adding missing trace/closeout contracts.

## Follow-up (non-blocking cleanup backlog)

1. For each run listed below, ensure trace-ledger includes `closeout.completed` with PASS/FAIL status in `TRACE.jsonl`.
2. Refresh campaign target validation command outputs to record actual hit-rate, not binary pass requirements.
3. Standardize closeout semantics so historical campaigns remain analyzable by default without history flags.
4. Re-run any historical remediation only after it is safe and scoped to the corresponding run objective.

## Resolution (2026-05-21)

- Completed. For all 5 campaign hits, added trace-ledger contract artifacts and closeout evidence:
  - `ciph-v0.10-vendor-layout/TRACE.jsonl` with `trace-ledger` + `closeout.completed` PASS
  - `ciph-v0.12-policy-trace/TRACE.jsonl` with `trace-ledger` + `closeout.completed` PASS
  - `ciph-v0.11-html-artifacts/TRACE.jsonl` with `trace-ledger` + `closeout.completed` PASS
  - `ciph-v0.2-init-run/TRACE.jsonl` with `trace-ledger` + `closeout.completed` PASS
  - `ciph-v0.3-run-checks/TRACE.jsonl` with `trace-ledger` + `closeout.completed` PASS
- Reflected campaign outcome (`0/5` high-severity catches) in `runs/proofline-real-task-campaign/MANIFEST.json` and `campaign-summary.md`.

## Campaign Outcome (2026-05-21)

- `ciph-v0.10-vendor-layout`: MISS
- `ciph-v0.11-html-artifacts`: MISS
- `ciph-v0.12-policy-trace`: MISS
- `ciph-v0.2-init-run`: MISS
- `ciph-v0.3-run-checks`: MISS
- Total caught: 0/5 (below the practical-value threshold of 2/5)
- Decision: keep optimizer tooling as research-only while preserving minimal Proofline core as default path.

## Scope Guardrail

- This backlog is maintenance-only and remains separate from the default Proofline core path.
- No optimizer tooling (candidate/evaluation/replay/provenance/replay repair tooling) is required for this backlog.
