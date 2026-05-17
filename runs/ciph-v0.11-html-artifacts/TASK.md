# CIPH Task

## Objective

Migrate Proofline human-facing artifacts from Markdown-first to HTML-first while preserving manifest compatibility and historical runs.

## Acceptance Object

The work is acceptable when new Proofline runs and child packets are generated as HTML-first artifacts, status/closeout/candidate summaries can be written as self-contained HTML, docs and the bundled Codex skill teach the HTML workflow, existing Markdown historical runs remain valid, and automated tests prove both the new HTML behavior and backward compatibility.

## Constraints

- Repository rules: keep the harness file-backed, stdlib-only, deterministic, and friendly to vendored installs.
- Files or areas in scope: `scripts/`, `templates/`, `tests/`, `README.md`, `harness/`, `skills/proofline/`, and this run.
- Files or areas out of scope: rewriting historical run records, adding a web framework, adding remote assets, or changing the manifest JSON schema.
- Permissions: network was used only to learn the approved HTML-effectiveness source material; implementation should not require network access.
- Secrets handling: no secrets or API keys are required.

## Volatile Facts To Verify

- Source material claims and examples from `https://thariqs.github.io/html-effectiveness/` and `https://github.com/ThariqS/html-effectiveness/tree/main` were reviewed before implementation.
- X status pages did not expose tweet text in this environment; do not depend on inaccessible tweet content for implementation details.
- HTML output must be generated with Python standard-library escaping and parsing only.

## Deliverables

| ID | Requirement | Artifact paths | Evidence paths |
| --- | --- | --- | --- |
| source-notes | Record the applicable HTML-effectiveness lessons and migration boundary. | `runs/ciph-v0.11-html-artifacts/artifacts/source-notes.html` | `runs/ciph-v0.11-html-artifacts/artifacts/checks/html-migration-tests.txt` |
| html-templates | Add HTML-first task and child templates while preserving historical Markdown compatibility. | `templates/TASK.html`, `templates/CHILD_TASK.html`, `templates/CHILD_RESPONSE.html`, `scripts/init_run.py`, `scripts/init_child_task.py` | `runs/ciph-v0.11-html-artifacts/artifacts/checks/html-migration-tests.txt` |
| html-reports | Render status, closeout, and candidate summary reports as self-contained HTML when requested. | `scripts/html_report.py`, `scripts/run_status.py`, `scripts/closeout_check.py`, `scripts/candidate_summary.py`, `runs/ciph-v0.11-html-artifacts/artifacts/status.html`, `runs/ciph-v0.11-html-artifacts/artifacts/closeout.html` | `runs/ciph-v0.11-html-artifacts/artifacts/checks/html-report-generation.txt` |
| docs-skill | Update operator docs and the bundled Codex skill to use HTML-first paths and closeout commands. | `README.md`, `index.html`, `harness/CIPH.md`, `harness/runtime-charter.md`, `skills/proofline/SKILL.md`, `skills/proofline/assets/proofline/` | `runs/ciph-v0.11-html-artifacts/artifacts/checks/html-migration-tests.txt` |
| compatibility-tests | Add automated coverage for generated HTML artifacts, HTML report parsing, and Markdown compatibility. | `tests/test_html_artifacts.py`, `tests/test_init_run.py`, `tests/test_init_child_task.py`, `tests/test_run_status.py`, `tests/test_closeout_check.py`, `tests/test_candidate_summary.py`, `tests/test_proofline_skill.py` | `runs/ciph-v0.11-html-artifacts/artifacts/checks/full-unit-tests.txt` |

## Risks And Blockers

- HTML can become decorative noise if the structure is not machine-checkable; tests must assert semantic sections and escaped content, not only file existence.
- Full Markdown removal would break historical runs and downstream habits; this run migrates defaults and generated artifacts while preserving readers and old reports.

## Closeout Commands

```bash
python3 scripts/lint_manifest.py runs/ciph-v0.11-html-artifacts/MANIFEST.json --root .
python3 scripts/run_checks.py runs/ciph-v0.11-html-artifacts/MANIFEST.json --root .
python3 scripts/verify_manifest.py runs/ciph-v0.11-html-artifacts/MANIFEST.json --root .
python3 scripts/run_status.py runs/ciph-v0.11-html-artifacts/MANIFEST.json --root . --output runs/ciph-v0.11-html-artifacts/artifacts/status.html
python3 scripts/closeout_check.py runs/ciph-v0.11-html-artifacts/MANIFEST.json --root . --output runs/ciph-v0.11-html-artifacts/artifacts/closeout.html
python3 scripts/check_repo.py
```
