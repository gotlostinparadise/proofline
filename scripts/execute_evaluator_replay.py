#!/usr/bin/env python3
"""Execute approved local CIPH evaluator replay commands."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.html_report import render_html_document
    from scripts.validate_evaluator_replay import validate_evaluator_replay
except ModuleNotFoundError:  # pragma: no cover - exercised by direct script execution.
    from html_report import render_html_document
    from validate_evaluator_replay import validate_evaluator_replay


REPLAY_RECEIPT_SCHEMA_VERSION = "ciph.replay-receipt.v1"


@dataclass(frozen=True)
class ReplayCommand:
    evaluator_id: str
    manifest_path: str
    working_directory: str
    argv: list[str]
    env_allowlist: list[str]
    expected_output_hashes: dict[str, str]


@dataclass
class EvaluatorReplayExecutionResult:
    messages: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def execute_evaluator_replay(
    run_dir: Path | str,
    *,
    root: Path | str = ".",
    execute: bool = False,
    allowed_argv0: list[str] | None = None,
    timeout_seconds: float = 30.0,
    sandbox_binary: str = "bwrap",
    receipt_dir: Path | str | None = None,
    report_path: Path | str | None = None,
) -> EvaluatorReplayExecutionResult:
    run_path = Path(run_dir)
    root_path = Path(root)
    receipt_path = Path(receipt_dir) if receipt_dir is not None else run_path / "replay_receipts"
    result = EvaluatorReplayExecutionResult()
    if timeout_seconds <= 0:
        result.errors.append("timeout_seconds must be greater than zero")
        return result

    readiness = validate_evaluator_replay(run_path, root=root_path)
    if not readiness.ok:
        result.errors.extend(f"readiness preflight failed: {error}" for error in readiness.errors)
        return result
    result.messages.extend(readiness.messages)

    commands = _discover_replay_commands(run_path, root_path, result)
    if result.errors:
        return result

    sandbox_path: str | None = None
    if execute:
        sandbox_path = _resolve_sandbox_binary(sandbox_binary)
        if sandbox_path is None:
            for command in commands:
                _write_replay_receipt(
                    command,
                    root_path=root_path,
                    receipt_dir=receipt_path,
                    mode="execute",
                    status="SANDBOX_UNAVAILABLE",
                    sandbox_mode="missing",
                    timeout_seconds=timeout_seconds,
                    report_path=report_path,
                    errors=[f"network sandbox is required for execution and was not found: {sandbox_binary}"],
                )
            result.errors.append(f"network sandbox is required for execution and was not found: {sandbox_binary}")
            return result

    approved_argv0 = set(allowed_argv0 or [])
    for command in commands:
        if not execute:
            result.messages.append(f"DRY-RUN evaluator {command.evaluator_id} command not executed")
            _write_replay_receipt(
                command,
                root_path=root_path,
                receipt_dir=receipt_path,
                mode="dry-run",
                status="DRY_RUN",
                sandbox_mode="none",
                timeout_seconds=timeout_seconds,
                report_path=report_path,
            )
            continue
        if command.argv[0] not in approved_argv0:
            error = f"evaluator {command.evaluator_id} command argv[0] is not approved for execution: {command.argv[0]}"
            result.errors.append(error)
            _write_replay_receipt(
                command,
                root_path=root_path,
                receipt_dir=receipt_path,
                mode="execute",
                status="SKIPPED_ARGV0_NOT_APPROVED",
                sandbox_mode="bwrap-unshare-net",
                timeout_seconds=timeout_seconds,
                report_path=report_path,
                errors=[error],
            )
            continue
        _run_replay_command(
            command,
            root_path=root_path,
            timeout_seconds=timeout_seconds,
            sandbox_path=str(sandbox_path),
            receipt_dir=receipt_path,
            report_path=report_path,
            result=result,
        )

    return result


def write_evaluator_replay_execution_report(
    run_dir: Path | str,
    output_path: Path | str,
    *,
    root: Path | str = ".",
    execute: bool = False,
    allowed_argv0: list[str] | None = None,
    timeout_seconds: float = 30.0,
    sandbox_binary: str = "bwrap",
    receipt_dir: Path | str | None = None,
) -> EvaluatorReplayExecutionResult:
    result = execute_evaluator_replay(
        run_dir,
        root=root,
        execute=execute,
        allowed_argv0=allowed_argv0,
        timeout_seconds=timeout_seconds,
        sandbox_binary=sandbox_binary,
        receipt_dir=receipt_dir,
        report_path=output_path,
    )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix == ".html":
        output.write_text(render_evaluator_replay_execution_report(run_dir, result), encoding="utf-8")
    else:
        output.write_text(render_evaluator_replay_execution_text(run_dir, result), encoding="utf-8")
    return result


def render_evaluator_replay_execution_report(
    run_dir: Path | str,
    result: EvaluatorReplayExecutionResult,
) -> str:
    status = "PASS" if result.ok else "FAIL"
    return render_html_document(
        title="CIPH Evaluator Replay Execution",
        heading="CIPH Evaluator Replay Execution",
        report_kind="evaluator-replay-execution",
        summary_items=[
            ("Run", str(run_dir)),
            ("Status", status),
            ("Errors", str(len(result.errors))),
        ],
        sections=[
            {
                "id": "messages",
                "title": "Messages",
                "items": result.messages,
            },
            {
                "id": "errors",
                "title": "Errors",
                "items": result.errors,
            },
        ],
    )


def render_evaluator_replay_execution_text(
    run_dir: Path | str,
    result: EvaluatorReplayExecutionResult,
) -> str:
    status = "PASS" if result.ok else "FAIL"
    lines = [f"{status} evaluator replay execution {run_dir}"]
    lines.extend(result.messages)
    lines.extend(f"ERROR {error}" for error in result.errors)
    return "\n".join(lines) + "\n"


def _discover_replay_commands(
    run_dir: Path,
    root_path: Path,
    result: EvaluatorReplayExecutionResult,
) -> list[ReplayCommand]:
    evaluation = _load_json_object(run_dir / "EVALUATION.json", result, "EVALUATION.json")
    if evaluation is None:
        return []
    candidates = evaluation.get("candidates")
    if not isinstance(candidates, list):
        result.errors.append("EVALUATION.json candidates must be a list")
        return []

    commands: list[ReplayCommand] = []
    seen_manifest_paths: set[str] = set()
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        for score_key in ("score_path", "holdout_score_path"):
            score_path = candidate.get(score_key)
            if not isinstance(score_path, str) or not score_path.strip():
                continue
            score = _load_json_object(root_path / score_path, result, score_path)
            if score is None:
                continue
            provenance = score.get("score_provenance")
            if not isinstance(provenance, dict):
                result.errors.append(f"{score_path} score_provenance must be an object")
                continue
            manifest_path = provenance.get("evaluator_manifest_path")
            if not isinstance(manifest_path, str) or not manifest_path.strip():
                result.errors.append(f"{score_path} score_provenance.evaluator_manifest_path must be a non-empty string")
                continue
            if manifest_path in seen_manifest_paths:
                continue
            seen_manifest_paths.add(manifest_path)
            manifest = _load_json_object(root_path / manifest_path, result, manifest_path)
            if manifest is None:
                continue
            command = _command_from_manifest(manifest_path, manifest, root_path, result)
            if command is not None:
                commands.append(command)
    return commands


def _command_from_manifest(
    manifest_path: str,
    manifest: dict[str, Any],
    root_path: Path,
    result: EvaluatorReplayExecutionResult,
) -> ReplayCommand | None:
    evaluator_id = manifest.get("evaluator_id")
    replay = manifest.get("replay")
    if not isinstance(evaluator_id, str) or not evaluator_id.strip():
        result.errors.append(f"{manifest_path} evaluator_id must be a non-empty string")
        return None
    if not isinstance(replay, dict):
        result.errors.append(f"evaluator {evaluator_id} replay must be an object")
        return None

    command_metadata = replay.get("command_metadata")
    if not isinstance(command_metadata, dict):
        result.errors.append(f"evaluator {evaluator_id} replay.command_metadata must be an object")
        return None
    argv = command_metadata.get("argv")
    if not isinstance(argv, list) or not argv or not all(isinstance(item, str) and item.strip() for item in argv):
        result.errors.append(f"evaluator {evaluator_id} replay.command_metadata.argv must contain at least one non-empty string")
        return None
    if command_metadata.get("shell") is not False:
        result.errors.append(f"evaluator {evaluator_id} replay.command_metadata.shell must be false")
        return None
    if replay.get("external_effect_policy") != "local-only":
        result.errors.append(f"evaluator {evaluator_id} replay.external_effect_policy must be local-only")
        return None

    working_directory = replay.get("working_directory")
    if not isinstance(working_directory, str) or not working_directory.strip():
        result.errors.append(f"evaluator {evaluator_id} replay.working_directory must be a non-empty string")
        return None
    if not _safe_local_path(root_path, working_directory) or not (root_path / working_directory).is_dir():
        result.errors.append(f"evaluator {evaluator_id} replay.working_directory must be an existing local path under root: {working_directory}")
        return None

    env_allowlist = replay.get("env_allowlist")
    if not isinstance(env_allowlist, list) or not all(isinstance(item, str) and item.strip() and "=" not in item for item in env_allowlist):
        result.errors.append(f"evaluator {evaluator_id} replay.env_allowlist must contain non-empty variable names")
        return None

    expected_output_hashes = replay.get("expected_output_hashes")
    if not isinstance(expected_output_hashes, dict):
        result.errors.append(f"evaluator {evaluator_id} replay.expected_output_hashes must be an object")
        return None

    return ReplayCommand(
        evaluator_id=evaluator_id,
        manifest_path=manifest_path,
        working_directory=working_directory,
        argv=[str(item) for item in argv],
        env_allowlist=[str(item) for item in env_allowlist],
        expected_output_hashes={str(path): str(digest) for path, digest in expected_output_hashes.items()},
    )


def _run_replay_command(
    command: ReplayCommand,
    *,
    root_path: Path,
    timeout_seconds: float,
    sandbox_path: str,
    receipt_dir: Path,
    report_path: Path | str | None,
    result: EvaluatorReplayExecutionResult,
) -> None:
    working_directory = (root_path / command.working_directory).resolve()
    env = {name: os.environ[name] for name in command.env_allowlist if name in os.environ}
    pre_output_hashes = _output_hashes(command, root_path)
    wrapped_command = [
        sandbox_path,
        "--unshare-net",
        "--dev-bind",
        "/",
        "/",
        "--chdir",
        str(working_directory),
        *command.argv,
    ]
    try:
        completed = subprocess.run(
            wrapped_command,
            cwd=root_path,
            env=env,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        stdout_bytes = len(exc.stdout or b"")
        stderr_bytes = len(exc.stderr or b"")
        result.messages.append(
            f"evaluator {command.evaluator_id} execution output suppressed stdout_bytes={stdout_bytes} stderr_bytes={stderr_bytes}"
        )
        error = f"evaluator {command.evaluator_id} execution timed out after {timeout_seconds:g} seconds"
        result.errors.append(error)
        _write_replay_receipt(
            command,
            root_path=root_path,
            receipt_dir=receipt_dir,
            mode="execute",
            status="TIMEOUT",
            sandbox_mode="bwrap-unshare-net",
            timeout_seconds=timeout_seconds,
            report_path=report_path,
            stdout_bytes=stdout_bytes,
            stderr_bytes=stderr_bytes,
            errors=[error],
            pre_output_hashes=pre_output_hashes,
        )
        return

    stdout_bytes = len(completed.stdout or b"")
    stderr_bytes = len(completed.stderr or b"")
    result.messages.append(
        f"evaluator {command.evaluator_id} execution output suppressed stdout_bytes={stdout_bytes} stderr_bytes={stderr_bytes}"
    )
    if completed.returncode != 0:
        error = f"evaluator {command.evaluator_id} execution failed with exit code {completed.returncode}"
        result.errors.append(error)
        _write_replay_receipt(
            command,
            root_path=root_path,
            receipt_dir=receipt_dir,
            mode="execute",
            status="EXECUTION_FAILED",
            sandbox_mode="bwrap-unshare-net",
            timeout_seconds=timeout_seconds,
            report_path=report_path,
            exit_code=completed.returncode,
            stdout_bytes=stdout_bytes,
            stderr_bytes=stderr_bytes,
            errors=[error],
            pre_output_hashes=pre_output_hashes,
        )
        return
    result.messages.append(f"PASS evaluator {command.evaluator_id} execution exit_code=0")
    errors_before = len(result.errors)
    _verify_output_hashes(command, root_path, result)
    status = "PASS" if len(result.errors) == errors_before else "OUTPUT_HASH_MISMATCH"
    _write_replay_receipt(
        command,
        root_path=root_path,
        receipt_dir=receipt_dir,
        mode="execute",
        status=status,
        sandbox_mode="bwrap-unshare-net",
        timeout_seconds=timeout_seconds,
        report_path=report_path,
        exit_code=completed.returncode,
        stdout_bytes=stdout_bytes,
        stderr_bytes=stderr_bytes,
        errors=result.errors[errors_before:],
        pre_output_hashes=pre_output_hashes,
    )


def _verify_output_hashes(
    command: ReplayCommand,
    root_path: Path,
    result: EvaluatorReplayExecutionResult,
) -> None:
    for output_path, expected_digest in command.expected_output_hashes.items():
        if not _safe_local_path(root_path, output_path):
            result.errors.append(f"evaluator {command.evaluator_id} output path is not local: {output_path}")
            continue
        absolute_output = root_path / output_path
        if not absolute_output.is_file():
            result.errors.append(f"evaluator {command.evaluator_id} output path missing after execution: {output_path}")
            continue
        actual_digest = _sha256_digest(absolute_output)
        if actual_digest != expected_digest:
            result.errors.append(f"evaluator {command.evaluator_id} output hash mismatch after execution: {output_path}")
        else:
            result.messages.append(f"PASS evaluator {command.evaluator_id} output hash {output_path}")


def _resolve_sandbox_binary(sandbox_binary: str) -> str | None:
    candidate = Path(sandbox_binary)
    if candidate.is_absolute():
        return str(candidate) if candidate.is_file() and os.access(candidate, os.X_OK) else None
    return shutil.which(sandbox_binary)


def _write_replay_receipt(
    command: ReplayCommand,
    *,
    root_path: Path,
    receipt_dir: Path,
    mode: str,
    status: str,
    sandbox_mode: str,
    timeout_seconds: float,
    report_path: Path | str | None,
    exit_code: int | None = None,
    stdout_bytes: int = 0,
    stderr_bytes: int = 0,
    errors: list[str] | None = None,
    pre_output_hashes: dict[str, str | None] | None = None,
) -> Path:
    started_at = _utc_now()
    pre_hashes = pre_output_hashes if pre_output_hashes is not None else _output_hashes(command, root_path)
    post_output_hashes = _output_hashes(command, root_path)
    receipt = {
        "schema_version": REPLAY_RECEIPT_SCHEMA_VERSION,
        "evaluator_id": command.evaluator_id,
        "manifest_path": command.manifest_path,
        "mode": mode,
        "status": status,
        "command_digest": _command_digest(command.argv),
        "argv": command.argv,
        "working_directory": command.working_directory,
        "sandbox_mode": sandbox_mode,
        "timeout_seconds": timeout_seconds,
        "env_allowlist": command.env_allowlist,
        "expected_output_hashes": command.expected_output_hashes,
        "pre_output_hashes": pre_hashes,
        "post_output_hashes": post_output_hashes,
        "exit_code": exit_code,
        "stdout_bytes": stdout_bytes,
        "stderr_bytes": stderr_bytes,
        "errors": errors or [],
        "report_path": str(report_path) if report_path is not None else None,
        "started_at_utc": started_at,
        "finished_at_utc": _utc_now(),
    }
    receipt_dir.mkdir(parents=True, exist_ok=True)
    path = receipt_dir / f"{_slugify(command.evaluator_id)}-{mode}.json"
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _output_hashes(command: ReplayCommand, root_path: Path) -> dict[str, str | None]:
    hashes: dict[str, str | None] = {}
    for output_path in command.expected_output_hashes:
        if _safe_local_path(root_path, output_path) and (root_path / output_path).is_file():
            hashes[output_path] = _sha256_digest(root_path / output_path)
        else:
            hashes[output_path] = None
    return hashes


def _command_digest(argv: list[str]) -> str:
    encoded = json.dumps(argv, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _slugify(value: str) -> str:
    result = []
    previous_dash = False
    for char in value.lower():
        if char.isalnum():
            result.append(char)
            previous_dash = False
        elif not previous_dash:
            result.append("-")
            previous_dash = True
    return "".join(result).strip("-") or "evaluator"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_json_object(
    path: Path,
    result: EvaluatorReplayExecutionResult,
    label: str,
) -> dict[str, Any] | None:
    if not path.is_file():
        result.errors.append(f"{label} does not exist")
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        result.errors.append(f"{label} invalid JSON: {exc.msg}")
        return None
    if not isinstance(payload, dict):
        result.errors.append(f"{label} must contain a JSON object")
        return None
    return payload


def _safe_local_path(root_path: Path, reference: str) -> bool:
    candidate = Path(reference)
    if candidate.is_absolute():
        return False
    try:
        (root_path / candidate).resolve().relative_to(root_path.resolve())
    except ValueError:
        return False
    return True


def _sha256_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Execute approved local CIPH evaluator replay commands.")
    parser.add_argument("run_dir", type=Path, help="Path to run directory")
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root for path references")
    parser.add_argument("--output", type=Path, default=None, help="Write replay execution report to this path")
    parser.add_argument("--execute", action="store_true", help="Actually execute approved local replay commands; default is dry-run")
    parser.add_argument("--allow-argv0", action="append", default=[], help="Approve an exact argv[0] value for execution")
    parser.add_argument("--timeout-seconds", type=float, default=30.0, help="Per-command timeout in seconds")
    parser.add_argument("--sandbox-binary", default="bwrap", help="Bubblewrap binary used for no-network execution")
    parser.add_argument("--receipt-dir", type=Path, default=None, help="Directory for replay receipt JSON files")
    args = parser.parse_args(argv)

    if args.output is not None:
        result = write_evaluator_replay_execution_report(
            args.run_dir,
            args.output,
            root=args.root,
            execute=args.execute,
            allowed_argv0=args.allow_argv0,
            timeout_seconds=args.timeout_seconds,
            sandbox_binary=args.sandbox_binary,
            receipt_dir=args.receipt_dir,
        )
        print(f"Wrote CIPH evaluator replay execution report: {args.output}")
    else:
        result = execute_evaluator_replay(
            args.run_dir,
            root=args.root,
            execute=args.execute,
            allowed_argv0=args.allow_argv0,
            timeout_seconds=args.timeout_seconds,
            sandbox_binary=args.sandbox_binary,
            receipt_dir=args.receipt_dir,
        )

    print(render_evaluator_replay_execution_text(args.run_dir, result), end="")
    for error in result.errors:
        print(f"ERROR {error}", file=sys.stderr)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
