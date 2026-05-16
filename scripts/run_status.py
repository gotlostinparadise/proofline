#!/usr/bin/env python3
"""Render a concise CIPH run status report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts.lint_manifest import lint_manifest
    from scripts.verify_manifest import load_manifest, path_exists, validate_manifest
except ModuleNotFoundError:  # pragma: no cover - exercised by direct script execution.
    from lint_manifest import lint_manifest
    from verify_manifest import load_manifest, path_exists, validate_manifest


def render_status(manifest_path: Path | str, root: Path | str | None = None) -> str:
    manifest_path = Path(manifest_path)
    root_path = Path(root) if root is not None else manifest_path.parent
    manifest = load_manifest(manifest_path)
    lint_result = lint_manifest(manifest_path, root_path)
    validation_result = validate_manifest(manifest_path, root_path)
    covered_deliverables, total_deliverables = _deliverable_coverage(manifest, root_path)
    passed_checks, total_checks, check_lines = _check_status(manifest, root_path)

    lines = [
        "# CIPH Run Status",
        "",
        f"Task: {manifest.get('task_id', '<missing>')}",
        f"Objective: {manifest.get('objective', '<missing>')}",
        f"Manifest: {manifest_path}",
        f"Root: {root_path}",
        "",
        "## Summary",
        "",
        f"- Lint: {'PASS' if lint_result.ok else 'FAIL'} ({len(lint_result.errors)} errors, {len(lint_result.warnings)} warnings)",
        f"- Manifest: {'PASS' if validation_result.ok else 'FAIL'} ({len(validation_result.errors)} errors)",
        f"- Deliverables: {covered_deliverables}/{total_deliverables} covered",
        f"- Required checks: {passed_checks}/{total_checks} passed",
        "",
        "## Required Checks",
        "",
    ]
    lines.extend(check_lines or ["- None."])

    if lint_result.errors or lint_result.warnings:
        lines.extend(["", "## Lint Issues", ""])
        lines.extend([f"- {issue}" for issue in [*lint_result.errors, *lint_result.warnings]])

    if validation_result.errors:
        lines.extend(["", "## Manifest Issues", ""])
        lines.extend([f"- {issue}" for issue in validation_result.errors])

    return "\n".join(lines) + "\n"


def write_status(manifest_path: Path | str, root: Path | str | None, output_path: Path | str) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_status(manifest_path, root), encoding="utf-8")
    return output


def _deliverable_coverage(manifest: dict[str, Any], root: Path) -> tuple[int, int]:
    deliverables = manifest.get("deliverables", [])
    if not isinstance(deliverables, list):
        return 0, 0

    covered = 0
    total = 0
    for deliverable in deliverables:
        if not isinstance(deliverable, dict):
            continue
        total += 1
        artifact_paths = _string_list(deliverable.get("artifact_paths", []))
        evidence_paths = _string_list(deliverable.get("evidence_paths", []))
        artifacts_ok = artifact_paths and all(path_exists(root, path) for path in artifact_paths)
        evidence_ok = evidence_paths and all(path_exists(root, path) for path in evidence_paths)
        if artifacts_ok and evidence_ok:
            covered += 1
    return covered, total


def _check_status(manifest: dict[str, Any], root: Path) -> tuple[int, int, list[str]]:
    checks = manifest.get("checks", [])
    if not isinstance(checks, list):
        return 0, 0, []

    passed = 0
    total = 0
    lines: list[str] = []
    for check in checks:
        if not isinstance(check, dict) or check.get("required", False) is not True:
            continue
        total += 1
        name = check.get("name", "<unnamed>")
        evidence = check.get("evidence")
        status = _evidence_status(root, evidence)
        if status == "PASS":
            passed += 1
        lines.append(f"- {name}: {status} ({evidence or '<missing evidence>'})")
    return passed, total, lines


def _evidence_status(root: Path, evidence: Any) -> str:
    if not isinstance(evidence, str) or not evidence.strip():
        return "MISSING"
    path = root / evidence
    if not path.is_file():
        return "MISSING"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return "UNREADABLE"
    if len(lines) >= 2 and lines[0] == "CIPH-CHECK-EVIDENCE v1":
        try:
            metadata = json.loads(lines[1])
        except json.JSONDecodeError:
            return "MALFORMED"
        if isinstance(metadata, dict):
            return str(metadata.get("status", "UNKNOWN"))
    return "PRESENT"


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render a concise CIPH run status report.")
    parser.add_argument("manifest", type=Path, help="Path to MANIFEST.json")
    parser.add_argument("--root", type=Path, default=None, help="Path that manifest references are relative to")
    parser.add_argument("--output", type=Path, default=None, help="Write report to this path")
    args = parser.parse_args(argv)

    if args.output is not None:
        path = write_status(args.manifest, args.root, args.output)
        print(f"Wrote CIPH run status: {path}")
    else:
        print(render_status(args.manifest, args.root), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
