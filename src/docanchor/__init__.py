"""Check that the anchors in Markdown links exist.

A docs site goes stale quietly: ``[setup](install.md#quick-start)`` keeps working
from the link checker's point of view even after the heading was renamed, and the
reader lands at the top of the page instead. This module parses the headings the way
GitHub does, collects the anchors a document offers, and reports the links that point
at nothing.

    >>> from docanchor import slug
    >>> slug("Install & Setup")
    'install--setup'

Standard library only, Python 3.9+.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "Heading",
    "Link",
    "Problem",
    "anchors",
    "check",
    "check_files",
    "headings",
    "links",
    "slug",
]

__version__ = "0.1.0"

_FENCE = re.compile(r"^(?P<indent>[ \t]*)(?P<fence>`{3,}|~{3,})")
_ATX = re.compile(r"^(?P<level>#{1,6})[ \t]+(?P<text>.*?)[ \t]*#*[ \t]*$")
_SETEXT_UNDERLINE = re.compile(r"^[ \t]*(?P<char>=+|-{2,})[ \t]*$")
_CODE_SPAN = re.compile(r"`[^`]*`")
_HTML_ANCHOR = re.compile(
    r"<a\b[^>]*?\b(?:name|id)\s*=\s*[\"'](?P<slug>[^\"']+)[\"']", re.IGNORECASE
)
_HTML_ANY_ID = re.compile(r"\b(?:id|name)\s*=\s*[\"'](?P<slug>[^\"']+)[\"']", re.IGNORECASE)
_LINK = re.compile(
    r"(?<!!)\[(?P<text>(?:[^\[\]]|\[[^\]]*\])*)\]\((?P<dest>[^()\s]*(?:\([^()]*\)[^()\s]*)*)"
    r"(?:\s+\"[^\"]*\")?\)"
)
_URL_SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:")


@dataclass(frozen=True)
class Heading:
    """A heading found in a document."""

    level: int
    text: str
    slug: str
    line: int


@dataclass(frozen=True)
class Link:
    """A link with an anchor, as written in the document."""

    target: str | None
    anchor: str
    line: int
    text: str = ""

    @property
    def is_local(self) -> bool:
        return self.target is None


@dataclass(frozen=True)
class Problem:
    """A link pointing at an anchor that does not exist."""

    source: str
    line: int
    message: str

    def __str__(self) -> str:
        return f"{self.source}:{self.line}: {self.message}"


def slug(text: str) -> str:
    """Slugify heading text the way GitHub's Markdown renderer does.

    Lowercase, drop inline code and anything that is not a letter, digit, space,
    hyphen or underscore, then turn runs of spaces into hyphens. Duplicate headings
    are disambiguated by :func:`headings`, not here.
    """
    plain = _CODE_SPAN.sub("", text)
    lowered = plain.strip().lower()
    kept = "".join(ch for ch in lowered if ch.isalnum() or ch in " -_")
    return kept.replace(" ", "-")


def _iter_lines(markdown: str) -> Iterable[tuple[int, str, bool]]:
    """Yield ``(line_number, line, inside_fenced_code)`` for a document."""
    fence: tuple[str, int] | None = None
    for number, raw in enumerate(markdown.splitlines(), start=1):
        line = raw.rstrip()
        match = _FENCE.match(line)
        if match:
            marker = match.group("fence")
            character, length = marker[0], len(marker)
            if fence is None:
                fence = (character, length)
                yield number, line, True
                continue
            if fence[0] == character and length >= fence[1]:
                fence = None
                yield number, line, True
                continue
        yield number, line, fence is not None


def headings(markdown: str) -> list[Heading]:
    """Every ATX and setext heading in the document, with GitHub's de-duplicated slugs."""
    lines = list(_iter_lines(markdown))
    found: list[Heading] = []
    seen: dict[str, int] = {}
    for index, (number, line, in_code) in enumerate(lines):
        if in_code or not line.strip():
            continue
        level = 0
        text = ""
        atx = _ATX.match(line)
        if atx:
            level = len(atx.group("level"))
            text = atx.group("text").strip()
        elif index + 1 < len(lines):
            _, underline, underline_in_code = lines[index + 1]
            setext = _SETEXT_UNDERLINE.match(underline or "")
            if setext and not underline_in_code and line.strip():
                level = 1 if setext.group("char").startswith("=") else 2
                text = line.strip()
        if not level or not text:
            continue
        base = slug(text)
        count = seen.get(base, 0)
        seen[base] = count + 1
        found.append(Heading(level, text, base if count == 0 else f"{base}-{count}", number))
    return found


def anchors(markdown: str) -> set[str]:
    """Every anchor the document offers: heading slugs and explicit HTML ids."""
    found = {heading.slug.lower() for heading in headings(markdown)}
    for match in _HTML_ANY_ID.finditer(markdown):
        found.add(match.group("slug").lower())
    return found


def links(markdown: str) -> list[Link]:
    """Inline links that carry an anchor and could land inside the docs."""
    found: list[Link] = []
    for number, line, in_code in _iter_lines(markdown):
        if in_code:
            continue
        for match in _LINK.finditer(line):
            destination = match.group("dest").strip()
            target, _, anchor = destination.partition("#")
            if not anchor:
                continue
            if _URL_SCHEME.match(target):
                continue
            found.append(
                Link(
                    target or None,
                    anchor,
                    number,
                    match.group("text").strip(),
                )
            )
    return found


def check(
    markdown: str,
    resolve: Callable[[str], str | None],
    *,
    source: str = "<string>",
) -> list[Problem]:
    """Report the anchors in ``markdown`` that no document provides.

    ``resolve`` maps a linked path to its text, or to ``None`` when the file cannot be
    read. It is only called for links that point at another document.
    """
    problems: list[Problem] = []
    own = anchors(markdown)
    for link in links(markdown):
        wanted = link.anchor.lower()
        if link.is_local:
            if wanted not in own:
                problems.append(Problem(source, link.line, f"#{link.anchor} is not a heading here"))
            continue
        text = resolve(link.target or "")
        if text is None:
            problems.append(Problem(source, link.line, f"{link.target} cannot be read"))
            continue
        if wanted not in anchors(text):
            problems.append(
                Problem(source, link.line, f"{link.target}#{link.anchor} is not a heading there")
            )
    return problems


def check_files(
    paths: Sequence[str | Path],
    *,
    encoding: str = "utf-8",
) -> list[Problem]:
    """Check a set of Markdown files, resolving links relative to each file."""
    problems: list[Problem] = []
    cache: dict[Path, str] = {}
    for raw in paths:
        path = Path(raw)
        text = path.read_text(encoding=encoding)

        def resolve(target: str, _base: Path = path.parent, _depth: int = 0) -> str | None:
            candidate = (_base / target).resolve()
            if candidate in cache:
                return cache[candidate]
            if candidate.is_dir():
                return None
            try:
                content = candidate.read_text(encoding=encoding)
            except OSError:
                return None
            cache[candidate] = content
            return content

        problems.extend(check(text, resolve, source=str(path)))
    return problems
