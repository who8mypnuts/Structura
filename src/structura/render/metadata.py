"""Reproducibility metadata embedded in rendered images (docs/09 §8).

Stored as flat string key/values under the 'structura:' prefix: PNG tEXt/iTXt chunks and EXR header
attributes. ``read_metadata`` restores them from either format.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from .. import __version__
from ..core.project.model import Project, camera_from_dict
from ..core.scene.camera import Camera
from .settings import RenderSettings, render_param_specs

PREFIX = "structura:"


def render_metadata(
    settings: RenderSettings,
    camera: Camera,
    script: str | None = None,
    params: dict[str, float] | None = None,
    embed_script: bool = True,
) -> dict[str, str]:
    meta = {
        "version": __version__,
        "seed": str(settings.seed),
        "settings": json.dumps(asdict(settings), sort_keys=True),
        "camera": json.dumps(asdict(camera), sort_keys=True),
        "params": json.dumps(params or {}, sort_keys=True),
    }
    if script is not None:
        meta["script_sha256"] = hashlib.sha256(script.encode("utf-8")).hexdigest()
        if embed_script:
            meta["script"] = script
    return {PREFIX + k: v for k, v in meta.items()}


def read_metadata(path: Path) -> dict[str, str]:
    """The 'structura:' entries of a PNG or EXR written by Structura (prefix removed)."""
    if path.suffix.lower() == ".exr":
        import OpenEXR  # noqa: PLC0415 - only needed for EXR files

        with OpenEXR.File(str(path)) as f:
            items = {k: v for k, v in f.header().items() if isinstance(v, str)}
    else:
        from PIL import Image  # noqa: PLC0415

        with Image.open(path) as im:
            items = {k: str(v) for k, v in im.info.items() if isinstance(v, str)}
    return {k.removeprefix(PREFIX): v for k, v in items.items() if k.startswith(PREFIX)}


def project_from_metadata(meta: dict[str, str]) -> Project:
    """File ▸ Open from Render: the script, seed, parameters, camera and changed render settings stored in a
    render's metadata (the 'structura:' keys). Raises ValueError when the image carries no script."""
    if "script" not in meta:
        raise ValueError("the image has no embedded script (rendered with --no-embed-script, or not by Structura)")
    settings = json.loads(meta.get("settings", "{}"))
    defaults = asdict(RenderSettings())
    adjustable = {spec.key for spec in render_param_specs()}
    render = {k: v for k, v in settings.items() if k in adjustable and v != defaults.get(k)}
    params = {str(k): float(v) for k, v in json.loads(meta.get("params", "{}")).items()}
    camera = camera_from_dict(json.loads(meta.get("camera", "null")))
    return Project(text=meta["script"], seed=int(meta.get("seed", "0")), params=params, camera=camera, render=render)
