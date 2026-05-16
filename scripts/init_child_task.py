#!/usr/bin/env python3
"""Create a bounded child-task packet for delegated CIPH work."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from scripts.verify_manifest import load_manifest
except ModuleNotFoundError:  # pragma: no cover - exercised by direct script execution.
    from verify_manifest import load_manifest


CHILD_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


@dataclass(frozen=True)
class ChildTaskResult:
    parent_task_id: str
    child_id: str
    child_dir: Path
    task_path: Path
    response_path: Path
    ownership_path: Path


def initialize_child_task(
    manifest_path: Path | str,
    child_id: str,
    root: Path | str = ".",
    title: str | None = None,
    owner: str | None = None,
    write_scopes: list[str] | None = None,
    force: bool = False,
) -> ChildTaskResult:
    validate_child_id(child_id)
    root_path = Path(root)
    manifest_path = Path(manifest_path)
    manifest = load_manifest(manifest_path)
    parent_task_id = manifest.get("task_id")
    if not isinstance(parent_task_id, str) or not parent_task_id.strip():
        raise ValueError("Parent manifest must include a non-empty task_id")

    child_dir = root_path / "runs" / parent_task_id / "children" / child_id
    if child_dir.exists() and not force:
        raise FileExistsError(f"Child task already exists: runs/{parent_task_id}/children/{child_id}")

    title_text = title.strip() if title and title.strip() else f"Child task {child_id}"
    owner_text = owner.strip() if owner and owner.strip() else "unassigned"
    scopes = write_scopes or []

    (child_dir / "inputs").mkdir(parents=True, exist_ok=True)
    (child_dir / "scratch").mkdir(parents=True, exist_ok=True)
    (child_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    (child_dir / "artifacts" / ".gitkeep").touch()

    task_path = child_dir / "TASK.md"
    response_path = child_dir / "RESPONSE.md"
    ownership_path = child_dir / "OWNERSHIP.json"

    task_path.write_text(
        _render_task(parent_task_id, child_id, title_text, owner_text, scopes, manifest),
        encoding="utf-8",
    )
    response_path.write_text(_render_response(child_id), encoding="utf-8")
    ownership_path.write_text(
        json.dumps(
            {
                "parent_task_id": parent_task_id,
                "child_id": child_id,
                "owner": owner_text,
                "write_scopes": scopes,
                "task_path": f"runs/{parent_task_id}/children/{child_id}/TASK.md",
                "response_path": f"runs/{parent_task_id}/children/{child_id}/RESPONSE.md",
                "artifacts_dir": f"runs/{parent_task_id}/children/{child_id}/artifacts",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return ChildTaskResult(parent_task_id, child_id, child_dir, task_path, response_path, ownership_path)


def validate_child_id(child_id: str) -> None:
    if not CHILD_ID_PATTERN.match(child_id):
        raise ValueError(
            "Child id must start with an alphanumeric character and contain only letters, "
            "numbers, dots, underscores, or hyphens."
        )


def _render_task(
    parent_task_id: str,
    child_id: str,
    title: str,
    owner: str,
    write_scopes: list[str],
    manifest: dict[str, Any],
) -> str:
    scope_lines = "\n".join(f"- `{scope}`" for scope in write_scopes) if write_scopes else "- No write scopes assigned yet."
    return f"""# CIPH Child Task: {child_id}

## Title

{title}

## Parent

- Parent task: `{parent_task_id}`
- Parent objective: {manifest.get("objective", "<missing>")}
- Owner: `{owner}`

## Write Scope

{scope_lines}

## Instructions

You are not alone in this codebase. Do not revert edits made by others. Keep changes inside the write scope unless the parent task explicitly expands it.

Use `scratch/` for temporary notes, `artifacts/` for deliverables, and `RESPONSE.md` for the final handoff.

## Completion Evidence

Record changed paths, commands run, outputs produced, and unresolved blockers in `RESPONSE.md`.
"""


def _render_response(child_id: str) -> str:
    return f"""# CIPH Child Response: {child_id}

## Summary

State what changed.

## Changed Paths

- None yet.

## Verification

- Not run yet.

## Artifacts

- None yet.

## Blockers

- None.
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a bounded CIPH child-task packet.")
    parser.add_argument("manifest", type=Path, help="Path to parent MANIFEST.json")
    parser.add_argument("child_id", help="Child id using letters, numbers, dots, underscores, or hyphens")
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root")
    parser.add_argument("--title", default=None, help="Child task title")
    parser.add_argument("--owner", default=None, help="Assigned child owner or role")
    parser.add_argument("--write-scope", action="append", default=[], help="Allowed write path; repeatable")
    parser.add_argument("--force", action="store_true", help="Overwrite generated child packet files")
    args = parser.parse_args(argv)

    try:
        result = initialize_child_task(
            args.manifest,
            args.child_id,
            root=args.root,
            title=args.title,
            owner=args.owner,
            write_scopes=args.write_scope,
            force=args.force,
        )
    except (FileExistsError, ValueError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}")
        return 1

    display_path = Path("runs") / result.parent_task_id / "children" / result.child_id
    print(f"Created CIPH child task: {display_path}")
    print(f"- Task: {result.task_path}")
    print(f"- Response: {result.response_path}")
    print(f"- Ownership: {result.ownership_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
