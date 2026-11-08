"""`structura theme {list,check,import}` — theme tools (docs/13, docs/16 §5)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ...themes.importers import import_theme
from ...themes.loader import builtin_ids, load_file, load_theme, theme_ids, user_dir
from .common import EXIT_OK, EXIT_USAGE

HELP = "list, check or import colour themes"


def register(p: argparse.ArgumentParser) -> None:
    sub = p.add_subparsers(dest="action", required=True)
    sub.add_parser("list", help="every installed theme (built-in and user)")
    check = sub.add_parser("check", help="resolve a theme file and report contrast fixes")
    check.add_argument("file", type=Path)
    check.add_argument("--strict", action="store_true", help="exit 1 when a colour needed a contrast fix")
    imported = sub.add_parser("import", help="import a VS Code (.json) or Base16 (.yaml) theme")
    imported.add_argument("file", type=Path)


def _list() -> int:
    builtin = set(builtin_ids())
    for theme_id in theme_ids():
        meta = load_theme(theme_id).meta
        print(f"{theme_id:24} {meta.kind:5}  {'built-in' if theme_id in builtin else 'user':8}  {meta.name}")
    return EXIT_OK


def _check(path: Path, strict: bool) -> int:
    try:
        theme = load_file(path)
    except (OSError, ValueError, KeyError) as exc:
        print(f"{path}: error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    for line in theme.adjustments:
        print(f"{path}: adjusted {line}")
    print(f"{path}: {theme.meta.name} ({theme.meta.kind}), {len(theme.adjustments)} contrast fix(es)")
    return 1 if strict and theme.adjustments else EXIT_OK


def run(args: argparse.Namespace) -> int:
    if args.action == "list":
        return _list()
    if args.action == "check":
        return _check(args.file, args.strict)
    try:
        written = import_theme(args.file, user_dir())
    except (OSError, ValueError, KeyError) as exc:
        print(f"{args.file}: cannot import: {exc}", file=sys.stderr)
        return EXIT_USAGE
    print(f"imported {written}")
    return EXIT_OK
