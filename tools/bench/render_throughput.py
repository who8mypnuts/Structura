"""Spike S2/S3: precision-engine throughput (docs/19 §2).

    python -m tools.bench.render_throughput --device cuda --size 1920x1080 --passes 8

Builds a ~1M-box binary tree (depth 20) and reports samples per second at the given size. The budget on
the reference GTX 1660 is ≥ 5 spp/s at 1080p (CUDA); on 8 CPU cores ≥ 1 spp/s.
"""

from __future__ import annotations

import argparse
import time

from structura.compute.select import NAMES, select_backend
from structura.core.build.api import build_scene
from structura.core.lang.api import compile_script
from structura.render.api import prepare, progressive
from structura.render.settings import RenderSettings

TREE = """
set maxdepth {depth}
set maxobjects 100000000
R
rule R {{ {{ x 0.6 rz 40 s 0.75 }} R {{ x 0.6 rz -40 s 0.75 }} R box }}
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", choices=NAMES, default="auto")
    ap.add_argument("--size", default="1920x1080")
    ap.add_argument("--depth", type=int, default=20)
    ap.add_argument("--passes", type=int, default=8)
    ap.add_argument("--integrator", default="path")
    args = ap.parse_args()
    width, height = (int(v) for v in args.size.split("x"))
    t0 = time.perf_counter()
    scene = build_scene(compile_script(TREE.format(depth=args.depth)).program).scene
    t1 = time.perf_counter()
    prepared = prepare(scene)
    t2 = time.perf_counter()
    backend = select_backend(args.device)
    settings = RenderSettings(
        width=width, height=height, samples=args.passes + 1, samples_per_pass=1, integrator=args.integrator, frame=True
    )
    print(
        f"{len(scene):,} objects: build {t1 - t0:.2f} s, pack+BVH {t2 - t1:.2f} s; {backend.name} {backend.device_name}"
    )
    stamps = [r.seconds for r in progressive(prepared, settings, backend)]
    warm = stamps[-1] - stamps[0]  # the first pass includes compilation and upload
    print(f"first pass {stamps[0]:.2f} s; {args.passes} warm passes {warm:.2f} s → {args.passes / warm:.2f} spp/s")


if __name__ == "__main__":
    main()
