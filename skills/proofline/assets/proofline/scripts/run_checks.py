#!/usr/bin/env python3
"""Run manifest checks and write structured CIPH evidence."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.verify_manifest import load_manifest
except ModuleNotFoundError:  # pragma: no cover - exercised by direct script execution.
    from verify_manifest import load_manifest


EVIDENCE_MARKER = "CIPH-CHECK-EVIDENCE v1"
GENERATED_BY = "scripts/run_checks.py"


@dataclass(frozen=True)
class CheckRun:
    name: str
    command: str
    evidence_path: Path
    required: bool
    exit_code: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


@dataclass(frozen=True)
class RunChecksResult:
    checks: list[CheckRun]
    errors: list[str]

    @property
    def ok(self) -> bool:
        required_failures = [check for check in self.checks if check.required and not check.ok]
        return not self.errors and not required_failures


def run_checks(
    manifest_path: Path | str,
    root: Path | str | None = None,
    include_optional: bool = False,
) -> RunChecksResult:
    manifest_path = Path(manifest_path)
    root_path = Path(root) if root is not None else manifest_path.parent
    manifest = load_manifest(manifest_path)
    errors: list[str] = []
    check_runs: list[CheckRun] = []
    evidence_paths: set[str] = set()

    checks = manifest.get("checks", [])
    if not isinstance(checks, list):
        return RunChecksResult([], ["checks must be a list"])

    for index, check in enumerate(checks, start=1):
        if not isinstance(check, dict):
            errors.append(f"checks[{index}] must be an object")
            continue
        if not include_optional and check.get("required", False) is not True:
            continue

        prepared = _prepare_check(check, index, manifest, evidence_paths)
        if isinstance(prepared, str):
            errors.append(prepared)
            continue

        name, command, evidence_reference, required = prepared
        evidence_path = root_path / evidence_reference
        started_at = _utc_now()
        completed = subprocess.run(
            command,
            cwd=root_path,
            shell=True,
            text=True,
            capture_output=True,
            check=False,
        )
        finished_at = _utc_now()
        check_run = CheckRun(
            name=name,
            command=command,
            evidence_path=evidence_path,
            required=required,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
        _write_evidence(check_run, started_at, finished_at)
        check_runs.append(check_run)

    return RunChecksResult(check_runs, errors)


def _prepare_check(
    check: dict[str, Any],
    index: int,
    manifest: dict[str, Any],
    evidence_paths: set[str],
) -> tuple[str, str, str, bool] | str:
    name = check.get("name")
    command = check.get("command")
    evidence = check.get("evidence")
    required = check.get("required", False) is True

    if not isinstance(name, str) or not name.strip():
        return f"checks[{index}].name must be a non-empty string"
    if not isinstance(command, str) or not command.strip():
        return f"Required check {name} must include a command"
    if not isinstance(evidence, str) or not evidence.strip():
        task_id = manifest.get("task_id", "run")
        evidence = f"runs/{task_id}/artifacts/checks/{_slugify(name)}.txt"

    if evidence in evidence_paths:
        return f"Duplicate check evidence path: {evidence}"
    evidence_paths.add(evidence)

    return name, command, evidence, required


def _write_evidence(check_run: CheckRun, started_at: str, finished_at: str) -> None:
    check_run.evidence_path.parent.mkdir(parents=True, exist_ok=True)
    stdout = check_run.stdout.rstrip() or "<empty>"
    stderr = check_run.stderr.rstrip() or "<empty>"
    metadata = {
        "check_name": check_run.name,
        "command": check_run.command,
        "exit_code": check_run.exit_code,
        "status": "PASS" if check_run.ok else "FAIL",
        "generated_by": GENERATED_BY,
        "started_at_utc": started_at,
        "finished_at_utc": finished_at,
    }
    body = [
        EVIDENCE_MARKER,
        json.dumps(metadata, sort_keys=True),
        "",
        "## STDOUT",
        "",
        stdout,
        "",
        "## STDERR",
        "",
        stderr,
    ]
    check_run.evidence_path.write_text("\n".join(body), encoding="utf-8")


def _slugify(value: str) -> str:
    result = []
    previous_dash = False
    for char in value.lower():
        if char.isalnum():
            result.append(char)
            previous_dash = False
        elif not previous_dash:
            result.append("-")
            previous_dash = True
    return "".join(result).strip("-") or "check"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run CIPH manifest checks and write structured evidence.")
    parser.add_argument("manifest", type=Path, help="Path to MANIFEST.json")
    parser.add_argument("--root", type=Path, default=None, help="Path that manifest references are relative to")
    parser.add_argument("--include-optional", action="store_true", help="Run optional checks too")
    args = parser.parse_args(argv)

    result = run_checks(args.manifest, args.root, include_optional=args.include_optional)
    for error in result.errors:
        print(f"ERROR {error}", file=sys.stderr)
    for check in result.checks:
        status = "PASS" if check.ok else "FAIL"
        print(f"{status} {check.name} -> {check.evidence_path}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
