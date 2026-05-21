#!/usr/bin/env python3
"""Create, inspect, and verify dependency-free Capsule context packages."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import html
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CAPSULE_SCHEMA_VERSION = "capsule.v1"
GENERATOR = "capsule.py"
SECRET_MARKERS = (
    "API_KEY",
    "ACCESS_TOKEN",
    "AUTH_TOKEN",
    "SECRET",
    "PRIVATE_KEY",
    "PASSWORD",
)


@dataclass(frozen=True)
class FileDigest:
    path: str
    sha256: str
    byte_count: int
    line_count: int


@dataclass(frozen=True)
class CapsuleResult:
    capsule_dir: Path
    manifest_path: Path
    file_count: int
    byte_count: int
    warning_count: int


def create_capsule(root: Path, capsule_id: str, includes: list[str], ignores: list[str]) -> CapsuleResult:
    root = root.resolve()
    if not includes:
        raise ValueError("at least one --include pattern is required")
    if not capsule_id.strip():
        raise ValueError("--id must be a non-empty string")

    capsule_dir = root / "capsules" / capsule_id
    capsule_dir.mkdir(parents=True, exist_ok=True)

    selected, excluded = _select_files(root, includes, ignores)
    digests = [_digest_file(root, rel_path) for rel_path in selected]
    warnings = _scan_warnings(root, selected)

    (capsule_dir / "FILES.txt").write_text("\n".join(selected) + ("\n" if selected else ""), encoding="utf-8")
    _write_json(
        capsule_dir / "DIGESTS.json",
        {
            "schema_version": CAPSULE_SCHEMA_VERSION,
            "files": {
                digest.path: {
                    "sha256": digest.sha256,
                    "byte_count": digest.byte_count,
                    "line_count": digest.line_count,
                }
                for digest in digests
            },
        },
    )
    _write_json(
        capsule_dir / "REDACTIONS.json",
        {
            "schema_version": CAPSULE_SCHEMA_VERSION,
            "warnings": warnings,
            "redactions": [],
        },
    )

    total_bytes = sum(digest.byte_count for digest in digests)
    manifest = {
        "schema_version": CAPSULE_SCHEMA_VERSION,
        "capsule_id": capsule_id,
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "root": str(root),
        "selection_rules": {
            "include": includes,
            "ignore": ignores,
        },
        "included_files": selected,
        "excluded_files": excluded,
        "digests_path": "DIGESTS.json",
        "redactions_path": "REDACTIONS.json",
        "files_path": "FILES.txt",
        "html_report_path": "capsule.html",
        "risk_summary": {
            "warning_count": len(warnings),
            "secret_like_file_count": len({warning["path"] for warning in warnings}),
            "total_bytes": total_bytes,
            "total_files": len(selected),
        },
        "generator": GENERATOR,
    }
    _write_json(capsule_dir / "CAPSULE.json", manifest)
    (capsule_dir / "capsule.html").write_text(_render_html(manifest, digests, warnings), encoding="utf-8")

    return CapsuleResult(
        capsule_dir=capsule_dir,
        manifest_path=capsule_dir / "CAPSULE.json",
        file_count=len(selected),
        byte_count=total_bytes,
        warning_count=len(warnings),
    )


def inspect_capsule(manifest_path: Path) -> str:
    manifest = _load_manifest(manifest_path)
    capsule_dir = manifest_path.parent
    digests = _load_json(capsule_dir / str(manifest["digests_path"]))
    redactions = _load_json(capsule_dir / str(manifest["redactions_path"]))
    files = digests.get("files", {})
    warnings = redactions.get("warnings", [])
    total_bytes = sum(int(meta.get("byte_count", 0)) for meta in files.values() if isinstance(meta, dict))
    return "\n".join(
        [
            f"capsule: {manifest['capsule_id']}",
            f"files: {len(files)}",
            f"bytes: {total_bytes}",
            f"warnings: {len(warnings) if isinstance(warnings, list) else 0}",
            f"manifest: {manifest_path}",
            f"digests: {capsule_dir / manifest['digests_path']}",
            f"redactions: {capsule_dir / manifest['redactions_path']}",
        ]
    ) + "\n"


def verify_capsule(manifest_path: Path) -> tuple[bool, list[str]]:
    manifest = _load_manifest(manifest_path)
    root = Path(str(manifest["root"]))
    capsule_dir = manifest_path.parent
    digests_json = _load_json(capsule_dir / str(manifest["digests_path"]))
    digest_map = digests_json.get("files", {})
    errors: list[str] = []

    if not isinstance(digest_map, dict):
        return False, ["DIGESTS.json files must be an object"]

    for rel_path, expected in sorted(digest_map.items()):
        if not isinstance(expected, dict):
            errors.append(f"{rel_path}: digest record is malformed")
            continue
        file_path = root / rel_path
        if not file_path.is_file():
            errors.append(f"{rel_path}: missing file")
            continue
        actual = _digest_file(root, rel_path)
        if actual.sha256 != expected.get("sha256"):
            errors.append(f"{rel_path}: digest mismatch")
        if actual.byte_count != expected.get("byte_count"):
            errors.append(f"{rel_path}: byte count mismatch")
        if actual.line_count != expected.get("line_count"):
            errors.append(f"{rel_path}: line count mismatch")

    return not errors, errors


def _select_files(root: Path, includes: list[str], ignores: list[str]) -> tuple[list[str], list[str]]:
    selected: set[str] = set()
    excluded: set[str] = set()
    for pattern in includes:
        for path in root.glob(pattern):
            if not path.is_file():
                continue
            rel_path = path.relative_to(root).as_posix()
            if rel_path.startswith("capsules/"):
                continue
            if _is_ignored(rel_path, ignores):
                excluded.add(rel_path)
                continue
            selected.add(rel_path)
    return sorted(selected), sorted(excluded)


def _is_ignored(rel_path: str, ignores: list[str]) -> bool:
    return any(fnmatch.fnmatch(rel_path, pattern) for pattern in ignores)


def _digest_file(root: Path, rel_path: str) -> FileDigest:
    data = (root / rel_path).read_bytes()
    return FileDigest(
        path=rel_path,
        sha256=hashlib.sha256(data).hexdigest(),
        byte_count=len(data),
        line_count=len(data.splitlines()),
    )


def _scan_warnings(root: Path, selected: list[str]) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    for rel_path in selected:
        data = (root / rel_path).read_bytes()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            marker = _secret_marker(line)
            if marker is None:
                continue
            warnings.append(
                {
                    "kind": "secret-like-content",
                    "path": rel_path,
                    "line": line_number,
                    "marker": marker,
                }
            )
    return warnings


def _secret_marker(line: str) -> str | None:
    upper = line.upper()
    for marker in SECRET_MARKERS:
        if marker in upper and ("=" in line or ":" in line):
            return marker
    return None


def _render_html(manifest: dict[str, Any], digests: list[FileDigest], warnings: list[dict[str, Any]]) -> str:
    file_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(digest.path)}</td>"
        f"<td>{digest.byte_count}</td>"
        f"<td>{digest.line_count}</td>"
        f"<td><code>{html.escape(digest.sha256)}</code></td>"
        "</tr>"
        for digest in digests
    )
    warning_items = "\n".join(
        f"<li>{html.escape(warning['path'])}: line {warning['line']} ({html.escape(warning['marker'])})</li>"
        for warning in warnings
    ) or "<li>None.</li>"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Capsule {html.escape(str(manifest["capsule_id"]))}</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,sans-serif;line-height:1.5;margin:32px;color:#161616;background:#fbfaf7}}
main{{max-width:980px;margin:0 auto}}
table{{border-collapse:collapse;width:100%;background:#fff}}
th,td{{border:1px solid #d8d5ca;padding:8px;text-align:left;vertical-align:top}}
code{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}}
</style>
</head>
<body>
<main>
<h1>Capsule {html.escape(str(manifest["capsule_id"]))}</h1>
<p>Files: {len(digests)}. Bytes: {manifest["risk_summary"]["total_bytes"]}. Warnings: {len(warnings)}.</p>
<h2>Warnings</h2>
<ul>{warning_items}</ul>
<h2>Files</h2>
<table>
<thead><tr><th>Path</th><th>Bytes</th><th>Lines</th><th>SHA-256</th></tr></thead>
<tbody>{file_rows}</tbody>
</table>
</main>
</body>
</html>
"""


