"""`structura lint FILE` — preprocess, parse and resolve; print diagnostics (exit 1 on errors)."""

from __future__ import annotations

import argparse

from .common import EXIT_OK, EXIT_SCRIPT_ERROR, add_script_arguments, compile_or_report

HELP = "check a script for errors and warnings"


def register(p: argparse.ArgumentParser) -> None:
    add_script_arguments(p)


def run(args: argparse.Namespace) -> int:
    compiled, _ = compile_or_report(args)
    return EXIT_OK if compiled is not None else EXIT_SCRIPT_ERROR
