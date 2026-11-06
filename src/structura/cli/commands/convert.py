"""`structura convert FILE --to v2 [-o OUT]` — migrate a Structure Synth 1.5 script to EisenScript v2 (docs/16 §5).

Prints what changed and a unified diff for review; writes OUT when given (the input is never overwritten
unless OUT names it).
"""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

from ...core.lang.convert import convert_to_v2
from ...core.text_file import TextFile, read, write
from .common import EXIT_OK

HELP = "migrate a Structure Synth 1.5 script to EisenScript v2"


def register(p: argparse.ArgumentParser) -> None:
    p.add_argument("script", type=Path, help="EisenScript file (.es)")
    p.add_argument("--to", choices=["v2"], default="v2", help="target dialect")
    p.add_argument("-o", "--output", type=Path, help="write the converted script here")
    p.add_argument("--quiet", action="store_true", help="no diff, only the notes")


def run(args: argparse.Namespace) -> int:
    source = read(args.script)
    result = convert_to_v2(source.text)
    for note in result.notes or ("already EisenScript v2: nothing to do",):
        print(f"  {note}", file=sys.stderr)
    if not args.quiet and result.changed:
        diff = difflib.unified_diff(source.text.splitlines(keepends=True), result.text.splitlines(keepends=True),
                                    str(args.script), str(args.output or "converted"))  # fmt: skip
        sys.stdout.writelines(diff)
    if args.output is not None:
        write(args.output, TextFile(result.text, source.encoding, source.newline))
        print(f"wrote {args.output}", file=sys.stderr)
    return EXIT_OK