def _load_manifest(manifest_path: Path) -> dict[str, Any]:
    manifest = _load_json(manifest_path)
    if manifest.get("schema_version") != CAPSULE_SCHEMA_VERSION:
        raise ValueError(f"unsupported capsule schema: {manifest.get('schema_version')}")
    for field in ["capsule_id", "root", "digests_path", "redactions_path"]:
        if not isinstance(manifest.get(field), str) or not manifest[field]:
            raise ValueError(f"CAPSULE.json missing {field}")
    return manifest


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create, inspect, and verify Capsule context packages.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="Create a Capsule context package.")
    create.add_argument("--root", type=Path, default=Path("."), help="Workspace root.")
    create.add_argument("--id", required=True, help="Deterministic capsule id.")
    create.add_argument("--include", action="append", default=[], help="Path or glob pattern to include.")
    create.add_argument("--ignore", action="append", default=[], help="Path or glob pattern to exclude.")

    inspect_parser = subparsers.add_parser("inspect", help="Print a Capsule summary.")
    inspect_parser.add_argument("manifest", type=Path, help="Path to CAPSULE.json.")

    verify = subparsers.add_parser("verify", help="Verify Capsule digests.")
    verify.add_argument("manifest", type=Path, help="Path to CAPSULE.json.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "create":
            result = create_capsule(args.root, args.id, args.include, args.ignore)
            print(f"created capsule: {result.capsule_dir}")
            print(f"files: {result.file_count}")
            print(f"bytes: {result.byte_count}")
            print(f"warnings: {result.warning_count}")
            return 0
        if args.command == "inspect":
            print(inspect_capsule(args.manifest), end="")
            return 0
        if args.command == "verify":
            ok, errors = verify_capsule(args.manifest)
            if ok:
                print(f"PASS capsule verify {args.manifest}")
                return 0
            for error in errors:
                print(error)
            return 1
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
