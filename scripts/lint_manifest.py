#!/usr/bin/env python3
"""Lint CIPH manifests for weak or placeholder-filled contracts."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from scripts.verify_manifest import load_manifest
except ModuleNotFoundError:  # pragma: no cover - exercised by direct script execution.
    from verify_manifest import load_manifest


PLACEHOLDER_SUBSTRINGS = [
    "Replace this",
    "path/to/artifact",
    "replace with exact command",
]
PLACEHOLDER_EXACT = {"<run-id>", "<original objective>"}


@dataclass
class LintResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def lint_manifest(manifest_path: Path | str, root: Path | str | None = None) -> LintResult:
    manifest_path = Path(manifest_path)
    root_path = Path(root) if root is not None else manifest_path.parent
    result = LintResult()

    try:
        manifest = load_manifest(manifest_path)
    except ValueError as exc:
        result.errors.append(f"ERROR {exc}")
        return result

    task_id = manifest.get("task_id")
    _lint_placeholders(manifest, result)
    _lint_deliverables(manifest.get("deliverables", []), result)
    _lint_checks(manifest.get("checks", []), task_id, manifest_path, root_path, result)

    return result


def _lint_placeholders(value: Any, result: LintResult, path: str = "") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            _lint_placeholders(item, result, child_path)
        return

    if isinstance(value, list):
        for index, item in enumerate(value, start=1):
            _lint_placeholders(item, result, f"{path}[{index}]")
        return

    if not isinstance(value, str):
        return

    if path.endswith(".id") and value == "example":
        result.errors.append(f"ERROR {path} contains placeholder text: {value}")
        return

    if value in PLACEHOLDER_EXACT or "runs/<run-id>" in value:
        result.errors.append(f"ERROR {path} contains placeholder text: {value}")
        return

    for placeholder in PLACEHOLDER_SUBSTRINGS:
        if placeholder in value:
            result.errors.append(f"ERROR {path} contains placeholder text: {value}")
            return


def _lint_deliverables(deliverables: Any, result: LintResult) -> None:
    if not isinstance(deliverables, list):
        return

    for index, deliverable in enumerate(deliverables, start=1):
        if not isinstance(deliverable, dict):
            continue

        deliverable_id = deliverable.get("id") if isinstance(deliverable.get("id"), str) else f"deliverables[{index}]"
        artifact_paths = deliverable.get("artifact_paths", [])
        evidence_paths = deliverable.get("evidence_paths", [])

        if not isinstance(artifact_paths, list) or not artifact_paths:
            result.errors.append(f"ERROR deliverable {deliverable_id} must list at least one artifact path")
        elif _has_duplicate_strings(artifact_paths):
            for duplicate in _duplicate_strings(artifact_paths):
                result.warnings.append(f"WARN deliverable {deliverable_id} repeats artifact path: {duplicate}")

        if not isinstance(evidence_paths, list) or not evidence_paths:
            result.errors.append(f"ERROR deliverable {deliverable_id} must list at least one evidence path")
        elif _has_duplicate_strings(evidence_paths):
            for duplicate in _duplicate_strings(evidence_paths):
                result.warnings.append(f"WARN deliverable {deliverable_id} repeats evidence path: {duplicate}")


def _lint_checks(checks: Any, task_id: Any, manifest_path: Path, root: Path, result: LintResult) -> None:
    if not isinstance(checks, list) or not isinstance(task_id, str) or not task_id:
        return

    expected_prefix = _expected_check_evidence_prefix(manifest_path, root, task_id)
    evidence_paths: set[str] = set()
    for index, check in enumerate(checks, start=1):
        if not isinstance(check, dict):
            continue
        name = check.get("name") if isinstance(check.get("name"), str) else f"checks[{index}]"
        if check.get("required", False) is not True:
            continue

        evidence = check.get("evidence")
        if not isinstance(evidence, str) or not evidence.strip():
            result.errors.append(f"ERROR required check {name} must include evidence")
            continue

        if not evidence.startswith(expected_prefix):
            result.errors.append(f"ERROR required check {name} evidence must be under {expected_prefix}")

        if evidence in evidence_paths:
            result.warnings.append(f"WARN repeated required check evidence path: {evidence}")
        evidence_paths.add(evidence)

        if check.get("evidence_producer") != "run_checks":
            result.warnings.append(f"WARN required check {name} should use evidence_producer: run_checks")


def _expected_check_evidence_prefix(manifest_path: Path, root: Path, task_id: str) -> str:
    expected_dir = manifest_path.parent / "artifacts" / "checks"
    try:
        relative = expected_dir.relative_to(root)
    except ValueError:
        relative = Path("runs") / task_id / "artifacts" / "checks"
    return f"{relative.as_posix().rstrip('/')}/"


def _has_duplicate_strings(values: list[Any]) -> bool:
    return bool(_duplicate_strings(values))


def _duplicate_strings(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    return duplicates


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lint a CIPH manifest for weak contracts.")
    parser.add_argument("manifest", type=Path, help="Path to MANIFEST.json")
    parser.add_argument("--root", type=Path, default=None, help="Path that manifest references are relative to")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    args = parser.parse_args(argv)

    result = lint_manifest(args.manifest, args.root)
    for error in result.errors:
        print(error, file=sys.stderr)
    for warning in result.warnings:
        print(warning)

    if result.errors or (args.strict and result.warnings):
        print(f"CIPH manifest lint failed: {args.manifest}", file=sys.stderr)
        return 1

    print(f"CIPH manifest lint clean: {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
