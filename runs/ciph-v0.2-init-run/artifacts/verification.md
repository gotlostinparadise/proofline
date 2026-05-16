# Verification Evidence

## Initializer Dogfood

Command:

```bash
python3 scripts/init_run.py ciph-v0.2-init-run --objective "Add a quick-start README and init_run command for CIPH v0.2."
```

Observed output:

```text
Created CIPH run: runs/ciph-v0.2-init-run
- Task: runs/ciph-v0.2-init-run/TASK.md
- Manifest: runs/ciph-v0.2-init-run/MANIFEST.json
- Artifacts: runs/ciph-v0.2-init-run/artifacts
```

## Focused Initializer Tests

Command:

```bash
python3 -m unittest tests.test_init_run
```

Observed output:

```text
....
----------------------------------------------------------------------
Ran 4 tests in 0.043s

OK
```

## CLI Help

Command:

```bash
python3 scripts/init_run.py --help
```

Observed output excerpt:

```text
usage: init_run.py [-h] [--root ROOT] [--objective OBJECTIVE] [--force] run_id
```

## Final Verification

Command:

```bash
python3 -m unittest discover
```

Observed output excerpt:

```text
.........
----------------------------------------------------------------------
Ran 9 tests

OK
```

Command:

```bash
python3 scripts/verify_manifest.py runs/ciph-v0.2-init-run/MANIFEST.json --root .
```

Observed output:

```text
CIPH manifest valid: runs/ciph-v0.2-init-run/MANIFEST.json
```

Command:

```bash
python3 scripts/closeout_check.py runs/ciph-v0.2-init-run/MANIFEST.json --root .
```

Observed output excerpt:

```text
- [COVERED] readme-quick-start: Add a README with the exact quick-start flow.
- [COVERED] init-run-command: Add scripts/init_run.py <run-id> to create a run directory.
- [COVERED] init-run-tests: Add tests for init behavior and direct CLI execution.
- [COVERED] dogfood-run: Dogfood the initializer by creating this run.
- COVERED: manifest validation passed.
```
