"""Command line entry point: ``docanchor`` or ``python -m docanchor``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import check_files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="docanchor",
        description="Check that #anchors in Markdown links exist.",
    )
    parser.add_argument("paths", nargs="+", type=Path, metavar="FILE")
    parser.add_argument("-q", "--quiet", action="store_true", help="print only problems")
    args = parser.parse_args(argv)

    missing = [str(path) for path in args.paths if not path.is_file()]
    if missing:
        print(f"no such file: {', '.join(missing)}", file=sys.stderr)
        return 2

    problems = check_files(args.paths)
    for problem in problems:
        print(problem)
    if not args.quiet:
        plural = "" if len(args.paths) == 1 else "s"
        print(f"{len(args.paths)} file{plural}, {len(problems)} broken anchor(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
