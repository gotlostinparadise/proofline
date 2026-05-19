# Repository Guidelines

## Project Structure & Module Organization

This repository contains CIPH, a file-backed harness for complex implementation work. `scripts/` holds Python CLI tools for initialization, manifest linting, checks, reports, and closeout. `tests/` contains `unittest` coverage. `templates/` stores HTML-first Proofline/CIPH templates, with Markdown fallbacks for legacy runs. `runs/` contains run records with `TASK.html` or `TASK.md`, `MANIFEST.json`, and evidence artifacts. `harness/` holds lifecycle guidance, and `skills/proofline/` contains bundled Codex skill assets.

## Build, Test, and Development Commands

- `python3 -m unittest discover`: run the full unit test suite.
- `python3 scripts/check_repo.py`: run tests, manifest linting, validation, closeout coverage, and `git diff --check`.
- `python3 scripts/init_run.py <run-id> --objective "..."`: create a new run under `runs/<run-id>/`.
- `python3 scripts/lint_manifest.py runs/<run-id>/MANIFEST.json --root .`: catch placeholders, weak evidence links, and manifest contract issues.
- `python3 scripts/run_checks.py runs/<run-id>/MANIFEST.json --root .`: execute manifest checks and write evidence.
- `python3 scripts/verify_manifest.py runs/<run-id>/MANIFEST.json --root .`: validate required paths.
- `python3 scripts/closeout_check.py runs/<run-id>/MANIFEST.json --root .`: render closeout coverage.

## Coding Style & Naming Conventions

Use Python 3 standard-library patterns already present in `scripts/`: `argparse` CLIs, `dataclass` results, `pathlib.Path`, explicit return codes, and UTF-8 file I/O. Use 4-space indentation, `snake_case` for functions and files, `PascalCase` for classes, and descriptive CLI options. Keep run IDs to letters, numbers, dots, underscores, and hyphens.

## Testing Guidelines

Tests use `unittest` and live in `tests/test_*.py`. Add focused tests beside changed behavior, including direct function tests and script execution tests for CLI changes. For manifest or report changes, verify both valid output and failure conditions. Run `python3 -m unittest discover` during development and `python3 scripts/check_repo.py` before closeout.

## Commit & Pull Request Guidelines

Recent history uses short conventional-style subjects such as `feat: make Proofline artifacts HTML-first` and `fix: refresh CIPH repo gate evidence`. Keep commits scoped to one behavior or documentation update. Pull requests should include the objective, changed paths, verification commands, and generated evidence or report paths. Include screenshots only for rendered HTML or user-visible page changes.

## Agent-Specific Instructions

The repository is the durable source of truth. Record meaningful task state in `TASK.html`, `MANIFEST.json`, plans, evidence files, and closeout output rather than relying on chat. When work depends on volatile facts such as APIs, config keys, CLI flags, schemas, or pricing, consult the most authoritative available MCP or documentation source before writing code or setup steps. Never print secrets or environment values.
