#!/usr/bin/env python3
"""Render a CIPH prompt-to-artifact closeout checklist."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

try:
    from scripts.verify_manifest import load_manifest, path_exists, validate_manifest
except ModuleNotFoundError:  # pragma: no cover - exercised by direct script execution.
    from verify_manifest import load_manifest, path_exists, validate_manifest


def render_closeout(manifest_path: Path | str, root: Path | str | None = None) -> str:
    manifest_path = Path(manifest_path)
    root_path = Path(root) if root is not None else manifest_path.parent
    manifest = load_manifest(manifest_path)
    validation = validate_manifest(manifest_path, root_path)

    lines: list[str] = [
        "# CIPH Closeout Checklist",
        "",
        f"Task: {manifest.get('task_id', '<missing>')}",
        f"Objective: {manifest.get('objective', '<missing>')}",
        f"Manifest: {manifest_path}",
        f"Root: {root_path}",
        "",
        "## Prompt-to-Artifact Checklist",
        "",
    ]

    for deliverable in manifest.get("deliverables", []):
        if not isinstance(deliverable, dict):
            continue
        lines.extend(_render_deliverable(deliverable, root_path))

    lines.extend(
        [
            "## Required Checks",
            "",
        ]
    )
    for check in manifest.get("checks", []):
        if not isinstance(check, dict):
            continue
        name = check.get("name", "<unnamed>")
        evidence = check.get("evidence", "")
        status = "COVERED" if evidence and path_exists(root_path, evidence) else "MISSING"
        lines.append(f"- [{status}] {name}")
        lines.append(f"  - Command: {check.get('command', '<missing>')}")
        lines.append(f"  - Evidence: {evidence or '<missing>'}")

    lines.extend(
        [
            "",
            "## Risks",
            "",
        ]
    )
    risks = manifest.get("risks", [])
    if risks:
        for risk in risks:
            lines.append(f"- {risk}")
    else:
        lines.append("- None recorded.")

    lines.extend(
        [
            "",
            "## Manifest Validation",
            "",
        ]
    )
    if validation.ok:
        lines.append("- COVERED: manifest validation passed.")
    else:
        for error in validation.errors:
            lines.append(f"- MISSING: {error}")

    return "\n".join(lines) + "\n"


def _render_deliverable(deliverable: dict[str, Any], root: Path) -> list[str]:
    deliverable_id = deliverable.get("id", "<missing>")
    requirement = deliverable.get("requirement", "<missing>")
    artifact_paths = _string_list(deliverable.get("artifact_paths", []))
    evidence_paths = _string_list(deliverable.get("evidence_paths", []))
    artifact_status = all(path_exists(root, path) for path in artifact_paths) if artifact_paths else False
    evidence_status = all(path_exists(root, path) for path in evidence_paths) if evidence_paths else False
    status = "COVERED" if artifact_status and evidence_status else "MISSING"

    lines = [
        f"- [{status}] {deliverable_id}: {requirement}",
        f"  - Artifacts: {', '.join(artifact_paths) if artifact_paths else '<missing>'}",
        f"  - Evidence: {', '.join(evidence_paths) if evidence_paths else '<missing>'}",
    ]
    return lines


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render a CIPH closeout checklist.")
    parser.add_argument("manifest", type=Path, help="Path to MANIFEST.json")
    parser.add_argument("--root", type=Path, default=None, help="Path that manifest references are relative to")
    parser.add_argument("--output", type=Path, default=None, help="Write checklist to this path")
    args = parser.parse_args(argv)

    output = render_closeout(args.manifest, args.root)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
        print(f"Wrote CIPH closeout checklist: {args.output}")
    else:
        print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
