"""`structura` command-line entry point (docs/16 §5)."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from .. import __version__
from .commands import animate, build, convert, devices, doctor, export, lint, render, run, template, theme, warmup

COMMANDS = {
    "lint": lint,
    "build": build,
    "render": render,
    "export": export,
    "template": template,
    "animate": animate,
    "run": run,
    "convert": convert,
    "doctor": doctor,
    "devices": devices,
    "theme": theme,
    "warmup": warmup,
}


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="structura", description="Structura — grammar-based 3D structures.")
    root.add_argument("--version", action="version", version=f"structura {__version__}")
    sub = root.add_subparsers(dest="command", required=True)
    for name, module in COMMANDS.items():
        module.register(sub.add_parser(name, help=module.HELP, description=module.HELP))
    return root


def opens_gui(argv: Sequence[str]) -> bool:
    """`structura` alone, or `structura FILE…` (scripts, projects): launch the GUI (docs/16 §5)."""
    return not argv or (argv[0] not in COMMANDS and not argv[0].startswith("-") and Path(argv[0]).suffix != "")


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if opens_gui(argv):
        from ..app.main import main as gui  # noqa: PLC0415 - the GUI stack loads only when needed

        return gui([sys.argv[0], *argv])
    args = parser().parse_args(argv)
    return int(COMMANDS[args.command].run(args))


if __name__ == "__main__":
    sys.exit(main())
