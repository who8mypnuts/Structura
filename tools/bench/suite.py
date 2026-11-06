"""Owner benchmark suite (docs/18 §8, docs/19 §4): the performance budgets, measured on this machine.

    python -m tools.bench.suite                      # everything, 1M objects, JSON to bench-results.json
    python -m tools.bench.suite --objects 100000     # smaller (the sandbox / laptops)
    python -m tools.bench.suite --only build,render

Each benchmark prints its numbers and the budget; the JSON file is what the owner reports back.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from structura.compute.base import BackendUnavailableError
from structura.compute.select import select_backend
from structura.core.build.api import build_scene
from structura.core.lang.analysis import analyze
from structura.core.lang.api import compile_script
from structura.core.scene.ir import SceneIR
from structura.export.api import export_scene
from structura.render.api import prepare, progressive
from structura.render.settings import RenderSettings

GRID = "set maxobjects 100000000\n{n} * {{ x 1.1 }} {n} * {{ y 1.1 }} {m} * {{ z 1.1 }} box\n"
Result = dict[str, Any]


def grid(objects: int) -> str:
    side = max(1, round(objects ** (1 / 3)))
    return GRID.format(n=side, m=max(1, objects // (side * side)))


def timed(fn: Callable[[], Any]) -> tuple[Any, float]:
    started = time.perf_counter()
    value = fn()
    return value, time.perf_counter() - started


def bench_analysis(_: SceneIR, __: int) -> Result:
    text = "\n".join(f"rule R{i} {{ {{ x 1 rz {i % 90} }} R{i + 1} box }}" for i in range(1000)) + "\nR0\n"
    analyze(text)  # warm (imports, caches)
    _, seconds = timed(lambda: analyze(text))
    return {"lines": 1001, "seconds": round(seconds, 3), "budget": "< 0.1 s (docs/12 §6)"}


def bench_build(_: SceneIR, objects: int) -> Result:
    program = compile_script(grid(objects)).program
    build_scene(compile_script(grid(1000)).program)  # warm
    scene, seconds = timed(lambda: build_scene(program).scene)
    return {"objects": len(scene), "seconds": round(seconds, 3), "budget": "100k in < 0.3 s (G2, docs/06 §10.5)"}


def bench_bvh(scene: SceneIR, _: int) -> Result:
    prepare(build_scene(compile_script(grid(1000)).program).scene)  # warm the packing and BVH kernels
    _, seconds = timed(lambda: prepare(scene))
    return {"objects": len(scene), "seconds": round(seconds, 3), "budget": "1M in < 3 s (docs/09 §3.2)"}


def bench_render(scene: SceneIR, _: int) -> Result:
    prepared, out = prepare(scene), {}
    settings = RenderSettings(width=1920, height=1080, samples=9, samples_per_pass=1, integrator="path", frame=True)
    for device in ("cuda", "opencl", "wgpu", "cpu"):
        try:
            backend = select_backend(device)
        except BackendUnavailableError as exc:
            out[device] = f"unavailable: {exc}"
            continue
        stamps = [r.seconds for r in progressive(prepared, settings, backend)]
        out[device] = {"device": backend.device_name, "first_pass_s": round(stamps[0], 3),
                       "spp_per_s_1080p": round(8 / max(stamps[-1] - stamps[0], 1e-9), 2)}  # fmt: skip
    out["budget"] = "GTX 1660 CUDA ≥ 5 spp/s at 1080p; 8 CPU cores ≥ 1 spp/s (docs/09 §1)"
    return out


def bench_export(scene: SceneIR, _: int) -> Result:
    out: Result = {"budget": "1M → .usdc < 3 s (docs/15 §8)"}
    with tempfile.TemporaryDirectory() as tmp:
        for suffix in (".usdc", ".glb", ".obj"):
            _, seconds = timed(lambda s=suffix: export_scene(scene, Path(tmp) / f"bench{s}"))
            out[suffix] = round(seconds, 3)
    return out


def bench_viewport(scene: SceneIR, _: int) -> Result:
    import moderngl  # noqa: PLC0415

    from structura.core.scene.camera import Camera, framed  # noqa: PLC0415
    from structura.preview.instances import preview_scene  # noqa: PLC0415
    from structura.preview.options import PreviewOptions  # noqa: PLC0415
    from structura.preview.renderer import PreviewRenderer  # noqa: PLC0415

    ctx = moderngl.create_standalone_context(require=330)
    renderer, ps = PreviewRenderer(ctx), preview_scene(scene)
    renderer.set_scene(ps)
    camera = framed(Camera((0.0, 0.0, 10.0), (0.0, 0.0, 0.0)), ps.lo, ps.hi, 16 / 9)
    fbo = ctx.framebuffer([ctx.texture((1920, 1080), 4)], ctx.depth_renderbuffer((1920, 1080)))
    renderer.render(camera, fbo, (1920, 1080), PreviewOptions(), accumulate=False)
    ctx.finish()
    frames = 30
    _, seconds = timed(lambda: [renderer.render(camera, fbo, (1920, 1080), PreviewOptions(), accumulate=False)
                                for _ in range(frames)] and ctx.finish())  # fmt: skip
    return {"renderer": ctx.info["GL_RENDERER"], "fps_1080p": round(frames / seconds, 1),
            "budget": "≥ 45 fps at 1M, ≥ 20 fps at 5M on the GTX 1660 (G3)"}  # fmt: skip


def bench_cold_start(_: SceneIR, __: int) -> Result:
    code = "import time; t = time.perf_counter(); import structura.ui.app_window; print(time.perf_counter() - t)"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout
    return {"import_ui_s": round(float(out), 3), "budget": "window interactive < 2.5 s with warm caches"}


BENCHES = {"analysis": bench_analysis, "build": bench_build, "bvh": bench_bvh, "render": bench_render,
           "export": bench_export, "viewport": bench_viewport, "cold_start": bench_cold_start}  # fmt: skip


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--objects", type=int, default=1_000_000)
    ap.add_argument("--only", default=",".join(BENCHES))
    ap.add_argument("--out", type=Path, default=Path("bench-results.json"))
    args = ap.parse_args()
    scene = build_scene(compile_script(grid(args.objects)).program).scene
    results: Result = {"machine": platform.platform(), "python": sys.version.split()[0], "objects": len(scene)}
    for name in args.only.split(","):
        try:
            results[name] = BENCHES[name](scene, args.objects)
        except Exception as exc:  # one failing benchmark must not hide the others
            results[name] = f"failed: {exc}"
        print(f"{name:>10}: {results[name]}", flush=True)
    args.out.write_text(json.dumps(results, indent=2))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
