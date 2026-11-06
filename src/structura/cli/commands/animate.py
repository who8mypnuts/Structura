"""`structura animate FILE -o frames/out.png --frames 0:48 [--fps 24] [--video out.mp4]` (docs/16 §2, §5).

v2 scripts read 'frame', 'time' and 'fps' in '( … )' expressions; every frame is rebuilt and rendered.
Frames are written as out_0000.png …; --video also encodes them (MP4/WebM/GIF via imageio-ffmpeg).
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import imageio.v3 as iio
import numpy as np

from ...compute.base import Backend
from ...compute.select import NAMES, select_backend
from ...core.build.api import build_scene
from ...core.errors import StructuraError
from ...core.lang.api import compile_script
from ...core.lang.diagnostics import ParseError
from ...render.api import prepare, progressive, script_settings
from ...render.config import scene_frame
from ...render.output import save_image, to_display
from .common import EXIT_OK, EXIT_SCRIPT_ERROR, EXIT_USAGE, add_script_arguments, parse_params, read_script

HELP = "render an animation (v2 scripts: 'frame', 'time', 'fps' in expressions)"


def _range(text: str) -> range:
    start, _, stop = text.partition(":")
    return range(int(start), int(stop))


def register(p: argparse.ArgumentParser) -> None:
    add_script_arguments(p)
    p.add_argument("-o", "--output", type=Path, required=True, help="frame name pattern, e.g. frames/out.png")
    p.add_argument("--frames", type=_range, default=range(0, 24), help="START:STOP (default 0:24)")
    p.add_argument("--fps", type=float, default=24.0)
    p.add_argument("--size", default=None, help="WIDTHxHEIGHT (default: the script's)")
    p.add_argument("--samples", type=int, default=16)
    p.add_argument("--integrator", default=None)
    p.add_argument("--device", choices=NAMES, default="auto")
    p.add_argument("--video", type=Path, help="also encode the frames (.mp4 .webm .gif)")


def _frame_image(text: str, args: argparse.Namespace, frame: int, backend: Backend) -> tuple[np.ndarray, str]:
    compiled = compile_script(text, args.seed, parse_params(args.param), args.script.parent, frame, args.fps)
    scene = build_scene(compiled.program, args.seed).scene
    overrides: dict[str, Any] = {"samples": args.samples, "samples_per_pass": max(1, min(8, args.samples))}
    if args.integrator:
        overrides["integrator"] = args.integrator
    if args.size:
        width, _, height = args.size.lower().partition("x")
        overrides |= {"width": int(width), "height": int(height)}
    settings = replace(script_settings(scene), **overrides)
    prepared = prepare(scene)
    view = scene_frame(prepared.scene_settings, settings, prepared.lo, prepared.hi, prepared.declarations)
    *_, result = progressive(prepared, settings, backend, view)
    return result.image, settings.view_transform


def run(args: argparse.Namespace) -> int:
    if not args.frames:
        print("animate: --frames must contain at least one frame", file=sys.stderr)
        return EXIT_USAGE
    text, backend = read_script(args.script), select_backend(args.device)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frames = []
    for frame in args.frames:
        try:
            image, view = _frame_image(text, args, frame, backend)
        except (ParseError, StructuraError) as exc:
            print(f"{args.script}: frame {frame}: {getattr(exc, 'message', exc)}", file=sys.stderr)
            return EXIT_SCRIPT_ERROR
        path = args.output.with_name(f"{args.output.stem}_{frame:04d}{args.output.suffix}")
        save_image(image, path, 0.0, view)
        frames.append(to_display(image, 0.0, view))
        print(f"\r  frame {frame} → {path.name}", end="", file=sys.stderr)
    print(file=sys.stderr)
    if args.video is not None:
        if args.video.suffix.lower() == ".gif":
            iio.imwrite(args.video, frames, duration=1000 / args.fps, loop=0)
        else:
            iio.imwrite(args.video, frames, fps=args.fps, macro_block_size=1)
        print(f"wrote {args.video}")
    return EXIT_OK
