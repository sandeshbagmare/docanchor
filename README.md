# docanchor

Find the Markdown links that point at headings that no longer exist.

[![PyPI](https://img.shields.io/pypi/v/docanchor.svg)](https://pypi.org/project/docanchor/)
[![Python](https://img.shields.io/pypi/pyversions/docanchor.svg)](https://pypi.org/project/docanchor/)
[![tests](https://github.com/sandeshbagmare/docanchor/actions/workflows/ci.yml/badge.svg)](https://github.com/sandeshbagmare/docanchor/actions/workflows/ci.yml)
[![license](https://img.shields.io/pypi/l/docanchor.svg)](https://github.com/sandeshbagmare/docanchor/blob/main/LICENSE)

```console
$ docanchor README.md docs/*.md
README.md:42: docs/install.md#quick-start is not a heading there
2 files, 1 broken anchor(s)
```

A link checker follows `docs/install.md` and finds the page, so it reports nothing.
The `#quick-start` on the end is the fragile part: rename the heading and every link
to it silently lands at the top of the page. `docanchor` parses the headings the way
GitHub's renderer does and checks the anchor really exists.

No network, no crawler, no configuration: point it at your Markdown files.

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
