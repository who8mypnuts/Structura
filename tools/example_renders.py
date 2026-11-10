"""Reproducible example renders for the docs (docs/renders): the Structura v2 showcase with the path tracer,
and a few Structure Synth classics with the classic integrator and the path tracer side by side.

    PYTHONPATH=src:. python -m tools.example_renders [--size 640x400] [--samples 96] [--device auto] [NAME …]

Each image embeds its script, seed, camera and settings (File ▸ Open from Render reopens it); docs/renders/
README.md lists them with the settings used.
"""

from __future__ import annotations

import argparse
import time
from dataclasses import replace
from pathlib import Path

from structura import api
from structura.compute.select import select_backend
from structura.render.api import prepare_with_frame, progressive, script_settings
from structura.render.metadata import render_metadata
from structura.render.output import save_image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "renders"
RESOURCES = ROOT / "src" / "structura" / "resources"
V2 = sorted((RESOURCES / "examples" / "v2").glob("*.es"))
CLASSICS = [RESOURCES / "legacy" / "examples" / name for name in ("Default.es", "Nouveau.es", "City of Glass.es")]


def _slug(path: Path) -> str:
    return path.stem.lower().replace(" ", "-")


def render_one(script: Path, integrator: str | None, size: tuple[int, int], samples: int, device: str) -> str:
    """Renders one example into docs/renders.

    Args:
        script: The example script to render.
        integrator: The integrator, or None for the script's own.
        size: (width, height) in pixels.
        samples: Samples per pixel.
        device: The compute device.

    Returns:
        Its row of docs/renders/README.md.
    """
    text = script.read_text(encoding="utf-8")
    scene = api.build(script)
    settings = script_settings(scene)
    changes = {"width": size[0], "height": size[1], "samples": samples, "samples_per_pass": 0,
               "asset_dir": str(script.parent), "aovs": False}  # fmt: skip
    if integrator is not None:
        changes["integrator"] = integrator
    settings = replace(settings, **changes)
    started = time.perf_counter()
    prepared, frame = prepare_with_frame(scene, settings)
    *_, result = progressive(prepared, settings, select_backend(device), frame)
    seconds = time.perf_counter() - started
    name = f"{_slug(script)}-{settings.integrator}.png"
    save_image(result.image, OUT / name, settings.display, render_metadata(settings, frame.camera, text))
    look = "its look (render block)" if settings.post.active else "no look"
    print(f"{name}: {len(scene):,} objects, {seconds:.0f} s")
    return (f"| ![{script.stem}]({name}) | `{script.relative_to(RESOURCES).as_posix()}` | {settings.integrator}, "
            f"{samples} spp, {size[0]}×{size[1]}, {look}, {seconds:.0f} s |")  # fmt: skip


def main() -> None:
    """Renders the chosen examples (all by default) and, for a full run, writes docs/renders/README.md."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--size", default="640x400")
    parser.add_argument("--samples", type=int, default=96)
    parser.add_argument("--device", default="auto")
    parser.add_argument("names", nargs="*", help="only scripts whose name contains one of these")
    args = parser.parse_args()
    width, _, height = args.size.partition("x")
    size = (int(width), int(height))
    jobs = [(p, None) for p in V2] + [(p, i) for p in CLASSICS for i in ("classic", "path")]
    jobs = [(p, i) for p, i in jobs if not args.names or any(n.lower() in p.name.lower() for n in args.names)]
    OUT.mkdir(parents=True, exist_ok=True)
    rows = [render_one(p, i, size, args.samples, args.device) for p, i in jobs]
    header = ["# Example renders", "", "Made by `python -m tools.example_renders` (CPU or GPU give the same image). "
              "Each PNG embeds its script: File ▸ Open from Render reopens it.", "",
              "| Image | Script | Settings |", "|-------|--------|----------|"]  # fmt: skip
    if not args.names:
        (OUT / "README.md").write_text("\n".join([*header, *rows]) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
