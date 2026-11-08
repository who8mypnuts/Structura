"""`structura template FILE --template NAME -o out` — legacy template export (docs/15 §5, docs/16 §5).

The same as `structura export --format template --option template=NAME`, with 1.5's wording."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import export
from .common import add_script_arguments

HELP = "export with a Structure Synth 1.5 render template (Sunflow, POV-Ray, RenderMan, …)"


def register(p: argparse.ArgumentParser) -> None:
    add_script_arguments(p)
    p.add_argument("-o", "--output", type=Path, required=True, help="the file the template writes")
    p.add_argument("--template", default="Sunflow-Colored", help="template name (see --list-options)")
    p.add_argument("--size", default="", help="WIDTHxHEIGHT placed in the template (default 640x480)")
    p.add_argument("--list-options", action="store_true", help="show the template choices and exit")


def run(args: argparse.Namespace) -> int:
    options = [f"template={args.template}"]
    if args.size:
        width, _, height = args.size.lower().partition("x")
        options += [f"width={width}", f"height={height}"]
    args.format, args.option = "template", options
    return export.run(args)
