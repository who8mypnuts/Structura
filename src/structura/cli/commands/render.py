"""`structura render FILE -o out.png` — build and render a still with the precision engine (docs/16 §5).

Settings come from the defaults, then the script's 'set raytracer::…' values, then the command line.
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from ...compute.base import Backend, BackendUnavailableError
from ...compute.select import NAMES, select_backend
from ...core.build.api import BuildResult, build_scene
from ...core.build.driver import BuildStats
from ...core.errors import StructuraError
from ...core.scene.camera import Camera
from ...core.scene.ir import SceneIR
from ...render.api import RenderProgress, prepare_with_frame, progressive, script_settings
from ...render.denoise import METHODS, denoise_with
from ...render.denoise.oidn import OidnUnavailableError
from ...render.denoise.oidn import library as oidn_library
from ...render.details import RenderDetails, render_details
from ...render.metadata import render_metadata
from ...render.output import FORMATS, save_image
from ...render.report.collect import ReportInputs, build_report
from ...render.report.writers import FORMATS as REPORT_FORMATS
from ...render.settings import AUTO_PASSES, BUCKET_ORDERS, INTEGRATORS, SAMPLERS, SEQUENCES, VIEWS, RenderSettings
from ...services.report_documents import write_report
from .common import EXIT_OK, EXIT_SCRIPT_ERROR, EXIT_USAGE, add_script_arguments, compile_or_report, parse_params
from .lens_args import add_lens_arguments, apply_lens_arguments
from .post_args import add_post_arguments, post_override

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
    p.add_argument("--exposure", type=float, help="exposure in stops (default: the script's, else 0)")
    p.add_argument("--tag-presets", action="store_true", help="tags named like a material preset use it (box::glass)")
    p.add_argument("--no-embed-script", action="store_true", help="do not store the script text in the image")
    p.add_argument(
        "--view", choices=VIEWS, help="view transform (default: the script's, else auto: AgX, standard for classic)"
    )
    p.add_argument("--aovs", action="store_true", help="EXR: add albedo, normal (N), depth (Z), alpha and id layers")
    p.add_argument("--noise-threshold", type=float, help="adaptive sampling: stop pixels below this error (0.01)")
    p.add_argument("--sampler", choices=SAMPLERS, help="progressive (whole image in passes) or tiled (buckets)")
    p.add_argument("--bucket-order", choices=BUCKET_ORDERS, help="tiled: the order of the buckets (hilbert)")
    p.add_argument("--sequence", choices=SEQUENCES, help="sample numbers: random (default) or halton")
    p.add_argument("--time-limit", type=float, help="stop after this many seconds")
    p.add_argument(
        "--denoise",
        choices=("off", *METHODS),
        help="denoise the result (auto: Open Image Denoise, else À-Trous; default: the script's)",
    )
    p.add_argument("--report", type=Path, action="append", default=[], metavar="FILE",
                   help="also write a render report (.pdf .html .md .txt .json .csv .odt); repeatable")  # fmt: skip
    add_lens_arguments(p)
    add_post_arguments(p)


def _overrides(args: argparse.Namespace) -> dict[str, Any]:
    out: dict[str, Any] = {"frame": args.frame, "seed": args.seed}
    for key in ("view", "exposure", "denoise"):
        if getattr(args, key) is not None:
            out[key] = getattr(args, key)
    if args.integrator:
        out["integrator"] = args.integrator
    if args.size:
        out["width"], out["height"] = args.size
    if args.samples:
        out["samples"] = args.samples
    for key in ("noise_threshold", "time_limit", "sampler", "bucket_order", "sequence"):
        if getattr(args, key) is not None:
            out[key] = getattr(args, key)
    return out


def denoiser(settings: RenderSettings) -> str | None:
    """The denoising method the command line or the script asks for (None: none)."""
    return settings.denoise if settings.denoise not in ("", "off") else None


def settings_for(scene: Any, args: argparse.Namespace) -> RenderSettings:
    settings = replace(script_settings(scene), **_overrides(args), asset_dir=str(args.script.resolve().parent))
    settings = replace(settings, **post_override(args, settings.post))
    aovs = settings.aovs or args.aovs or denoiser(settings) is not None  # the denoiser is guided by the AOVs
    return replace(settings, samples_per_pass=AUTO_PASSES, aovs=aovs)


def _usage_error(args: argparse.Namespace) -> str | None:
    if args.output.suffix.lower() not in FORMATS:
        return f"unsupported output format '{args.output.suffix}' (use one of {sorted(FORMATS)})"
    for report in args.report:
        if report.suffix.lower() not in REPORT_FORMATS:
            return f"unsupported report format '{report.suffix}' (use one of {', '.join(REPORT_FORMATS)})"
    try:
        apply_lens_arguments(Camera((0.0, 0.0, 1.0), (0.0, 0.0, 0.0)), args)
    except ValueError as exc:
        return str(exc)
    if args.denoise == "oidn":
        try:
            oidn_library()
        except OidnUnavailableError as exc:
            return f"--denoise oidn: {exc} (use --denoise auto to fall back to À-Trous)"
    return None


@dataclass
class _Rendered:
    scene: SceneIR
    build: BuildStats
    settings: RenderSettings
    result: RenderProgress
    details: RenderDetails
    device: str
    passes: int


def _render(build: BuildResult, args: argparse.Namespace, backend: Backend) -> _Rendered:
    settings = settings_for(build.scene, args)
    started = time.perf_counter()
    prepared, frame = prepare_with_frame(build.scene, settings, args.tag_presets)
    frame = replace(frame, camera=apply_lens_arguments(frame.camera, args))
    details = render_details(prepared, frame, time.perf_counter() - started, backend.details())
    print(f"rendering {len(build.scene)} objects on {backend.name} {backend.device_name}", file=sys.stderr)
    result, passes = None, 0
    for passes, result in enumerate(progressive(prepared, settings, backend, frame), 1):  # noqa: B007
        print(f"\r  {result.samples}/{settings.samples} spp  {result.seconds:.1f}s", end="", file=sys.stderr)
    print(file=sys.stderr)
    assert result is not None
    device = f"{backend.name} {backend.device_name}".strip()
    return _Rendered(build.scene, build.stats, settings, result, details, device, passes)


def _write_reports(r: _Rendered, args: argparse.Namespace, text: str, image: Any, method: str) -> None:
    inputs = ReportInputs(
        scene=r.scene, progress=r.result, details=r.details, device=r.device, passes=r.passes, image=image,
        denoiser=method, script=text, script_path=args.script.resolve(), seed=args.seed,
        params=parse_params(args.param), build=r.build, outputs=(args.output.resolve(),),
    )  # fmt: skip
    report = build_report(inputs)
    for path in args.report:
        for written in write_report(report, path):
            print(f"wrote {written}")


def run(args: argparse.Namespace) -> int:
    if problem := _usage_error(args):
        print(problem, file=sys.stderr)
        return EXIT_USAGE
    compiled, text = compile_or_report(args)
    if compiled is None:
        return EXIT_SCRIPT_ERROR
    try:
        build = build_scene(compiled.program, args.seed)
        backend = select_backend(args.device)
    except StructuraError as exc:
        print(f"{args.script}: error: {exc.message}", file=sys.stderr)
        return EXIT_SCRIPT_ERROR
    except BackendUnavailableError as exc:
        print(f"device error: {exc}", file=sys.stderr)
        return EXIT_DEVICE
    r = _render(build, args, backend)
    metadata = render_metadata(r.settings, r.details.camera, text, parse_params(args.param), not args.no_embed_script)
    image, method = r.result.image, ""
    if (wanted := denoiser(r.settings)) is not None:
        try:
            image, method = denoise_with(image, r.result.aovs, wanted)
        except OidnUnavailableError as exc:  # the script asked for OIDN (the command line is checked up front)
            print(f"  Open Image Denoise unavailable ({exc}); using À-Trous", file=sys.stderr)
            image, method = denoise_with(image, r.result.aovs, "atrous")
        print(f"  denoised ({method})", file=sys.stderr)
    layers = r.result.aovs.layers() if r.result.aovs is not None and args.aovs else None
    save_image(image, args.output, r.settings.display, metadata, layers)
    print(f"wrote {args.output}")
    if args.report:
        _write_reports(r, args, text, image, method)
    return EXIT_OK
