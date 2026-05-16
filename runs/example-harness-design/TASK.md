# CIPH Task

## Objective

Validate the initial structured HTML research artifact for the request:

> Invent agent harness to simplify complex coding projects. Study `https://arxiv.org/pdf/2603.28052v1` and `https://arxiv.org/pdf/2603.25723` while documenting valuable information into structured HTML.

## Acceptance Object

The run is acceptable when `index.html` exists, links both papers, documents research takeaways, presents an invented harness design, and has local verification evidence.

## Constraints

- Keep the artifact repo-native and inspectable.
- Do not depend on third-party packages.
- Preserve the source links in the artifact.
- Do not treat tests alone as completion; map the objective to concrete evidence.

## Volatile Facts To Verify

- Source papers were fetched directly from arXiv during the research turn.
- No API, CLI, pricing, product-limit, or schema fact is needed for this sample run.

## Deliverables

| ID | Requirement | Artifact paths | Evidence paths |
| --- | --- | --- | --- |
| source-meta-harness | Study and cite `https://arxiv.org/pdf/2603.28052v1`. | `index.html` | `source:https://arxiv.org/pdf/2603.28052v1` |
| source-nlah | Study and cite `https://arxiv.org/pdf/2603.25723`. | `index.html` | `source:https://arxiv.org/pdf/2603.25723` |
| structured-html | Document valuable information in structured HTML. | `index.html` | `runs/example-harness-design/artifacts/verification.md` |
| invented-harness | Present an invented harness for complex coding projects. | `index.html` | `runs/example-harness-design/artifacts/verification.md` |

## Risks And Blockers

- None recorded.

## Closeout Commands

```bash
python3 scripts/verify_manifest.py runs/example-harness-design/MANIFEST.json --root .
python3 scripts/closeout_check.py runs/example-harness-design/MANIFEST.json --root .
```
