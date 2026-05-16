#!/usr/bin/env python3
"""Validate a CIPH run manifest and its local evidence paths."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "ciph.manifest.v1"
RUN_CHECKS_EVIDENCE_MARKER = "CIPH-CHECK-EVIDENCE v1"
RUN_CHECKS_GENERATED_BY = "scripts/run_checks.py"


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def messages(self) -> list[str]:
        return [*self.errors, *self.warnings]


def load_manifest(manifest_path: Path) -> dict[str, Any]:
    try:
        with manifest_path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {manifest_path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"Manifest must be a JSON object: {manifest_path}")

    return payload


def validate_manifest(manifest_path: Path | str, root: Path | str | None = None) -> ValidationResult:
    manifest_path = Path(manifest_path)
    root_path = Path(root) if root is not None else manifest_path.parent
    result = ValidationResult()

    try:
        manifest = load_manifest(manifest_path)
    except ValueError as exc:
        result.errors.append(str(exc))
        return result

    _validate_required_top_level(manifest, result)
    _validate_deliverables(manifest, root_path, result)
    _validate_artifacts(manifest, root_path, result)
    _validate_checks(manifest, root_path, result)

    return result


def path_exists(root: Path, reference: str) -> bool:
    if _is_external_reference(reference):
        return True

    return (root / reference).exists()


def _validate_required_top_level(manifest: dict[str, Any], result: ValidationResult) -> None:
    required_fields = ["schema_version", "task_id", "objective", "deliverables", "artifacts", "checks"]
    for field_name in required_fields:
        if field_name not in manifest:
            result.errors.append(f"Missing required field: {field_name}")

    if manifest.get("schema_version") != SCHEMA_VERSION:
        result.errors.append(f"schema_version must be {SCHEMA_VERSION}")

    for field_name in ["task_id", "objective"]:
        if field_name in manifest and not _non_empty_string(manifest[field_name]):
            result.errors.append(f"{field_name} must be a non-empty string")

    for field_name in ["deliverables", "artifacts", "checks"]:
        if field_name in manifest and not isinstance(manifest[field_name], list):
            result.errors.append(f"{field_name} must be a list")


def _validate_deliverables(manifest: dict[str, Any], root: Path, result: ValidationResult) -> None:
    deliverables = manifest.get("deliverables", [])
    if not isinstance(deliverables, list):
        return

    if not deliverables:
        result.errors.append("Manifest must list at least one deliverable")
        return

    for index, deliverable in enumerate(deliverables, start=1):
        if not isinstance(deliverable, dict):
            result.errors.append(f"deliverables[{index}] must be an object")
            continue

        deliverable_id = deliverable.get("id", f"deliverable[{index}]")
        if not _non_empty_string(deliverable.get("id")):
            result.errors.append(f"deliverables[{index}].id must be a non-empty string")
        if not _non_empty_string(deliverable.get("requirement")):
            result.errors.append(f"deliverables[{index}].requirement must be a non-empty string")

        artifact_paths = deliverable.get("artifact_paths", [])
        evidence_paths = deliverable.get("evidence_paths", [])
        if not _list_of_strings(artifact_paths):
            result.errors.append(f"deliverable {deliverable_id} artifact_paths must be a list of strings")
        if not _list_of_strings(evidence_paths):
            result.errors.append(f"deliverable {deliverable_id} evidence_paths must be a list of strings")

        for path in artifact_paths if isinstance(artifact_paths, list) else []:
            if isinstance(path, str) and not path_exists(root, path):
                result.errors.append(f"Missing deliverable artifact for {deliverable_id}: {path}")

        for path in evidence_paths if isinstance(evidence_paths, list) else []:
            if isinstance(path, str) and not path_exists(root, path):
                result.errors.append(f"Missing deliverable evidence for {deliverable_id}: {path}")


def _validate_artifacts(manifest: dict[str, Any], root: Path, result: ValidationResult) -> None:
    artifacts = manifest.get("artifacts", [])
    if not isinstance(artifacts, list):
        return

    for index, artifact in enumerate(artifacts, start=1):
        if not isinstance(artifact, dict):
            result.errors.append(f"artifacts[{index}] must be an object")
            continue

        path = artifact.get("path")
        if not _non_empty_string(path):
            result.errors.append(f"artifacts[{index}].path must be a non-empty string")
            continue

        if artifact.get("required", False) is True and not path_exists(root, path):
            result.errors.append(f"Missing required artifact: {path}")


def _validate_checks(manifest: dict[str, Any], root: Path, result: ValidationResult) -> None:
    checks = manifest.get("checks", [])
    if not isinstance(checks, list):
        return

    for index, check in enumerate(checks, start=1):
        if not isinstance(check, dict):
            result.errors.append(f"checks[{index}] must be an object")
            continue

        name = check.get("name")
        if not _non_empty_string(name):
            result.errors.append(f"checks[{index}].name must be a non-empty string")
            name = f"checks[{index}]"

        if check.get("required", False) is True:
            if not _non_empty_string(check.get("command")):
                result.errors.append(f"Required check {name} must include a command")

            evidence = check.get("evidence")
            if not _non_empty_string(evidence):
                result.errors.append(f"Required check {name} must include evidence")
            elif not path_exists(root, evidence):
                result.errors.append(f"Missing required check evidence for {name}: {evidence}")
            elif check.get("evidence_producer") == "run_checks":
                _validate_run_checks_evidence(root / evidence, evidence, name, check.get("command"), result)


def _is_external_reference(reference: str) -> bool:
    return reference.startswith(("http://", "https://", "source:"))


def _validate_run_checks_evidence(
    evidence_path: Path,
    evidence_reference: str,
    check_name: str,
    command: Any,
    result: ValidationResult,
) -> None:
    try:
        lines = evidence_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        result.errors.append(f"Unable to read run_checks evidence for {check_name}: {evidence_reference}: {exc}")
        return

    if len(lines) < 2 or lines[0] != RUN_CHECKS_EVIDENCE_MARKER:
        result.errors.append(f"Malformed run_checks evidence for {check_name}: {evidence_reference}")
        return

    try:
        metadata = json.loads(lines[1])
    except json.JSONDecodeError:
        result.errors.append(f"Malformed run_checks metadata for {check_name}: {evidence_reference}")
        return

    if not isinstance(metadata, dict):
        result.errors.append(f"Malformed run_checks metadata for {check_name}: {evidence_reference}")
        return

    if metadata.get("generated_by") != RUN_CHECKS_GENERATED_BY:
        result.errors.append(f"run_checks evidence for {check_name} has wrong generator: {evidence_reference}")
    if metadata.get("check_name") != check_name:
        result.errors.append(f"run_checks evidence for {check_name} has wrong check name: {evidence_reference}")
    if metadata.get("command") != command:
        result.errors.append(f"run_checks evidence for {check_name} does not match manifest command: {evidence_reference}")
    if metadata.get("exit_code") != 0 or metadata.get("status") != "PASS":
        result.errors.append(f"run_checks evidence for {check_name} did not pass: {evidence_reference}")


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _list_of_strings(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a CIPH run manifest.")
    parser.add_argument("manifest", type=Path, help="Path to MANIFEST.json")
    parser.add_argument("--root", type=Path, default=None, help="Path that manifest references are relative to")
    args = parser.parse_args(argv)

    result = validate_manifest(args.manifest, args.root)
    if result.ok:
        print(f"CIPH manifest valid: {args.manifest}")
        return 0

    print(f"CIPH manifest invalid: {args.manifest}", file=sys.stderr)
    for error in result.errors:
        print(f"ERROR: {error}", file=sys.stderr)
    for warning in result.warnings:
        print(f"WARN: {warning}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
