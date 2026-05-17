#!/usr/bin/env python3
"""Create a bounded child-task packet for delegated CIPH work."""

from __future__ import annotations

import argparse
from html import escape
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
    if not manifest_path.is_absolute():
        manifest_path = root_path / manifest_path
    manifest = load_manifest(manifest_path)
    parent_task_id = manifest.get("task_id")
    if not isinstance(parent_task_id, str) or not parent_task_id.strip():
        raise ValueError("Parent manifest must include a non-empty task_id")

    run_dir = manifest_path.parent
    child_dir = run_dir / "children" / child_id
    if child_dir.exists() and not force:
        raise FileExistsError(f"Child task already exists: {child_dir}")

    title_text = title.strip() if title and title.strip() else f"Child task {child_id}"
    owner_text = owner.strip() if owner and owner.strip() else "unassigned"
    scopes = write_scopes or []

    (child_dir / "inputs").mkdir(parents=True, exist_ok=True)
    (child_dir / "scratch").mkdir(parents=True, exist_ok=True)
    (child_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    (child_dir / "artifacts" / ".gitkeep").touch()

    proofline_root = run_dir.parent.parent
    task_template = _template_path(proofline_root, "CHILD_TASK")
    response_template = _template_path(proofline_root, "CHILD_RESPONSE")
    use_html = task_template is not None and task_template.suffix == ".html"
    task_path = child_dir / ("TASK.html" if use_html else "TASK.md")
    response_path = child_dir / ("RESPONSE.html" if use_html else "RESPONSE.md")
    ownership_path = child_dir / "OWNERSHIP.json"

    if task_template is not None:
        task_body = _render_task_template(
            task_template.read_text(encoding="utf-8"),
            parent_task_id,
            child_id,
            title_text,
            owner_text,
            scopes,
            manifest,
            use_html,
        )
    else:
        task_body = _render_task(parent_task_id, child_id, title_text, owner_text, scopes, manifest)

    if response_template is not None:
        response_body = _render_response_template(response_template.read_text(encoding="utf-8"), child_id, use_html)
    else:
        response_body = _render_response(child_id)

    task_path.write_text(task_body, encoding="utf-8")
    response_path.write_text(response_body, encoding="utf-8")
    ownership_path.write_text(
        json.dumps(
            {
                "parent_task_id": parent_task_id,
                "child_id": child_id,
                "owner": owner_text,
                "write_scopes": scopes,
                "task_path": _display_path(task_path, root_path),
                "response_path": _display_path(response_path, root_path),
                "artifacts_dir": _display_path(child_dir / "artifacts", root_path),
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


def _template_path(proofline_root: Path, stem: str) -> Path | None:
    templates_dir = proofline_root / "templates"
    html_template = templates_dir / f"{stem}.html"
    if html_template.is_file():
        return html_template
    markdown_template = templates_dir / f"{stem}.md"
    if markdown_template.is_file():
        return markdown_template
    return None


def _render_task_template(
    template: str,
    parent_task_id: str,
    child_id: str,
    title: str,
    owner: str,
    write_scopes: list[str],
    manifest: dict[str, Any],
    is_html: bool,
) -> str:
    parent_objective = str(manifest.get("objective", "<missing>"))
    replacements = {
        "child-id": child_id,
        "parent-task-id": parent_task_id,
        "parent-objective": parent_objective,
        "owner": owner,
        "title": title,
    }
    rendered = template
    for key, value in replacements.items():
        replacement = escape(value) if is_html else value
        rendered = rendered.replace(f"<{key}>", replacement).replace(f"&lt;{key}&gt;", replacement)
    scope_html = _render_scope_html(write_scopes) if is_html else _render_scope_markdown(write_scopes)
    return rendered.replace("<write-scope-list>", scope_html).replace("&lt;write-scope-list&gt;", scope_html)


def _render_response_template(template: str, child_id: str, is_html: bool) -> str:
    replacement = escape(child_id) if is_html else child_id
    return template.replace("<child-id>", replacement).replace("&lt;child-id&gt;", replacement)


def _render_scope_html(write_scopes: list[str]) -> str:
    if not write_scopes:
        return "<p>No write scopes assigned yet.</p>"
    items = "".join(f"<li><code>{escape(scope)}</code></li>" for scope in write_scopes)
    return f"<ul>{items}</ul>"


def _render_scope_markdown(write_scopes: list[str]) -> str:
    return "\n".join(f"- `{scope}`" for scope in write_scopes) if write_scopes else "- No write scopes assigned yet."


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


def _display_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


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

    display_path = _display_path(result.child_dir, args.root)
    print(f"Created CIPH child task: {display_path}")
    print(f"- Task: {result.task_path}")
    print(f"- Response: {result.response_path}")
    print(f"- Ownership: {result.ownership_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
