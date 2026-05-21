# Capsule

Capsule is a dependency-free context packaging tool for AI agent work.

It answers:

> What exact context did the agent receive, where did it come from, and can we reproduce it?

Capsule is a sibling to Proofline. Proofline owns task proof: scope, manifest, checks, evidence, status, and closeout. Capsule owns context proof: selected files, source paths, digests, warning records, and reproducibility.

## Create

```bash
python3 capsule.py create --root . --id docs-context --include README.md --include "docs/**/*.md"
```

This writes:

- `capsules/docs-context/CAPSULE.json`
- `capsules/docs-context/FILES.txt`
- `capsules/docs-context/DIGESTS.json`
- `capsules/docs-context/REDACTIONS.json`
- `capsules/docs-context/capsule.html`

Use `--ignore` to exclude matched paths:

```bash
python3 capsule.py create --root . --id docs-context --include "docs/**/*.md" --ignore "docs/private/**"
```

## Inspect

```bash
python3 capsule.py inspect capsules/docs-context/CAPSULE.json
```

`inspect` prints the capsule id, file count, byte count, warning count, and artifact paths.

## Verify

```bash
python3 capsule.py verify capsules/docs-context/CAPSULE.json
```

`verify` recomputes recorded file digests and fails if an included file is missing or changed.

## Secret-Like Warnings

Capsule records secret-like warning metadata without printing matched values. Warning records include path, line number, and marker type, not the token or key value.

## Non-Goals

Capsule does not run tests, manage Proofline tasks, call LLM APIs, implement memory retrieval, authorize side effects, compare candidates, or require third-party dependencies.
