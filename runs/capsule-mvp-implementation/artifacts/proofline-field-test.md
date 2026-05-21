# Proofline Field-Test Finding

Date: 2026-05-22

## Proofline field-test finding

Concrete catch: yes.

During implementation planning, the manifest had to place `capsule-example-create` before `capsule-example-inspect` and `capsule-example-verify`. That create-before-inspect ordering made the generated example capsule explicit instead of relying on a stale or manually created `capsules/docs-context` directory.

Proofline also forced the secret-risk requirement into both tests and manifest checks: secret-like warnings must be recorded without printing matched values.

## Category

scope-control, weak-evidence

## Decision

Count this as one concrete core Proofline implementation catch.

This run used no optimizer, candidate, evaluation, or replay tooling.
