"""Image output: exposure + post stack + view transform + encoding, with embedded metadata (docs/09 §7–8).

8-bit formats (PNG, JPEG, WebP, TIFF) get the display transform; EXR keeps linear float radiance (the post stack
is a look for display, render/post.py).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo

from ..core.color import linear_to_srgb
from .post import PostSettings, apply_display, apply_linear
from .views import VIEW_TRANSFORMS

DISPLAY_FORMATS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}
FORMATS = DISPLAY_FORMATS | {".exr"}


def to_display(
    image: np.ndarray, exposure: float = 0.0, view: str = "soft", *, post: PostSettings | None = None,
    asset_dir: str = "",
) -> np.ndarray:  # fmt: skip
    """Linear HDR → sRGB 8-bit through the post stack and a view transform (render/views.py)."""
    scaled = image * np.float32(2.0**exposure)
    if post is not None and post.active:
        scaled = apply_linear(scaled, post)
    mapped = VIEW_TRANSFORMS.get(view, VIEW_TRANSFORMS["standard"])(scaled)
    shown = linear_to_srgb(np.clip(mapped, 0.0, 1.0).astype(np.float32))
    if post is not None and post.active:
        shown = apply_display(shown, post, asset_dir)
    return (np.clip(shown, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)


@dataclass(frozen=True)
class Display:
    """How a linear image becomes a picture: exposure (stops), the view transform and the post stack (with the
    folder its LUT is relative to). Compared to tell whether an image made elsewhere is still the one wanted."""

    exposure: float = 0.0
    view: str = "standard"
    post: PostSettings = field(default_factory=PostSettings)
    asset_dir: str = ""

    def apply(self, image: np.ndarray) -> np.ndarray:
        return to_display(image, self.exposure, self.view, post=self.post, asset_dir=self.asset_dir)


def _save_exr(image: np.ndarray, path: Path, metadata: Mapping[str, str], layers: Mapping[str, np.ndarray]) -> None:
    """Float EXR; extra ``layers`` (AOVs) become channels like 'albedo.R' or 'Z'."""
    import OpenEXR  # noqa: PLC0415 - heavy import, only for EXR output

    header = {"compression": OpenEXR.ZIP_COMPRESSION, "type": OpenEXR.scanlineimage, **metadata}
    channels = {"RGB": np.ascontiguousarray(image, np.float32)}
    channels |= {name: np.ascontiguousarray(np.nan_to_num(v, posinf=1e30), np.float32) for name, v in layers.items()}
    with OpenEXR.File(header, channels) as f:
        f.write(str(path))


def save_image(
    image: np.ndarray,
    path: Path,
    display: Display | None = None,
    metadata: Mapping[str, str] | None = None,
    layers: Mapping[str, np.ndarray] | None = None,
) -> None:
    """Write an image; EXR keeps linear radiance (exposed, without the post stack) and any AOV ``layers`` (other
    formats ignore them)."""
    display = display or Display()
    suffix = path.suffix.lower()
    meta = dict(metadata or {})
    if suffix == ".exr":
        _save_exr(image * np.float32(2.0**display.exposure), path, meta, layers or {})
        return
    if suffix not in DISPLAY_FORMATS:
        raise ValueError(f"unsupported image format '{suffix}' (use one of {sorted(FORMATS)})")
    pil = Image.fromarray(display.apply(image))
    if suffix == ".png":
        info = PngInfo()
        for key, value in meta.items():
            info.add_itxt(key, value)
        pil.save(path, pnginfo=info)
    else:
        pil.save(path)
