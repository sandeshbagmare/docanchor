"""Tests for docanchor."""

import pytest

from docanchor import (
    Heading,
    Link,
    Problem,
    anchors,
    check,
    check_files,
    headings,
    links,
    slug,
)


class TestSlug:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("Install", "install"),
            ("Install & Setup", "install--setup"),
            ("What's new?", "whats-new"),
            ("a  b", "a--b"),
            ("Under_score", "under_score"),
            ("Use `x` here", "use--here"),
            ("  padded  ", "padded"),
            ("Ünïcode heading", "ünïcode-heading"),
            ("1. Numbered", "1-numbered"),
            ("C++ / Rust", "c--rust"),
        ],
    )
    def test_slug_rules(self, text, expected):
        assert slug(text) == expected


class TestHeadings:
    def test_atx_headings(self):
        found = headings("# One\n\n### Three\n")
        assert [h.level for h in found] == [1, 3]
        assert [h.slug for h in found] == ["one", "three"]

    def test_heading_text_drops_the_closing_hashes(self):
        assert headings("## Usage ##\n")[0].text == "Usage"

    def test_line_numbers_are_reported(self):
        assert headings("intro\n\n## Usage\n")[0].line == 3

    def test_setext_headings(self):
        found = headings("Title\n=====\n\nSub\n---\n")
        assert [(h.level, h.slug) for h in found] == [(1, "title"), (2, "sub")]

    def test_fenced_code_is_ignored(self):
        markdown = "```md\n# not a heading\n```\n\n# real\n"
        assert [h.slug for h in headings(markdown)] == ["real"]

    def test_tilde_fences_are_ignored(self):
        assert [h.slug for h in headings("~~~\n# no\n~~~\n\n# yes\n")] == ["yes"]

    def test_duplicate_headings_are_numbered(self):
        found = headings("# Notes\n\n# Notes\n\n# Notes\n")
        assert [h.slug for h in found] == ["notes", "notes-1", "notes-2"]

    def test_seven_hashes_is_not_a_heading(self):
        assert headings("####### nope\n") == []

    def test_hash_without_space_is_not_a_heading(self):
        assert headings("#nope\n") == []

    def test_a_list_item_is_not_a_setext_heading(self):
        assert [h.slug for h in headings("- item\n- item\n")] == []

    def test_empty_document(self):
        assert headings("") == []


class TestAnchors:
    def test_heading_slugs_are_anchors(self):
        assert anchors("## Quick start\n") == {"quick-start"}

    def test_duplicate_headings_offer_both_anchors(self):
        assert anchors("# Notes\n# Notes\n") == {"notes", "notes-1"}

    def test_explicit_html_ids_count(self):
        assert "custom" in anchors('<a name="custom"></a>\n')

    def test_other_html_ids_count(self):
        assert "deep" in anchors('<div id="deep"></div>\n')

    def test_ids_are_lower_cased(self):
        assert "Mixed" not in anchors('<a name="Mixed"></a>\n')


class TestLinks:
    def test_local_anchor(self):
        found = links("See [setup](#setup).\n")
        assert found == [Link(None, "setup", 1, "setup")]

    def test_anchor_in_another_file(self):
        found = links("[install](docs/install.md#quick-start)\n")
        assert found == [Link("docs/install.md", "quick-start", 1, "install")]

    def test_links_without_an_anchor_are_ignored(self):
        assert links("[other](docs/other.md)\n") == []

    def test_external_links_are_ignored(self):
        assert links("[x](https://example.com/page#frag)\n") == []

    def test_mailto_links_are_ignored(self):
        assert links("[mail](mailto:a@b.c#x)\n") == []

    def test_images_are_ignored(self):
        assert links("![logo](img/logo.svg#anchor)\n") == []

    def test_links_inside_code_fences_are_ignored(self):
        assert links("```\n[a](#b)\n```\n") == []

    def test_several_links_on_one_line(self):
        assert len(links("[a](#a) and [b](#b)\n")) == 2


class TestCheck:
    def test_a_valid_local_link_is_quiet(self):
        assert check("# Setup\n\n[go](#setup)\n", lambda _: None) == []

    def test_a_missing_local_anchor_is_reported(self):
        problems = check("# Setup\n\n[go](#install)\n", lambda _: None)
        assert len(problems) == 1
        assert problems[0].line == 3
        assert "#install is not a heading here" in problems[0].message

    def test_a_valid_cross_file_link_is_quiet(self):
        resolver = lambda _: "# Quick start\n"  # noqa: E731
        assert check("[go](install.md#quick-start)\n", resolver) == []

    def test_a_missing_cross_file_anchor_names_the_file(self):
        problems = check("[go](install.md#nope)\n", lambda _: "# Quick start\n")
        assert "install.md#nope is not a heading there" in problems[0].message

    def test_an_unreadable_file_is_reported(self):
        problems = check("[go](gone.md#x)\n", lambda _: None)
        assert "gone.md cannot be read" in problems[0].message

    def test_the_resolver_is_not_called_for_local_links(self):
        calls = []

        def resolver(target):
            calls.append(target)
            return "# x\n"

        check("[go](#setup)\n", resolver)
        assert calls == []

    def test_anchor_matching_ignores_case(self):
        assert check("# Setup\n\n[go](#SETUP)\n", lambda _: None) == []

    def test_the_source_is_carried_into_the_message(self):
        problems = check("[go](#nada)\n", lambda _: None, source="README.md")
        assert str(problems[0]).startswith("README.md:1: ")

    def test_a_heading_with_trailing_punctuation_still_matches(self):
        assert check("## Works?\n\n[x](#works)\n", lambda _: None) == []


