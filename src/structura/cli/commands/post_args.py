"""Look options of `structura render` and `structura animate` (PLAN F1): the post stack from the command line.

--look neon   --bloom 0.2   --vignette 0.3   --lut grade.cube

They change the saved 8-bit image (EXR keeps the linear radiance). `render` adjusts the script's own look
(render { look … bloom … }) unless --look replaces it; `animate` starts from --look, else no look.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from ...render.post import LOOKS, PostSettings, adjusted, look_named

KEYS = ("bloom", "vignette", "lut")


def add_post_arguments(p: argparse.ArgumentParser) -> None:
    g = p.add_argument_group("look (bloom, vignette and grading of the saved image)")
    g.add_argument("--look", choices=[name.lower() for name in LOOKS], help="a finishing look (default: the script's)")
    g.add_argument("--bloom", type=float, metavar="X", help="bloom intensity: 0 off, 0.05 subtle, 0.3 neon")
    g.add_argument("--vignette", type=float, metavar="X", help="darken the corners: 0 … 1")
    g.add_argument("--lut", type=Path, metavar="FILE", help="a 3D colour look-up table (.cube) applied last")


def post_override(args: argparse.Namespace, current: PostSettings) -> dict[str, Any]:
    """{'post': …} for RenderSettings when the options change the look of ``current``; else {}."""
    values = {key: getattr(args, key) for key in KEYS if getattr(args, key) is not None}
    if "lut" in values:
        values["lut"] = str(Path(values["lut"]).resolve())
    if args.look is None and not values:
        return {}
    base = look_named(args.look) if args.look is not None else current
    return {"post": adjusted(base or PostSettings(), values)}
