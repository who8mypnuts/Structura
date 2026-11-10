"""Look options of `structura render` and `structura animate` (PLAN F1): the post stack from the command line.

--look neon   --bloom 0.2   --vignette 0.3   --temperature 0.2   --lut grade.cube

One option per post-stack number (render/post.py RANGES, documented by the language catalogue), so the command
line, the render block and the reproduce command of reports always offer the same keys. The options change
the saved 8-bit image (EXR keeps the linear radiance). `render` adjusts the script's own look
(render { look … bloom … }) unless --look replaces it; `animate` starts from --look, else no look.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from ...core.lang.catalog import v2_blocks
from ...render.post import LOOKS, RANGES, PostSettings, adjusted, cli_option, look_named


def add_post_arguments(p: argparse.ArgumentParser) -> None:
    """Adds --look, one option per post-stack number and --lut to a command's parser.

    Args:
        p: The parser of `structura render` or `structura animate`.
    """
    g = p.add_argument_group("look (bloom, vignette and grading of the saved image)")
    g.add_argument("--look", choices=[name.lower() for name in LOOKS], help="a finishing look (default: the script's)")
    docs = {key.name: key.doc for key in v2_blocks()["render"].keys}
    for key, (low, high) in RANGES.items():
        text = f"{low:g} … {high:g}: {docs[key]}".replace("%", "%%")  # (argparse formats help with %)
        g.add_argument(cli_option(key), dest=key, type=float, metavar="X", help=text)
    g.add_argument("--lut", type=Path, metavar="FILE", help="a 3D colour look-up table (.cube) applied last")


def post_override(args: argparse.Namespace, current: PostSettings) -> dict[str, Any]:
    """Reads the look options.

    Args:
        args: The parsed command line.
        current: The look to adjust when --look is not given (the script's own).

    Returns:
        {'post': the new PostSettings} when the options change the look, else {} (a RenderSettings update).
    """
    values = {key: getattr(args, key) for key in (*RANGES, "lut") if getattr(args, key) is not None}
    if "lut" in values:
        values["lut"] = str(Path(values["lut"]).resolve())
    if args.look is None and not values:
        return {}
    base = look_named(args.look) if args.look is not None else current
    return {"post": adjusted(base or PostSettings(), values)}
