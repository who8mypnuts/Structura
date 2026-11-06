"""`structura build FILE` — build the structure and print statistics; optionally dump the SceneIR."""

from __future__ import annotations

import argparse
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np

from ...core.build.api import build_scene
from ...core.errors import StructuraError
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
        scene = result.scene
        np.savez_compressed(
            args.dump,
            kind=scene.kind,
            xform=scene.xform,
            rgba=scene.rgba,
            tag=scene.tag,
            source=scene.source,
            generation=scene.generation,
            aux=scene.aux,
            aux_data=scene.aux_data,
            tags=np.array(scene.tags),
        )
        print(f"{'dump':>16}: {args.dump}")
    return EXIT_OK
