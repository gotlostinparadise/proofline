# Complex Implementation Project Harness

CIPH is a file-backed harness for complex coding work. It keeps the project objective, implementation plan, required artifacts, verification evidence, and closeout checklist in the repository so future agents can inspect the actual work state instead of relying on chat memory.

## Lifecycle

1. Intake: capture the user objective, constraints, permissions, volatile facts, and required deliverables.
2. Scope: map every explicit requirement to planned artifacts, evidence, commands, or known blockers.
3. Design: choose the smallest architecture that can satisfy the objective and record non-goals.
4. Execute: implement within the agreed write boundaries and preserve material decisions.
5. Verify: run evaluator-aligned commands and record evidence paths in the manifest.
6. Close: compare the original objective to concrete artifacts and evidence before claiming completion.

## Contracts

### Task Contract

Each run starts with `TASK.md`. It records the original objective, acceptance object, constraints, non-goals, volatile facts that require source verification, and intended deliverables.

### Artifact Contract

Each required artifact is listed in `MANIFEST.json` with a path, description, and required flag. Required artifacts must exist before closeout.

### Evidence Contract

Every required check must have an evidence path. Evidence can be a local file or an external source reference. Local evidence paths are verified by `scripts/verify_manifest.py`.

### Fact Contract

Facts about APIs, configuration keys, CLI flags, pricing, schemas, product behavior, or other volatile details must be sourced from the most authoritative available documentation before code or setup instructions depend on them.

### Delegation Contract

Delegated work requires a bounded task packet, clear write ownership, expected output paths, and local verification after return. Child-agent self-report is not completion evidence.

### Stop Contract

A run is complete only when the closeout checklist maps every explicit requirement to existing artifacts and evidence, or when remaining gaps are recorded as concrete blockers.

## Commands

Create a run:

```bash
python3 scripts/init_run.py <run-id> --objective "Describe the coding task."
```

Lint the manifest:

```bash
python3 scripts/lint_manifest.py runs/<run-id>/MANIFEST.json --root .
```

Lint manifests before running checks so placeholders, missing evidence links, and weak required-check evidence paths fail early.

Run executable checks:

```bash
python3 scripts/run_checks.py runs/<run-id>/MANIFEST.json --root .
```

Run checks before manifest validation when checks use `evidence_producer: "run_checks"`.

Validate a run manifest:

```bash
python3 scripts/verify_manifest.py runs/<run-id>/MANIFEST.json --root .
```

Render a closeout checklist:

```bash
python3 scripts/closeout_check.py runs/<run-id>/MANIFEST.json --root .
```

Write reusable reports:

```bash
python3 scripts/run_status.py runs/<run-id>/MANIFEST.json --root . --output runs/<run-id>/artifacts/status.md
python3 scripts/closeout_check.py runs/<run-id>/MANIFEST.json --root . --output runs/<run-id>/artifacts/closeout.md
```

Create a bounded child task packet:

```bash
python3 scripts/init_child_task.py runs/<run-id>/MANIFEST.json <child-id> --owner <role> --write-scope <path>
```

Create and summarize candidates:

```bash
python3 scripts/init_candidate.py runs/<run-id>/MANIFEST.json <candidate-id> --changed-module <module>
python3 scripts/candidate_summary.py runs/<run-id> --output runs/<run-id>/artifacts/candidate-summary.md
```

Run the repository gate:

```bash
python3 scripts/check_repo.py
```

## Minimal Run Layout

```text
runs/<run-id>/
  TASK.md
  MANIFEST.json
  artifacts/
    checks/
      <check-name>.txt
```

Use `templates/TASK.md` and `templates/MANIFEST.json` as starting points.
