"""`structura build FILE` — build the structure and print statistics; optionally dump the SceneIR."""

from __future__ import annotations

import argparse
import sys
from dataclasses import asdict
from pathlib import Path

from ...core.build.api import build_scene
from ...core.errors import StructuraError
from ...core.scene.ir_io import save_scene
from .common import EXIT_OK, EXIT_SCRIPT_ERROR, add_script_arguments, compile_or_report

HELP = "build a script and report statistics"


def register(p: argparse.ArgumentParser) -> None:
    add_script_arguments(p)
    p.add_argument("--dump", type=Path, help="write the SceneIR arrays to an .npz file")


def run(args: argparse.Namespace) -> int:
    compiled, _ = compile_or_report(args)
    if compiled is None:
        return EXIT_SCRIPT_ERROR
    try:
        result = build_scene(compiled.program, args.seed)
    except StructuraError as exc:
        print(f"{args.script}: error: {exc.message}", file=sys.stderr)
        return EXIT_SCRIPT_ERROR
    for key, value in asdict(result.stats).items():
        print(f"{key:>16}: {value}")
    if args.dump:
        save_scene(result.scene, args.dump)
        print(f"{'dump':>16}: {args.dump}")
    return EXIT_OK
