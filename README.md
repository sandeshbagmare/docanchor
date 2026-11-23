<p align="center">
  <img src="https://raw.githubusercontent.com/sandeshbagmare/docanchor/main/assets/banner.svg" width="100%" alt="docanchor: catch every broken heading anchor in your docs">
</p>

<p align="center">
  <a href="https://pypi.org/project/docanchor/"><img alt="PyPI version" src="https://img.shields.io/pypi/v/docanchor.svg"></a>
  <a href="https://pypi.org/project/docanchor/"><img alt="Python versions" src="https://img.shields.io/pypi/pyversions/docanchor.svg"></a>
  <a href="https://pypi.org/project/docanchor/"><img alt="Downloads" src="https://img.shields.io/pypi/dm/docanchor.svg"></a>
  <a href="https://github.com/sandeshbagmare/docanchor/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/sandeshbagmare/docanchor/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/sandeshbagmare/docanchor/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/pypi/l/docanchor.svg"></a>
  <a href="https://sandeshbagmare.github.io/docanchor/"><img alt="docs" src="https://img.shields.io/badge/docs-online-2ea44f.svg"></a>
  <a href="https://pypi.org/project/docanchor/"><img alt="zero dependencies" src="https://img.shields.io/badge/dependencies-0-2ea44f.svg"></a>
</p>

<h3 align="center">catch every broken heading anchor in your docs</h3>
<p align="center"><em>Standard library only. No runtime dependencies. Python 3.9+.</em></p>

<p align="center">
  <img src="https://raw.githubusercontent.com/sandeshbagmare/docanchor/main/assets/how.svg" width="720" alt="how docanchor fits in">
</p>

## Install

```console
pip install docanchor
```

## Use

```python
from docanchor import check_files

for problem in check_files(["README.md", "docs/install.md"]):
    print(problem)          # README.md:42: docs/install.md#quick-start is not ...
```

Or check a string against a resolver you control:

```python
from docanchor import check

docs = {"install.md": "## Quick start\n"}
problems = check(
    "See [install](install.md#quick-start).",
    resolve=docs.get,          # None means "cannot read"
    source="README.md",
)
```

## What counts as an anchor

- ATX headings `## Quick start` → `quick-start`
- setext headings (`Title` over `=====`) → `title`
- duplicates get `-1`, `-2`, as GitHub does, so both `#notes` and `#notes-1` work
- explicit `<a name="custom">` and any HTML `id="custom"`
- headings inside fenced code blocks are ignored, as are links there
- matching is case-insensitive

Slugs follow GitHub's rules: lowercase, inline code removed, punctuation dropped,
spaces turned into hyphens. Emoji and other symbols disappear the same way they do
on GitHub, so an emoji-only heading gets a stable (if empty) slug.

## What is skipped

- external links (`https:`, `mailto:`, …) — this is not a crawler
- links without a `#anchor`
- images (`![alt](img.svg#x)`)
- reference-style links and HTML `href`s

Those are the cases where a full link checker (or the site build) already helps.

## Development

```console
python -m venv .venv
.venv/bin/pip install -e ".[test]"
.venv/bin/pytest
```

## License

MIT.
