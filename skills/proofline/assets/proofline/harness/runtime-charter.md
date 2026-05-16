# CIPH Runtime Charter

## Authority

The parent agent owns orchestration, scope control, evidence promotion, and final audit. Tools, child agents, browser sessions, and generated artifacts are inputs to inspect; they are not trusted completion authorities.

## Source Truth

The repository is the durable source of work state. Chat can explain decisions, but durable task facts belong in `TASK.md`, `MANIFEST.json`, plans, evidence files, and closeout output.

## Volatile Facts

When a task depends on an API shape, config key, CLI flag, pricing detail, product limit, schema, required field, or other volatile fact, consult the most authoritative available documentation before writing code or setup instructions. Record the source in the task or evidence file when the fact affects the implementation.

## Evidence

Evidence must be concrete: command output, inspected files, generated reports, browser traces, source citations, or explicit blocker records. Passing tests are useful only when they cover the objective requirement being claimed.

## Secrets

Never print secrets, tokens, API keys, private headers, or environment values. Redact sensitive values before promoting logs into evidence.

## Delegation

Delegate only bounded work with clear ownership. A child agent must receive the task, allowed write set, expected output, and verification expectation. The parent must inspect returned changes and verify them locally.

## Closeout

Before completion, run the manifest verifier and render the closeout checklist. Completion requires every explicit objective requirement to be covered by existing artifacts and evidence, or a recorded blocker that explains why the work cannot finish safely.
