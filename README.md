# Agent Harness

This repository contains CIPH, the Complex Implementation Project Harness. CIPH is a small file-backed harness for complex coding projects. It keeps the objective, deliverables, artifacts, checks, evidence, and closeout audit in the repository.

## Quick Start

Create a run:

```bash
python3 scripts/init_run.py my-run --objective "Describe the coding task here."
```

Edit the generated files:

```text
runs/my-run/
  TASK.md
  MANIFEST.json
  artifacts/
```

Record each explicit requirement from the prompt in `MANIFEST.json`. Point each requirement at concrete artifact paths and evidence paths.

Lint the manifest for weak contracts:

```bash
python3 scripts/lint_manifest.py runs/my-run/MANIFEST.json --root .
```

Run executable checks and write fresh evidence:

```bash
python3 scripts/run_checks.py runs/my-run/MANIFEST.json --root .
```

Validate the manifest:

```bash
python3 scripts/verify_manifest.py runs/my-run/MANIFEST.json --root .
```

Render the closeout checklist:

```bash
python3 scripts/closeout_check.py runs/my-run/MANIFEST.json --root .
```

## Files

- `harness/CIPH.md`: harness lifecycle and contracts.
- `harness/runtime-charter.md`: runtime rules for facts, evidence, delegation, and closeout.
- `templates/TASK.md`: task template used by the initializer.
- `templates/MANIFEST.json`: manifest template used by the initializer.
- `scripts/init_run.py`: creates a run directory from templates.
- `scripts/lint_manifest.py`: catches placeholders and weak manifest contracts.
- `scripts/run_checks.py`: runs manifest checks and writes structured evidence.
- `scripts/verify_manifest.py`: validates manifest structure and required local paths.
- `scripts/closeout_check.py`: prints the prompt-to-artifact closeout checklist.

## Development Checks

```bash
python3 -m unittest discover
python3 scripts/lint_manifest.py runs/example-harness-design/MANIFEST.json --root .
python3 scripts/lint_manifest.py runs/ciph-v0.2-init-run/MANIFEST.json --root .
python3 scripts/lint_manifest.py runs/ciph-v0.3-run-checks/MANIFEST.json --root .
python3 scripts/lint_manifest.py runs/ciph-v0.4-manifest-lint/MANIFEST.json --root .
python3 scripts/run_checks.py runs/ciph-v0.3-run-checks/MANIFEST.json --root .
python3 scripts/run_checks.py runs/ciph-v0.4-manifest-lint/MANIFEST.json --root .
python3 scripts/verify_manifest.py runs/example-harness-design/MANIFEST.json --root .
python3 scripts/verify_manifest.py runs/ciph-v0.2-init-run/MANIFEST.json --root .
python3 scripts/verify_manifest.py runs/ciph-v0.3-run-checks/MANIFEST.json --root .
python3 scripts/verify_manifest.py runs/ciph-v0.4-manifest-lint/MANIFEST.json --root .
python3 scripts/closeout_check.py runs/example-harness-design/MANIFEST.json --root .
python3 scripts/closeout_check.py runs/ciph-v0.2-init-run/MANIFEST.json --root .
python3 scripts/closeout_check.py runs/ciph-v0.3-run-checks/MANIFEST.json --root .
python3 scripts/closeout_check.py runs/ciph-v0.4-manifest-lint/MANIFEST.json --root .
```