class TestCheckFiles:
    def test_links_between_files_are_resolved(self, tmp_path):
        (tmp_path / "install.md").write_text("# Quick start\n", encoding="utf-8")
        (tmp_path / "README.md").write_text("[go](install.md#quick-start)\n", encoding="utf-8")
        assert check_files([tmp_path / "README.md"]) == []

    def test_a_broken_cross_file_link_is_reported(self, tmp_path):
        (tmp_path / "install.md").write_text("# Something else\n", encoding="utf-8")
        (tmp_path / "README.md").write_text("[go](install.md#quick-start)\n", encoding="utf-8")
        problems = check_files([tmp_path / "README.md"])
        assert len(problems) == 1

    def test_a_missing_file_is_reported(self, tmp_path):
        (tmp_path / "README.md").write_text("[go](nope.md#x)\n", encoding="utf-8")
        assert "cannot be read" in check_files([tmp_path / "README.md"])[0].message

    def test_a_directory_target_is_reported(self, tmp_path):
        (tmp_path / "docs").mkdir()
        (tmp_path / "README.md").write_text("[go](docs#x)\n", encoding="utf-8")
        assert "cannot be read" in check_files([tmp_path / "README.md"])[0].message

    def test_several_documents(self, tmp_path):
        (tmp_path / "a.md").write_text("# A\n\n[bad](#b)\n", encoding="utf-8")
        (tmp_path / "b.md").write_text("# B\n", encoding="utf-8")
        problems = check_files([tmp_path / "a.md", tmp_path / "b.md"])
        assert [p.source for p in problems] == [str(tmp_path / "a.md")]


class TestTypes:
    def test_problem_str_has_the_editor_shape(self):
        assert str(Problem("a.md", 4, "boom")) == "a.md:4: boom"

    def test_heading_is_frozen(self):
        heading = Heading(1, "A", "a", 1)
        with pytest.raises(AttributeError):
            heading.slug = "b"  # type: ignore[misc]

    def test_link_reports_local_targets(self):
        assert Link(None, "a", 1).is_local is True
        assert Link("x.md", "a", 1).is_local is False


class TestCommandLine:
    def run(self, argv):
        from docanchor.__main__ import main

        return main(argv)

    def test_clean_files_exit_zero(self, tmp_path, capsys):
        path = tmp_path / "README.md"
        path.write_text("# Setup\n\n[go](#setup)\n", encoding="utf-8")
        assert self.run([str(path)]) == 0
        assert "0 broken anchor(s)" in capsys.readouterr().out

    def test_a_broken_anchor_exits_one(self, tmp_path, capsys):
        path = tmp_path / "README.md"
        path.write_text("# Setup\n\n[go](#install)\n", encoding="utf-8")
        assert self.run([str(path)]) == 1
        assert "README.md:3" in capsys.readouterr().out

    def test_a_missing_file_exits_two(self, tmp_path, capsys):
        assert self.run([str(tmp_path / "nope.md")]) == 2
        assert "no such file" in capsys.readouterr().err

    def test_quiet_prints_only_problems(self, tmp_path, capsys):
        path = tmp_path / "README.md"
        path.write_text("# Setup\n\n[go](#install)\n", encoding="utf-8")
        assert self.run([str(path), "--quiet"]) == 1
        assert "file, " not in capsys.readouterr().out


class TestRigour:
    """A file that two links point at is read once and reused."""

    def test_a_target_read_twice_comes_from_the_cache(self, tmp_path, monkeypatch):
        from pathlib import Path

        target = tmp_path / "b.md"
        target.write_text("# Bee\n\n## Buzz\n", encoding="utf-8")
        page = tmp_path / "a.md"
        page.write_text(
            "[one](b.md#bee) and [two](b.md#buzz) and [three](b.md)\n", encoding="utf-8"
        )

        reads = []
        real = Path.read_text

        def counting(self, *args, **kwargs):
            reads.append(self.name)
            return real(self, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", counting)
        problems = check_files([page])
        assert problems == []
        assert reads.count("b.md") == 1

    def test_an_unreadable_target_is_not_a_crash(self, tmp_path):

        page = tmp_path / "a.md"
        page.write_text("[gone](missing.md#x)\n", encoding="utf-8")
        problems = check_files([page])
        assert [problem.message for problem in problems] == ["missing.md cannot be read"]

    def test_a_directory_target_cannot_be_read(self, tmp_path):
        (tmp_path / "sub").mkdir()
        page = tmp_path / "a.md"
        page.write_text("[sub](sub#x)\n", encoding="utf-8")
        assert [problem.message for problem in check_files([page])] == ["sub cannot be read"]

    def test_a_link_without_an_anchor_is_not_checked(self, tmp_path):
        page = tmp_path / "a.md"
        page.write_text("[gone](missing.md)\n", encoding="utf-8")
        assert check_files([page]) == []
