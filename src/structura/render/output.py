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
from .post import PostSettings
from .post_image import apply_display, apply_linear
from .views import VIEW_TRANSFORMS

DISPLAY_FORMATS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}
FORMATS = DISPLAY_FORMATS | {".exr"}


def to_display(
    image: np.ndarray, exposure: float = 0.0, view: str = "soft", *, post: PostSettings | None = None,
    asset_dir: str = "",
) -> np.ndarray:  # fmt: skip
    """Turns linear HDR into 8-bit sRGB through the post stack and a view transform.

    Most callers use ``Display.apply``, which bundles these settings.

    Args:
        image: float linear RGB (H, W, 3).
        exposure: Exposure in stops.
        view: The view transform (unknown names use 'standard').
        post: The post stack; None or inactive skips it.
        asset_dir: The folder the post stack's LUT is relative to.

    Returns:
        uint8 sRGB (H, W, 3).
    """
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
    """How a linear image becomes a picture.

    Displays compare equal when they make the same picture, which tells whether an image made elsewhere (by a
    render job) is still the one wanted.

    Attributes:
        exposure: Exposure in stops.
        view: The view transform (render/views.py VIEW_TRANSFORMS).
        post: The post stack (bloom, vignette, grading).
        asset_dir: The folder the post stack's LUT is relative to (the script's).
    """

    exposure: float = 0.0
    view: str = "standard"
    post: PostSettings = field(default_factory=PostSettings)
    asset_dir: str = ""

    def apply(self, image: np.ndarray) -> np.ndarray:
        """Returns an image as uint8 sRGB with these settings.

        Args:
            image: float linear RGB (H, W, 3).
        """
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
) -> np.ndarray | None:
    """Writes an image.

    EXR keeps linear radiance (exposed, without the post stack) and any AOV ``layers``; the other formats get the
    display transform and ignore the layers. PNG files carry ``metadata`` as text chunks, EXR in its header.

    Args:
        image: float linear RGB (H, W, 3).
        path: The file; its suffix picks the format (FORMATS).
        display: Exposure, view transform and look (default: none, the standard view).
        metadata: Key → text entries to embed.
        layers: EXR channels by name (AOVs).

    Returns:
        The uint8 image written for a display format (reuse it: a video of the frames), None for EXR.

    Raises:
        ValueError: The suffix is not an image format Structura writes.
    """
    display = display or Display()
    suffix = path.suffix.lower()
    meta = dict(metadata or {})
    if suffix == ".exr":
        _save_exr(image * np.float32(2.0**display.exposure), path, meta, layers or {})
        return None
    if suffix not in DISPLAY_FORMATS:
        raise ValueError(f"unsupported image format '{suffix}' (use one of {sorted(FORMATS)})")
    rgb = display.apply(image)
    pil = Image.fromarray(rgb)
    if suffix == ".png":
        info = PngInfo()
        for key, value in meta.items():
            info.add_itxt(key, value)
        pil.save(path, pnginfo=info)
    else:
        pil.save(path)
    return rgb
