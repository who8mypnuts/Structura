"""`structura run SCRIPT [--limit N]`: run a Structure Synth '#javascript' script (docs/16 §3), or a Python
script that uses the Python API (`import structura as st`, docs/16 §4)."""

from __future__ import annotations

import argparse
import runpy
import sys
import traceback
from pathlib import Path

from PySide6.QtCore import QCoreApplication

from ...compute.select import select_backend
from ...core.text_file import read_script
from ...scripting.js_bridge import run_javascript
from ...services.scripting import BuilderHost, Channel
from .common import EXIT_OK, EXIT_SCRIPT_ERROR

HELP = "run a '#javascript' script (Builder.load / define / build / raytraceToFile …) or a Python (.py) script"


def register(p: argparse.ArgumentParser) -> None:
    p.add_argument("script", type=Path)
    p.add_argument("--limit", type=int, help="stop after this many output files")
    p.add_argument("--samples", type=int, help="override the samples of each raytrace")
    p.add_argument("--device", default="auto")
    p.add_argument("--allow-execute", action="store_true", help="let Builder.execute run external programs")
    p.add_argument("--dir", type=Path, help="the folder file names are relative to (default: the script's)")
    p.add_argument("--ipc", action="store_true", help=argparse.SUPPRESS)  # run for the window (services/scripting.py)


def _report(message: str) -> None:
    print(f"  {message}", file=sys.stderr)


def run_python(script: Path) -> int:
    """A .py script, as `python script.py` would run it (its folder first on sys.path)."""
    sys.path.insert(0, str(script.resolve().parent))
    try:
        runpy.run_path(str(script), run_name="__main__")
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else EXIT_OK
    except Exception:
        traceback.print_exc()
        return EXIT_SCRIPT_ERROR
    return EXIT_OK


def run(args: argparse.Namespace) -> int:
    if args.script.suffix.lower() == ".py":
        return run_python(args.script)
    app = QCoreApplication.instance() or QCoreApplication(sys.argv[:1])
    channel = Channel() if args.ipc else None
    host = BuilderHost(select_backend(args.device), args.samples, args.allow_execute, _report, channel=channel)
    folder = args.dir or args.script.parent
    try:
        written = run_javascript(read_script(args.script), folder, host, args.limit)
    except (RuntimeError, ValueError, OSError) as exc:
        print(f"{args.script}: {exc}", file=sys.stderr)
        return EXIT_SCRIPT_ERROR
    del app
    print(f"wrote {written} file{'s' if written != 1 else ''}")
    return EXIT_OK
