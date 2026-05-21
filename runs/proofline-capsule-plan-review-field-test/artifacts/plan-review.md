# Capsule MVP Plan Review

Date: 2026-05-21

## Finding

The implementation plan described deterministic test ids but did not make `--id` part of the first CLI example.

## Risk

Without a deterministic id in the MVP CLI, implementation tests and agent handoffs could rely on timestamped or generated paths. That would weaken reproducibility and make `verify` examples less precise.

## Fix

Harden the plan so `create` accepts or requires `--id`, and use `docs-context` in example commands:

```bash
python3 capsule.py create --root . --id docs-context --include README.md --include "docs/**/*.md"
python3 capsule.py inspect capsules/docs-context/CAPSULE.json
python3 capsule.py verify capsules/docs-context/CAPSULE.json
```

## Review Decision

Block implementation until deterministic id behavior is explicit in the implementation plan.
