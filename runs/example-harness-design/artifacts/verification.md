# Verification Evidence

## HTML Parse

Command:

```bash
python3 - <<'PY'
from html.parser import HTMLParser
from pathlib import Path
parser = HTMLParser()
parser.feed(Path('index.html').read_text(encoding='utf-8'))
parser.close()
print('HTML parse ok')
PY
```

Observed output:

```text
HTML parse ok
```

## Source And Section Markers

Command:

```bash
rg -n "2603\.28052|2603\.25723|Invented Harness: CIPH|Verification Matrix|Minimum Viable Harness" index.html
```

Observed output excerpt:

```text
309:        <a href="https://arxiv.org/pdf/2603.28052v1">
313:        <a href="https://arxiv.org/pdf/2603.25723">
416:        <h2>Invented Harness: CIPH</h2>
644:        <h2>Verification Matrix</h2>
689:        <h2>Minimum Viable Harness</h2>
```
