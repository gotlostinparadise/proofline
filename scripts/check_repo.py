#!/usr/bin/env python3
"""Run the CIPH repository health gate."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    from scripts.closeout_check import render_closeout
    from scripts.lint_manifest import lint_manifest
    from scripts.verify_manifest import validate_manifest
except ModuleNotFoundError:  # pragma: no cover - exercised by direct script execution.
    from closeout_check import render_closeout
    from lint_manifest import lint_manifest
    from verify_manifest import validate_manifest


@dataclass
class RepoGateResult:
    messages: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures


def check_repo(
    root: Path | str = ".",
    include_diff_check: bool = True,
    runs_dir: Path | str = "runs",
) -> RepoGateResult:
    root_path = Path(root)
    runs_path = root_path / runs_dir
    result = RepoGateResult()

    _run_tests(root_path, result)
    manifests = sorted(runs_path.glob("*/MANIFEST.json"))
    if not manifests:
        result.failures.append(f"FAIL manifests none found under {Path(runs_dir).as_posix()}/*/MANIFEST.json")

    for manifest_path in manifests:
        rel_manifest = _relative(manifest_path, root_path)
        lint_result = lint_manifest(manifest_path, root_path)
        if lint_result.ok:
            result.messages.append(f"PASS lint {rel_manifest}")
        else:
            result.failures.append(f"FAIL lint {rel_manifest}")
            result.failures.extend(lint_result.errors)

        validation_result = validate_manifest(manifest_path, root_path)
        if validation_result.ok:
            result.messages.append(f"PASS verify {rel_manifest}")
        else:
            result.failures.append(f"FAIL verify {rel_manifest}")
            result.failures.extend(validation_result.errors)

        closeout = render_closeout(manifest_path, root_path)
        if "[MISSING]" in closeout or "MISSING:" in closeout:
            result.failures.append(f"FAIL closeout {rel_manifest} has missing coverage")
        else:
            result.messages.append(f"PASS closeout {rel_manifest}")

    if include_diff_check:
        _run_diff_check(root_path, result)

    return result


def _run_tests(root: Path, result: RepoGateResult) -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "unittest", "discover"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode == 0:
        result.messages.append("PASS tests")
    else:
        result.failures.append("FAIL tests")
        output = "\n".join(part for part in [completed.stdout, completed.stderr] if part)
        if output:
            result.failures.append(output.strip())


def _run_diff_check(root: Path, result: RepoGateResult) -> None:
    completed = subprocess.run(
        ["git", "diff", "--check"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode == 0:
        result.messages.append("PASS git diff --check")
    else:
        result.failures.append("FAIL git diff --check")
        output = "\n".join(part for part in [completed.stdout, completed.stderr] if part)
        if output:
            result.failures.append(output.strip())


def _relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the CIPH repository health gate.")
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root")
    parser.add_argument("--runs-dir", type=Path, default=Path("runs"), help="Runs directory relative to --root")
    parser.add_argument("--skip-diff-check", action="store_true", help="Skip git diff --check")
    args = parser.parse_args(argv)

    result = check_repo(args.root, include_diff_check=not args.skip_diff_check, runs_dir=args.runs_dir)
    for message in result.messages:
        print(message)
    for failure in result.failures:
        print(failure, file=sys.stderr)

    if result.ok:
        print("CIPH repo gate passed")
        return 0

    print("CIPH repo gate failed", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
