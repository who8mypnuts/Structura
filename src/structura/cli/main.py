"""`structura` command-line entry point (docs/16 §5)."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from .. import __version__
from .commands import animate, build, doctor, export, lint, render, run

COMMANDS = {
    "lint": lint,
    "build": build,
    "render": render,
    "export": export,
    "animate": animate,
    "run": run,
    "doctor": doctor,
}


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="structura", description="Structura — grammar-based 3D structures.")
    root.add_argument("--version", action="version", version=f"structura {__version__}")
    sub = root.add_subparsers(dest="command", required=True)
    for name, module in COMMANDS.items():
        module.register(sub.add_parser(name, help=module.HELP, description=module.HELP))
    return root


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    return int(COMMANDS[args.command].run(args))


if __name__ == "__main__":
    sys.exit(main())
