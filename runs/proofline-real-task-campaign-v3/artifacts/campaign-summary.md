# Proofline Real-Task Campaign v3

Date: 2026-05-21

## What this run checked

- ciph-v0.22-replay-result-attestation
- ciph-v0.21-local-replay-executor
- ciph-v0.20-evaluator-replay-readiness
- ciph-v0.19-score-integrity
- ciph-v0.18-mechanism-metrics

## What happened

- None of the 5 runs produced a high-severity issue.
- Catch rate: `0/5`
- Threshold: `2/5`
- Decision: keep optimizer tooling as research-only.

No optimizer commands were run in this campaign.

campaign-hit-summary: 0/5
campaign-acceptance-threshold: 2/5
campaign-decision: keep optimizer tooling research-only

- Diagnostics executed with `python3 scripts/diagnose_experience_store.py --root . --runs-dir runs --min-severity high`.
- This run intentionally executes no candidate/evaluation/replay commands.
