# Capsule MVP Implementation Plan

Date: 2026-05-21

## Objective

Implement the first dependency-free Capsule MVP as a local context packaging tool.

Capsule must answer:

> What exact context did the agent receive, where did it come from, and can we reproduce it?

This plan converts `docs/plans/2026-05-21-capsule-context-package-design.md` into a bounded implementation sequence. It does not implement Capsule in this field-trial run.

## Write Scope

Expected files for the implementation run:

- `capsule.py`
- `tests/test_capsule.py`
- `docs/capsule.md`
- `docs/plans/2026-05-21-capsule-mvp-implementation-plan.md`
- `runs/<future-capsule-implementation-run>/...`

No package manager, database, network service, external scanner, Docker setup, or hosted API should be added.

## Data Model

`CAPSULE.json` should include:

- `schema_version`
- `capsule_id`
- `created_at_utc`
- `root`
- `selection_rules`
- `included_files`
- `excluded_files`
- `digests_path`
- `redactions_path`
- `risk_summary`
- `generator`

`DIGESTS.json` should map normalized relative paths to:

- SHA-256 digest
- byte count
- line count

`REDACTIONS.json` should record omitted or masked content reasons without printing secret values.

`FILES.txt` should list included paths in deterministic order.

`capsule.html` should render a human-readable report but must not be required for verification.

## CLI Surface

First implementation should support:

```bash
python3 capsule.py create --root . --id docs-context --include README.md --include "docs/**/*.md"
python3 capsule.py inspect capsules/<id>/CAPSULE.json
python3 capsule.py verify capsules/<id>/CAPSULE.json
```

The `create` command should write a new directory under `capsules/<id>/`. The MVP should require or accept `--id` so tests and handoffs can use deterministic capsule paths. If `--id` is omitted in later versions, a generated id is acceptable, but the first implementation should keep deterministic ids first.

The `inspect` command should print a concise summary: file count, byte count, warning count, and artifact paths.

The `verify` command should recompute file digests and fail if included files changed, disappeared, or no longer match the capsule record.

## Implementation Phases

1. Define path normalization, deterministic glob expansion, ignore handling, and output directory creation.
2. Implement digest collection with SHA-256, byte count, and line count.
3. Implement simple secret-like risk detection without printing matched values.
4. Implement `CAPSULE.json`, `FILES.txt`, `DIGESTS.json`, and `REDACTIONS.json` writers.
5. Implement `inspect` and `verify`.
6. Render `capsule.html`.
7. Add focused unit tests and a small fixture workspace.
8. Add docs with examples and non-goals.

## Acceptance Criteria

The implementation is acceptable when:

- `create` produces all five MVP artifacts.
- file ordering is deterministic.
- `verify` passes immediately after `create`.
- `verify` fails after an included file changes.
- secret-like warnings are recorded without leaking matched values.
- `inspect` prints a useful summary without requiring HTML parsing.
- tests cover create, inspect, verify, ignore behavior, digest mismatch, and warning redaction.
- docs explain Capsule's relationship to Proofline.

## Verification Commands

Expected implementation verification:

```bash
python3 -m unittest tests.test_capsule
python3 capsule.py create --root . --id docs-context --include README.md --include "docs/**/*.md"
python3 capsule.py inspect capsules/docs-context/CAPSULE.json
python3 capsule.py verify capsules/docs-context/CAPSULE.json
python3 scripts/check_repo.py
```

The exact capsule id should be deterministic for tests. Manual runs may later support generated ids, but the MVP should keep `--id` available and documented.

## Non-Goals

The MVP must not:

- manage Proofline task state
- run repo checks
- call LLM APIs
- read or write external services
- implement memory retrieval
- authorize side effects
- compare candidates
- require third-party dependencies

## Field-Test Boundary

This field trial creates the implementation plan only.

The next field trial should review and harden this plan before any `capsule.py` implementation begins. This protects the experiment from turning broad approval into uncontrolled implementation drift.
