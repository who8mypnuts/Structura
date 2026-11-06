"""`structura export FILE -o out.usdc [--format NAME] [--option key=value …]` (docs/15 §7, docs/16 §5)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ...core.build.api import build_scene
from ...core.errors import StructuraError
from ...export.api import EXPORTERS, export_scene, find_exporter
from .common import EXIT_OK, EXIT_SCRIPT_ERROR, EXIT_USAGE, add_script_arguments, compile_or_report

HELP = "export a script's structure (OBJ, PLY, STL, glTF, USD, Blender, templates)"


def register(p: argparse.ArgumentParser) -> None:
    add_script_arguments(p)
    p.add_argument("-o", "--output", type=Path, required=True, help="output file; the extension picks the format")
    p.add_argument("--format", choices=sorted(EXPORTERS), help="exporter (default: from the extension)")
    p.add_argument("--option", action="append", default=[], metavar="KEY=VALUE", help="exporter option")
    p.add_argument("--list-options", action="store_true", help="show the chosen exporter's options and exit")


def _options(items: list[str]) -> dict[str, str]:
    out = {}
    for item in items:
        key, sep, value = item.partition("=")
        if not sep:
            raise ValueError(f"--option expects KEY=VALUE, got {item!r}")
        out[key.strip()] = value.strip()
    return out


def run(args: argparse.Namespace) -> int:
    try:
        exporter = find_exporter(args.output, args.format)
        options = _options(args.option)
    except ValueError as exc:
        print(f"export: {exc}", file=sys.stderr)
        return EXIT_USAGE
    if args.list_options:
        for spec in exporter.params:
            extra = f" ({'|'.join(spec.choices)})" if spec.choices else ""
            print(f"{spec.key}={spec.default}{extra}  {spec.title}")
        return EXIT_OK
    compiled, _ = compile_or_report(args)
    if compiled is None:
        return EXIT_SCRIPT_ERROR
    try:
        scene = build_scene(compiled.program, args.seed).scene
        report = export_scene(scene, args.output, exporter.name, options)
    except (StructuraError, ValueError) as exc:
        print(f"export: {getattr(exc, 'message', exc)}", file=sys.stderr)
        return EXIT_SCRIPT_ERROR
    for warning in report.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    counts = ", ".join(f"{k} {v:,}" for k, v in report.counts.items())
    print(f"wrote {', '.join(str(p) for p in report.files)}" + (f" ({counts})" if counts else ""))
    return EXIT_OK
