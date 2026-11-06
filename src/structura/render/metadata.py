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
from ..core.scene.camera import Camera
from .settings import RenderSettings

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
