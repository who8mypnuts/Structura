"""`structura run SCRIPT.es [--limit N]`: run a Structure Synth '#javascript' script (docs/16 §3)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication

from ...compute.select import select_backend
from ...core.text_file import read_script
from ...scripting.js_bridge import run_javascript
from ...services.scripting import BuilderHost
from .common import EXIT_OK, EXIT_SCRIPT_ERROR

HELP = "run a Structure Synth '#javascript' script (Builder.load / define / build / raytraceToFile …)"


def register(p: argparse.ArgumentParser) -> None:
    p.add_argument("script", type=Path)
    p.add_argument("--limit", type=int, help="stop after this many output files")
    p.add_argument("--samples", type=int, help="override the samples of each raytrace")
    p.add_argument("--device", default="auto")
    p.add_argument("--allow-execute", action="store_true", help="let Builder.execute run external programs")


def _report(message: str) -> None:
    print(f"  {message}", file=sys.stderr)


def run(args: argparse.Namespace) -> int:
    app = QCoreApplication.instance() or QCoreApplication(sys.argv[:1])
    host = BuilderHost(select_backend(args.device), args.samples, args.allow_execute, _report)
    try:
        written = run_javascript(read_script(args.script), args.script.parent, host, args.limit)
    except (RuntimeError, ValueError, OSError) as exc:
        print(f"{args.script}: {exc}", file=sys.stderr)
        return EXIT_SCRIPT_ERROR
    del app
    print(f"wrote {written} file{'s' if written != 1 else ''}")
    return EXIT_OK
