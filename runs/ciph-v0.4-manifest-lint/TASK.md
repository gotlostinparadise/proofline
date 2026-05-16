# CIPH Task

## Objective

Add manifest linting to catch placeholders, weak evidence, and required-check evidence path issues.

## Acceptance Object

The work is acceptable when `scripts/lint_manifest.py` catches placeholder text, missing deliverable links, weak required-check evidence, and bad required-check evidence paths; existing manifests are migrated to lint cleanly; and this dogfood run closes with runner-produced evidence.

## Constraints

- Repository rules: keep linting stdlib-only and separate from structural manifest verification.
- Files or areas in scope: lint script, lint tests, README, harness docs, templates, existing run manifests, and this run directory.
- Files or areas out of scope: external services, schema migrations beyond current manifest JSON, and custom runtime behavior.
- Permissions: local file and shell command execution only.
- Secrets handling: no secrets are required.

## Volatile Facts To Verify

No external API, pricing, product-limit, or schema fact is required. The feature depends on local repository files and Python standard-library behavior.

## Deliverables

| ID | Requirement | Artifact paths | Evidence paths |
| --- | --- | --- | --- |
| lint-command | Add `scripts/lint_manifest.py` for manifest quality checks. | `scripts/lint_manifest.py` | `runs/ciph-v0.4-manifest-lint/artifacts/checks/focused-lint-tests.txt` |
| lint-tests | Add tests for placeholders, missing links, weak checks, bad evidence paths, duplicates, and direct CLI execution. | `tests/test_lint_manifest.py` | `runs/ciph-v0.4-manifest-lint/artifacts/checks/focused-lint-tests.txt` |
| migrated-manifests | Migrate existing manifests so lint and verify both pass. | `runs/example-harness-design/MANIFEST.json`, `runs/ciph-v0.2-init-run/MANIFEST.json`, `runs/ciph-v0.3-run-checks/MANIFEST.json` | `runs/ciph-v0.4-manifest-lint/artifacts/checks/lint-all-manifests.txt` |
| docs-flow | Add linting to README, CIPH, and task template flow. | `README.md`, `harness/CIPH.md`, `templates/TASK.md` | `runs/ciph-v0.4-manifest-lint/artifacts/checks/full-unit-tests.txt` |
| dogfood-run | Dogfood v0.4 with this generated run and runner evidence. | `runs/ciph-v0.4-manifest-lint/TASK.md`, `runs/ciph-v0.4-manifest-lint/MANIFEST.json` | `runs/ciph-v0.4-manifest-lint/artifacts/checks/lint-help.txt` |

## Risks And Blockers

- None yet.

## Closeout Commands

```bash
python3 scripts/lint_manifest.py runs/ciph-v0.4-manifest-lint/MANIFEST.json --root .
python3 scripts/run_checks.py runs/ciph-v0.4-manifest-lint/MANIFEST.json --root .
python3 scripts/verify_manifest.py runs/ciph-v0.4-manifest-lint/MANIFEST.json --root .
python3 scripts/closeout_check.py runs/ciph-v0.4-manifest-lint/MANIFEST.json --root .
```
