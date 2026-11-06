"""Image output: exposure + view transform + encoding, with embedded metadata (docs/09 §7–8).

8-bit formats (PNG, JPEG, WebP, TIFF) get the display transform; EXR keeps linear float radiance.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo

from ..core.color import linear_to_srgb

LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)
DISPLAY_FORMATS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}
FORMATS = DISPLAY_FORMATS | {".exr"}


def _soft(image: np.ndarray) -> np.ndarray:
    """Gentle highlight roll-off: Reinhard on luminance above 0.8, hue preserved."""
    lum = image @ LUMA
    over = np.maximum(lum - 0.8, 0.0)
    knee = np.where(lum > 0.8, 0.8 + over / (1.0 + over / 0.6), lum)
    return image * (knee / np.maximum(lum, 1e-8))[..., None]


def to_display(image: np.ndarray, exposure: float = 0.0, view: str = "soft") -> np.ndarray:
    """Linear HDR → sRGB 8-bit. 'standard' clips (the Structure Synth look); 'soft' rolls highlights off."""
    scaled = image * np.float32(2.0**exposure)
    mapped = _soft(scaled) if view == "soft" else scaled
    return (linear_to_srgb(np.clip(mapped, 0.0, 1.0)) * 255.0 + 0.5).astype(np.uint8)


def _save_exr(image: np.ndarray, path: Path, metadata: Mapping[str, str]) -> None:
    import OpenEXR  # noqa: PLC0415 - heavy import, only for EXR output

    header = {"compression": OpenEXR.ZIP_COMPRESSION, "type": OpenEXR.scanlineimage, **metadata}
    with OpenEXR.File(header, {"RGB": np.ascontiguousarray(image, np.float32)}) as f:
        f.write(str(path))


def save_image(
    image: np.ndarray,
    path: Path,
    exposure: float = 0.0,
    view: str = "soft",
    metadata: Mapping[str, str] | None = None,
) -> None:
    suffix = path.suffix.lower()
    meta = dict(metadata or {})
    if suffix == ".exr":
        _save_exr(image * np.float32(2.0**exposure), path, meta)
        return
    if suffix not in DISPLAY_FORMATS:
        raise ValueError(f"unsupported image format '{suffix}' (use one of {sorted(FORMATS)})")
    pil = Image.fromarray(to_display(image, exposure, view))
    if suffix == ".png":
        info = PngInfo()
        for key, value in meta.items():
            info.add_itxt(key, value)
        pil.save(path, pnginfo=info)
    else:
        pil.save(path)


def save_png(image: np.ndarray, path: Path, exposure: float = 0.0, view: str = "soft") -> None:
    save_image(image, path, exposure, view)
