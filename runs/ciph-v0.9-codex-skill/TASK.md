# CIPH Task

## Objective

Package Proofline as a reusable Codex skill with bundled installer assets.

## Acceptance Object

The work is acceptable when the repository contains a reusable `skills/proofline` Codex skill, the skill bundles enough Proofline assets to install the harness into another repo, installer tests pass, Codex skill validation passes, the skill is installed into `/home/bm/.codex/skills/proofline`, and this run records evidence and closeout.

## Constraints

- Repository rules: use the skill-creator workflow, keep the skill concise, and keep installer behavior deterministic.
- Files or areas in scope: `skills/proofline`, installer tests, this run, and local skill installation.
- Files or areas out of scope: publishing a marketplace package, adding CI provider config, and renaming the existing CIPH internals.
- Permissions: local filesystem writes, git commit, and push to the configured repository.
- Secrets handling: no secrets are required; do not print tokens or credentials.

## Volatile Facts To Verify

Codex skill shape and `agents/openai.yaml` fields were verified from the local `skill-creator` skill instructions and references. No external API, pricing, or product-limit fact is required.

## Deliverables

| ID | Requirement | Artifact paths | Evidence paths |
| --- | --- | --- | --- |
| skill-source | Add a reusable Proofline Codex skill with discovery metadata. | `skills/proofline/SKILL.md`, `skills/proofline/agents/openai.yaml` | `runs/ciph-v0.9-codex-skill/artifacts/checks/skill-quick-validate.txt` |
| installer-assets | Bundle installer code and Proofline harness assets for use in other repositories. | `skills/proofline/scripts/install_proofline.py`, `skills/proofline/assets/proofline/harness/CIPH.md`, `skills/proofline/assets/proofline/scripts/init_run.py`, `skills/proofline/assets/proofline/templates/MANIFEST.json` | `runs/ciph-v0.9-codex-skill/artifacts/checks/proofline-skill-tests.txt` |
| local-install | Install the skill into the local Codex skills directory for cross-project use. | `skills/proofline/scripts/install_proofline.py` | `runs/ciph-v0.9-codex-skill/artifacts/checks/local-skill-install.txt` |
| run-closeout | Record status and closeout for this skill-packaging run. | `runs/ciph-v0.9-codex-skill/artifacts/status.md`, `runs/ciph-v0.9-codex-skill/artifacts/closeout.md` | `runs/ciph-v0.9-codex-skill/artifacts/checks/proofline-skill-tests.txt` |

## Risks And Blockers

- None yet.

## Closeout Commands

```bash
python3 scripts/lint_manifest.py runs/ciph-v0.9-codex-skill/MANIFEST.json --root .
python3 scripts/run_checks.py runs/ciph-v0.9-codex-skill/MANIFEST.json --root .
python3 scripts/verify_manifest.py runs/ciph-v0.9-codex-skill/MANIFEST.json --root .
python3 scripts/check_repo.py --skip-diff-check
python3 scripts/closeout_check.py runs/ciph-v0.9-codex-skill/MANIFEST.json --root .
python3 scripts/run_status.py runs/ciph-v0.9-codex-skill/MANIFEST.json --root . --output runs/ciph-v0.9-codex-skill/artifacts/status.md
python3 scripts/closeout_check.py runs/ciph-v0.9-codex-skill/MANIFEST.json --root . --output runs/ciph-v0.9-codex-skill/artifacts/closeout.md
```
