#!/usr/bin/env python3
"""Initialize a CIPH run directory from the repository templates."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
DEFAULT_OBJECTIVE = "State the original user request in concrete terms."


@dataclass(frozen=True)
class InitRunResult:
    run_id: str
    run_dir: Path
    task_path: Path
    manifest_path: Path
    artifacts_dir: Path


def initialize_run(
    run_id: str,
    root: Path | str = ".",
    proofline_root: Path | str | None = None,
    objective: str | None = None,
    force: bool = False,
) -> InitRunResult:
    validate_run_id(run_id)
    root_path = Path(root)
    proofline_path = Path(proofline_root) if proofline_root is not None else root_path
    templates_dir = proofline_path / "templates"
    run_dir = proofline_path / "runs" / run_id
    task_path = run_dir / "TASK.md"
    manifest_path = run_dir / "MANIFEST.json"
    artifacts_dir = run_dir / "artifacts"

    if run_dir.exists() and not force:
        raise FileExistsError(f"Run already exists: runs/{run_id}")

    task_template = _read_template(templates_dir / "TASK.md")
    manifest_template = _load_manifest_template(templates_dir / "MANIFEST.json")
    objective_text = objective.strip() if objective and objective.strip() else DEFAULT_OBJECTIVE

    run_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir / ".gitkeep").touch()

    task_path.write_text(_render_task(task_template, run_id, objective_text), encoding="utf-8")
    manifest_path.write_text(
        json.dumps(_render_manifest(manifest_template, run_id, objective_text), indent=2) + "\n",
        encoding="utf-8",
    )

    return InitRunResult(
        run_id=run_id,
        run_dir=run_dir,
        task_path=task_path,
        manifest_path=manifest_path,
        artifacts_dir=artifacts_dir,
    )


def validate_run_id(run_id: str) -> None:
    if not RUN_ID_PATTERN.match(run_id):
        raise ValueError(
            "Run id must start with an alphanumeric character and contain only letters, "
            "numbers, dots, underscores, or hyphens."
        )


def _read_template(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"Missing template: {path}")
    return path.read_text(encoding="utf-8")


def _load_manifest_template(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing template: {path}")
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Manifest template must be a JSON object: {path}")
    return payload


def _render_task(template: str, run_id: str, objective: str) -> str:
    rendered = template.replace("<run-id>", run_id)
    placeholder = "State the original user request in concrete terms."
    if placeholder in rendered:
        rendered = rendered.replace(placeholder, objective, 1)
    return rendered


def _render_manifest(template: dict[str, Any], run_id: str, objective: str) -> dict[str, Any]:
    rendered = _replace_placeholders(template, run_id, objective)
    rendered["task_id"] = run_id
    rendered["objective"] = objective
    return rendered


def _replace_placeholders(value: Any, run_id: str, objective: str) -> Any:
    if isinstance(value, str):
        return value.replace("<run-id>", run_id).replace("<original objective>", objective)
    if isinstance(value, list):
        return [_replace_placeholders(item, run_id, objective) for item in value]
    if isinstance(value, dict):
        return {key: _replace_placeholders(item, run_id, objective) for key, item in value.items()}
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Initialize a CIPH run directory.")
    parser.add_argument("run_id", help="Run id using letters, numbers, dots, underscores, or hyphens")
    parser.add_argument("--root", type=Path, default=Path("."), help="Project repository root")
    parser.add_argument(
        "--proofline-root",
        type=Path,
        default=None,
        help="Proofline state root containing templates/ and runs/; defaults to --root",
    )
    parser.add_argument("--objective", default=None, help="Original user objective for TASK.md and MANIFEST.json")
    parser.add_argument("--force", action="store_true", help="Overwrite generated files for an existing run")
    args = parser.parse_args(argv)

    try:
        result = initialize_run(args.run_id, args.root, args.proofline_root, args.objective, args.force)
    except (FileExistsError, FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1

    display_path = _display_path(result.run_dir, args.root)
    print(f"Created CIPH run: {display_path}")
    print(f"- Task: {result.task_path}")
    print(f"- Manifest: {result.manifest_path}")
    print(f"- Artifacts: {result.artifacts_dir}")
    return 0


def _display_path(path: Path, root: Path) -> Path | str:
    try:
        return path.relative_to(root)
    except ValueError:
        return path


if __name__ == "__main__":
    raise SystemExit(main())
