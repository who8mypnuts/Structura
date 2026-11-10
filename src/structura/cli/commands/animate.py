"""`structura animate FILE -o frames/out.png [--frames 0:48] [--fps 24] [--video out.mp4] [--turntable [S]]`
(docs/16 §2, §5).

FILE is a script or a .structura project. A project brings its timeline (keyed parameters, seed and camera;
the default frame range and fps), parameter values, seed and camera. v2 scripts can also read 'frame', 'time'
and 'fps' in '( … )' expressions. Frames are written as out_0000.png …; --video also encodes them (MP4, WebM
or GIF through imageio-ffmpeg). --turntable orbits the camera in a seamless loop instead (PLAN F2).
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

from ...api import open as open_document
from ...compute.select import NAMES, select_backend
from ...core.animation.paths import Turntable
from ...core.animation.timeline import Timeline
from ...core.errors import StructuraError
from ...core.lang.diagnostics import ParseError
from ...core.project.model import SUFFIX
from ...render.animation import Animation, frame_path, render_frame, with_turntable
from ...render.output import save_image
from ...render.post import PostSettings
from ...render.settings import AUTO_PASSES
from ...render.video import encode_video
from .common import EXIT_OK, EXIT_SCRIPT_ERROR, EXIT_USAGE, add_script_arguments, parse_params
from .post_args import add_post_arguments, post_override

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
    p.add_argument("--turntable", type=float, nargs="?", const=5.0, metavar="SECONDS",
                   help="orbit the camera in a seamless loop of SECONDS (default 5); replaces camera keys")  # fmt: skip
    p.add_argument("--turns", type=float, default=1.0, help="--turntable: full turns in the loop (default 1)")
    p.add_argument("--ease", action="store_true", help="--turntable: start and stop gently (not a loop)")
    p.add_argument("--zoom", type=float, default=1.0, help="--turntable: the distance at the end, e.g. 0.7")
    add_post_arguments(p)


def _overrides(args: argparse.Namespace) -> dict[str, Any]:
    out: dict[str, Any] = {"samples": args.samples, "samples_per_pass": AUTO_PASSES}
    out |= post_override(args, PostSettings())
    if args.integrator:
        out["integrator"] = args.integrator
    if args.size:
        width, _, height = args.size.lower().partition("x")
        out |= {"width": int(width), "height": int(height)}
    return out


def animation_for(args: argparse.Namespace) -> Animation:
    """The animation of a script, or of a project (its timeline, seed, parameters and camera)."""
    overrides, params = _overrides(args), parse_params(args.param)
    doc = open_document(args.script)
    project = args.script.suffix.lower() == SUFFIX
    timeline = doc.timeline if project else Timeline(start=0, end=23)
    timeline = replace(timeline, fps=args.fps or timeline.fps)
    seed = (doc.seed or args.seed) if project else args.seed
    anim = Animation(doc.text, timeline, seed, {**doc.params, **params}, args.script.parent, doc.camera,
                     {**doc.render_overrides, **overrides})  # fmt: skip
    if args.turntable is not None:
        frames = max(2, round(args.turntable * timeline.fps))
        anim = with_turntable(anim, Turntable(frames, args.turns, start=timeline.start, ease=args.ease, zoom=args.zoom))
    return anim


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
        save_image(result.image, path, settings.display)
        images.append(settings.display.apply(result.image))
        print(f"\r  frame {frame} → {path.name}", end="", file=sys.stderr)
    print(file=sys.stderr)
    if args.video is not None:
        encode_video(args.video, images, anim.timeline.fps)
        print(f"wrote {args.video}")
    return EXIT_OK
