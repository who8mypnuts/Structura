"""`structura render FILE -o out.png` — build and render a still with the precision engine (docs/16 §5).

Settings come from the defaults, then the script's 'set raytracer::…' values, then the command line.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

from ...compute.base import BackendUnavailableError
from ...compute.select import NAMES, select_backend
from ...core.build.api import build_scene
from ...core.errors import StructuraError
from ...render.api import prepare_with_frame, progressive, script_settings
from ...render.denoise import METHODS, denoise_with
from ...render.denoise.oidn import OidnUnavailableError
from ...render.denoise.oidn import library as oidn_library
from ...render.metadata import render_metadata
from ...render.output import FORMATS, save_image
from ...render.settings import AUTO_PASSES, INTEGRATORS, VIEWS, RenderSettings
from .common import EXIT_OK, EXIT_SCRIPT_ERROR, EXIT_USAGE, add_script_arguments, compile_or_report, parse_params

HELP = "render a script to an image"
EXIT_DEVICE = 3


def _size(text: str) -> tuple[int, int]:
    width, _, height = text.lower().partition("x")
    return int(width), int(height)


def register(p: argparse.ArgumentParser) -> None:
    add_script_arguments(p)
    p.add_argument("-o", "--output", type=Path, required=True, help="image to write (.png .jpg .webp .tif .exr)")
    p.add_argument("--size", type=_size, help="WIDTHxHEIGHT (default: script 'raytracer::size' or 640x480)")
    p.add_argument("--samples", type=int, help="samples per pixel (default: script or 64)")
    p.add_argument("--integrator", choices=sorted(INTEGRATORS), help="default: the script's, else path")
    p.add_argument("--device", choices=NAMES, default="auto")
    p.add_argument("--frame", action="store_true", help="fit the structure instead of using the script camera")
    p.add_argument("--exposure", type=float, default=0.0, help="exposure in stops")
    p.add_argument("--tag-presets", action="store_true", help="tags named like a material preset use it (box::glass)")
    p.add_argument("--no-embed-script", action="store_true", help="do not store the script text in the image")
    p.add_argument("--view", choices=VIEWS, default="auto", help="view transform (auto: standard for classic)")
    p.add_argument("--aovs", action="store_true", help="EXR: add albedo, normal (N), depth (Z), alpha and id layers")
    p.add_argument("--noise-threshold", type=float, help="adaptive sampling: stop pixels below this error (0.01)")
    p.add_argument("--time-limit", type=float, help="stop after this many seconds")
    p.add_argument("--denoise", choices=METHODS, help="denoise the result (auto: Open Image Denoise, else À-Trous)")


def _overrides(args: argparse.Namespace) -> dict[str, Any]:
    out: dict[str, Any] = {
        "frame": args.frame,
        "seed": args.seed,
        "view": args.view,
        "aovs": args.aovs or bool(args.denoise),
    }
    if args.integrator:
        out["integrator"] = args.integrator
    if args.size:
        out["width"], out["height"] = args.size
    if args.samples:
        out["samples"] = args.samples
    for key in ("noise_threshold", "time_limit"):
        if getattr(args, key) is not None:
            out[key] = getattr(args, key)
    return out


def settings_for(scene: Any, args: argparse.Namespace) -> RenderSettings:
    settings = replace(script_settings(scene), **_overrides(args), asset_dir=str(args.script.resolve().parent))
    return replace(settings, samples_per_pass=AUTO_PASSES)


def _usage_error(args: argparse.Namespace) -> str | None:
    if args.output.suffix.lower() not in FORMATS:
        return f"unsupported output format '{args.output.suffix}' (use one of {sorted(FORMATS)})"
    if args.denoise == "oidn":
        try:
            oidn_library()
        except OidnUnavailableError as exc:
            return f"--denoise oidn: {exc} (use --denoise auto to fall back to À-Trous)"
    return None


def run(args: argparse.Namespace) -> int:
    if problem := _usage_error(args):
        print(problem, file=sys.stderr)
        return EXIT_USAGE
    compiled, text = compile_or_report(args)
    if compiled is None:
        return EXIT_SCRIPT_ERROR
    try:
        scene = build_scene(compiled.program, args.seed).scene
        backend = select_backend(args.device)
    except StructuraError as exc:
        print(f"{args.script}: error: {exc.message}", file=sys.stderr)
        return EXIT_SCRIPT_ERROR
    except BackendUnavailableError as exc:
        print(f"device error: {exc}", file=sys.stderr)
        return EXIT_DEVICE
    settings = settings_for(scene, args)
    prepared, frame = prepare_with_frame(scene, settings, args.tag_presets)
    print(f"rendering {len(scene)} objects on {backend.name} {backend.device_name}", file=sys.stderr)
    result = None
    for result in progressive(prepared, settings, backend, frame):
        print(f"\r  {result.samples}/{settings.samples} spp  {result.seconds:.1f}s", end="", file=sys.stderr)
    print(file=sys.stderr)
    assert result is not None
    metadata = render_metadata(settings, frame.camera, text, parse_params(args.param), not args.no_embed_script)
    image = result.image
    if args.denoise:
        image, method = denoise_with(image, result.aovs, args.denoise)
        print(f"  denoised ({method})", file=sys.stderr)
    layers = result.aovs.layers() if result.aovs is not None and args.aovs else None
    save_image(image, args.output, args.exposure, settings.view_transform, metadata, layers)
    print(f"wrote {args.output}")
    return EXIT_OK
