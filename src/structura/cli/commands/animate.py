"""`structura animate FILE -o frames/out.png [--frames 0:48] [--fps 24] [--video out.mp4]` (docs/16 §2, §5).

FILE is a script or a .structura project. A project brings its timeline (keyed parameters, seed and camera;
the default frame range and fps), parameter values, seed and camera. v2 scripts can also read 'frame', 'time'
and 'fps' in '( … )' expressions. Frames are written as out_0000.png …; --video also encodes them (MP4, WebM
or GIF through imageio-ffmpeg).
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

from ...compute.select import NAMES, select_backend
from ...core.animation.timeline import Timeline
from ...core.errors import StructuraError
from ...core.lang.diagnostics import ParseError
from ...core.project.model import SUFFIX
from ...core.project.model import load as load_project
from ...core.text_file import read_script
from ...render.animation import Animation, frame_path, render_frame
from ...render.output import save_image, to_display
from ...render.settings import AUTO_PASSES
from ...render.video import encode_video
from .common import EXIT_OK, EXIT_SCRIPT_ERROR, EXIT_USAGE, add_script_arguments, parse_params

HELP = "render an animation (a project's timeline; v2 'frame', 'time', 'fps' in expressions)"


def _range(text: str) -> range:
    start, _, stop = text.partition(":")
    return range(int(start), int(stop))


def register(p: argparse.ArgumentParser) -> None:
    add_script_arguments(p)
    p.add_argument("-o", "--output", type=Path, required=True, help="frame name pattern, e.g. frames/out.png")
    p.add_argument("--frames", type=_range, help="START:STOP (default: the project's timeline, else 0:24)")
    p.add_argument("--fps", type=float, help="frames per second (default: the timeline's, else 24)")
    p.add_argument("--size", default=None, help="WIDTHxHEIGHT (default: the script's)")
    p.add_argument("--samples", type=int, default=16)
    p.add_argument("--integrator", default=None)
    p.add_argument("--device", choices=NAMES, default="auto")
    p.add_argument("--video", type=Path, help="also encode the frames (.mp4 .webm .gif)")


def _overrides(args: argparse.Namespace) -> dict[str, Any]:
    out: dict[str, Any] = {"samples": args.samples, "samples_per_pass": AUTO_PASSES}
    if args.integrator:
        out["integrator"] = args.integrator
    if args.size:
        width, _, height = args.size.lower().partition("x")
        out |= {"width": int(width), "height": int(height)}
    return out


def animation_for(args: argparse.Namespace) -> Animation:
    """The animation of a script, or of a project (its timeline, seed, parameters and camera)."""
    overrides, params = _overrides(args), parse_params(args.param)
    if args.script.suffix.lower() == SUFFIX:
        project = load_project(args.script)
        timeline = project.timeline or Timeline()
        timeline = replace(timeline, fps=args.fps or timeline.fps)
        return Animation(project.text, timeline, project.seed or args.seed, {**project.params, **params},
                         args.script.parent, project.camera, {**project.render, **overrides})  # fmt: skip
    timeline = Timeline(fps=args.fps or 24.0, start=0, end=23)
    return Animation(read_script(args.script), timeline, args.seed, params, args.script.parent, None, overrides)


def run(args: argparse.Namespace) -> int:
    anim = animation_for(args)
    frames = args.frames if args.frames is not None else anim.frames()
    if not frames:
        print("animate: --frames must contain at least one frame", file=sys.stderr)
        return EXIT_USAGE
    backend = select_backend(args.device)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    images = []
    for frame in frames:
        try:
            result, settings = render_frame(anim, frame, backend)
        except (ParseError, StructuraError) as exc:
            print(f"{args.script}: frame {frame}: {getattr(exc, 'message', exc)}", file=sys.stderr)
            return EXIT_SCRIPT_ERROR
        path = frame_path(args.output, frame)
        save_image(result.image, path, 0.0, settings.view_transform)
        images.append(to_display(result.image, 0.0, settings.view_transform))
        print(f"\r  frame {frame} → {path.name}", end="", file=sys.stderr)
    print(file=sys.stderr)
    if args.video is not None:
        encode_video(args.video, images, anim.timeline.fps)
        print(f"wrote {args.video}")
    return EXIT_OK
