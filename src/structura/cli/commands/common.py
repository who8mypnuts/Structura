"""Helpers shared by CLI commands: loading scripts, parameters, reporting errors with positions."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ...core.errors import StructuraError
from ...core.lang.api import CompiledScript, compile_script
from ...core.lang.diagnostics import Diagnostic, ParseError
from ...core.lang.source import LineIndex
from ...core.text_file import read_script

EXIT_OK, EXIT_SCRIPT_ERROR, EXIT_USAGE = 0, 1, 2


def add_script_arguments(p: argparse.ArgumentParser) -> None:
    p.add_argument("script", type=Path, help="EisenScript file (.es)")
    p.add_argument("--seed", type=int, default=0, help="random seed (default 0)")
    p.add_argument("--param", action="append", default=[], metavar="NAME=VALUE", help="GUI parameter value")


def parse_params(items: list[str]) -> dict[str, float]:
    values: dict[str, float] = {}
    for item in items:
        name, _, value = item.partition("=")
        values[name.strip()] = float(value)
    return values


def report(path: Path, text: str, diagnostic: Diagnostic) -> None:
    where = ""
    if diagnostic.span is not None:
        line, column = LineIndex.of(text).position(diagnostic.span.start)
        where = f"{line}:{column}: "
    print(f"{path}:{where}{diagnostic.severity.name.lower()} {diagnostic.code}: {diagnostic.message}", file=sys.stderr)


def compile_or_report(args: argparse.Namespace) -> tuple[CompiledScript | None, str]:
    text = read_script(args.script)
    try:
        compiled = compile_script(text, args.seed, parse_params(args.param), args.script.parent)
    except ParseError as exc:
        report(args.script, text, exc.diagnostic())
        return None, text
    except StructuraError as exc:
        print(f"{args.script}: error: {exc.message}", file=sys.stderr)
        return None, text
    for diagnostic in compiled.diagnostics:
        report(args.script, text, diagnostic)
    return compiled, text
