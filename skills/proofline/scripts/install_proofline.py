#!/usr/bin/env python3
"""Install bundled Proofline harness assets into a target repository."""

from __future__ import annotations

import argparse
import filecmp
import shutil
import stat
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class InstallResult:
    copied: list[Path] = field(default_factory=list)
    unchanged: list[Path] = field(default_factory=list)
    conflicts: list[Path] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.conflicts


def install_proofline(target: Path | str, force: bool = False) -> InstallResult:
    target_path = Path(target)
    source_root = Path(__file__).resolve().parents[1] / "assets" / "proofline"
    if not source_root.is_dir():
        raise FileNotFoundError(f"Missing bundled Proofline assets: {source_root}")

    result = InstallResult()
    files = sorted(path for path in source_root.rglob("*") if path.is_file())

    for source in files:
        relative = source.relative_to(source_root)
        destination = target_path / relative
        if destination.exists():
            if destination.is_file() and filecmp.cmp(source, destination, shallow=False):
                result.unchanged.append(relative)
                continue
            if not force:
                result.conflicts.append(relative)
                continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        if relative.parts and relative.parts[0] == "scripts" and destination.suffix == ".py":
            _make_executable(destination)
        result.copied.append(relative)

    return result


def _make_executable(path: Path) -> None:
    current = path.stat().st_mode
    executable = current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    path.chmod(executable)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install Proofline harness assets into a repository.")
    parser.add_argument("--target", type=Path, default=Path("."), help="Target repository root")
    parser.add_argument("--force", action="store_true", help="Overwrite conflicting target files")
    args = parser.parse_args(argv)

    try:
        result = install_proofline(args.target, force=args.force)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if result.conflicts:
        print("Refusing to overwrite existing Proofline target files without --force:", file=sys.stderr)
        for conflict in result.conflicts:
            print(f"- {conflict}", file=sys.stderr)
        return 1

    print(f"Installed Proofline into {args.target}")
    print(f"Copied: {len(result.copied)}")
    print(f"Unchanged: {len(result.unchanged)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
