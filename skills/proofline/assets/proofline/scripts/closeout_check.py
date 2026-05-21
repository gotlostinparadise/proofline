#!/usr/bin/env python3
"""Render a CIPH prompt-to-artifact closeout checklist."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

try:
    from scripts.html_report import render_html_document
    from scripts.verify_manifest import load_manifest, path_exists, validate_manifest
except ModuleNotFoundError:  # pragma: no cover - exercised by direct script execution.
    from html_report import render_html_document
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
        status = _check_status(check, root_path)
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


def render_closeout_html(manifest_path: Path | str, root: Path | str | None = None) -> str:
    manifest_path = Path(manifest_path)
    root_path = Path(root) if root is not None else manifest_path.parent
    manifest = load_manifest(manifest_path)
    validation = validate_manifest(manifest_path, root_path)

    deliverable_items: list[str] = []
    for deliverable in manifest.get("deliverables", []):
        if not isinstance(deliverable, dict):
            continue
        deliverable_items.append(_deliverable_summary(deliverable, root_path))

    check_items: list[str] = []
    for check in manifest.get("checks", []):
        if not isinstance(check, dict):
            continue
        name = check.get("name", "<unnamed>")
        evidence = check.get("evidence", "")
        status = _check_status(check, root_path)
        check_items.append(f"[{status}] {name} - Command: {check.get('command', '<missing>')} - Evidence: {evidence or '<missing>'}")

    risks = manifest.get("risks", [])
    risk_items = [str(risk) for risk in risks] if risks else ["None recorded."]
    validation_items = ["COVERED: manifest validation passed."] if validation.ok else [f"MISSING: {error}" for error in validation.errors]

    return render_html_document(
        title="CIPH Closeout Checklist",
        heading="CIPH Closeout Checklist",
        report_kind="closeout",
        summary_items=[
            ("Task", str(manifest.get("task_id", "<missing>"))),
            ("Objective", str(manifest.get("objective", "<missing>"))),
            ("Manifest", str(manifest_path)),
            ("Root", str(root_path)),
        ],
        sections=[
            {
                "id": "prompt-to-artifact",
                "title": "Prompt-to-Artifact Checklist",
                "items": deliverable_items,
            },
            {
                "id": "required-checks",
                "title": "Required Checks",
                "items": check_items,
            },
            {
                "id": "risks",
                "title": "Risks",
                "items": risk_items,
            },
            {
                "id": "manifest-validation",
                "title": "Manifest Validation",
                "items": validation_items,
            },
        ],
    )


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


def _deliverable_summary(deliverable: dict[str, Any], root: Path) -> str:
    deliverable_id = deliverable.get("id", "<missing>")
    requirement = deliverable.get("requirement", "<missing>")
    artifact_paths = _string_list(deliverable.get("artifact_paths", []))
    evidence_paths = _string_list(deliverable.get("evidence_paths", []))
    artifact_status = all(path_exists(root, path) for path in artifact_paths) if artifact_paths else False
    evidence_status = all(path_exists(root, path) for path in evidence_paths) if evidence_paths else False
    status = "COVERED" if artifact_status and evidence_status else "MISSING"
    artifacts = ", ".join(artifact_paths) if artifact_paths else "<missing>"
    evidence = ", ".join(evidence_paths) if evidence_paths else "<missing>"
    return f"[{status}] {deliverable_id}: {requirement} - Artifacts: {artifacts} - Evidence: {evidence}"


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _check_status(check: dict[str, Any], root: Path) -> str:
    required = check.get("required", False) is True
    evidence = check.get("evidence", "")
    has_evidence = isinstance(evidence, str) and evidence and path_exists(root, evidence)
    if has_evidence:
        return "COVERED"
    if required:
        return "MISSING"
    return "OPTIONAL"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render a CIPH closeout checklist.")
    parser.add_argument("manifest", type=Path, help="Path to MANIFEST.json")
    parser.add_argument("--root", type=Path, default=None, help="Path that manifest references are relative to")
    parser.add_argument("--output", type=Path, default=None, help="Write checklist to this path")
    args = parser.parse_args(argv)

    output = render_closeout_html(args.manifest, args.root) if args.output is not None and args.output.suffix == ".html" else render_closeout(args.manifest, args.root)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
        print(f"Wrote CIPH closeout checklist: {args.output}")
    else:
        print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
