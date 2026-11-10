"""The post stack (PLAN F1): what turns the linear render into a finished picture besides exposure and the view
transform — bloom (light spilling around bright highlights and emitters), vignette, white balance, saturation,
contrast and a grading LUT. Applied when an image is shown or saved (render/output.Display), never to the
linear radiance itself (EXR files keep it untouched), so every change is live and free.

Order: bloom, vignette, temperature and saturation on linear light; then the view transform; then contrast and
the LUT on display values. Bloom adds intensity × the light above the threshold, spread by a Gaussian pyramid:
the energy it adds is exactly that, so a bloom never brightens what does not glow.

This module holds the settings: the looks, the render block's keys (``post_from_block``), and their command-line
spelling (one option per RANGES key: ``cli_option``, ``look_arguments``, shared by `structura render` and the
reproduce commands of reports). render/post_image.py holds the image operations."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any


@dataclass(frozen=True)
class PostSettings:
    """The post stack's settings; the defaults change nothing.

    Attributes:
        bloom: Intensity of the bloom: 0 off, 0.05 subtle, 0.3 neon.
        bloom_threshold: Linear luminance above which light blooms.
        bloom_radius: 0 a tight halo … 1 a wide glow (the weight of the coarse pyramid levels).
        vignette: How dark the corners get: 0 … 1.
        temperature: White balance: −1 cool (blue) … 1 warm (amber).
        saturation: 0 grey … 1 as rendered … 2 vivid.
        contrast: Contrast around mid grey, on display values (1 as rendered).
        lut: A .cube file, relative to the script's folder; "" for none.
    """

    bloom: float = 0.0
    bloom_threshold: float = 1.0
    bloom_radius: float = 0.5
    vignette: float = 0.0
    temperature: float = 0.0
    saturation: float = 1.0
    contrast: float = 1.0
    lut: str = ""

    @property
    def active(self) -> bool:
        """Whether any setting differs from the defaults (the stack then has work to do)."""
        return self != PostSettings()


RANGES: dict[str, tuple[float, float]] = {  # render-block values are clamped to these (catalog/v2_blocks.toml)
    "bloom": (0.0, 2.0),
    "bloom_threshold": (0.0, 100.0),
    "bloom_radius": (0.0, 1.0),
    "vignette": (0.0, 1.0),
    "temperature": (-1.0, 1.0),
    "saturation": (0.0, 2.0),
    "contrast": (0.0, 2.0),
}

LOOKS: dict[str, PostSettings] = {
    "Off": PostSettings(),
    "Subtle": PostSettings(bloom=0.04, vignette=0.15, saturation=1.05, contrast=1.05),
    "Neon": PostSettings(bloom=0.3, bloom_threshold=0.8, bloom_radius=0.7, saturation=1.2, contrast=1.1),
    "Cinematic": PostSettings(bloom=0.08, vignette=0.35, temperature=0.15, saturation=0.9, contrast=1.15),
    "Studio": PostSettings(vignette=0.1, contrast=1.08),
}


def look_named(name: str) -> PostSettings | None:
    """Finds a look by name, in any case ('neon' in a script, 'Neon' in the tool bar).

    Args:
        name: The look's name.

    Returns:
        Its settings, or None for an unknown name.
    """
    return next((post for key, post in LOOKS.items() if key.lower() == name.lower()), None)


def adjusted(base: PostSettings, values: Mapping[str, object]) -> PostSettings:
    """Changes some post settings.

    Args:
        base: The settings to start from.
        values: New values: numbers for RANGES keys (clamped to their range; other types are ignored) and a
            file name for 'lut'.

    Returns:
        ``base`` with the values over it.
    """
    changes: dict[str, Any] = {}
    for key, (low, high) in RANGES.items():
        value = values.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            changes[key] = min(high, max(low, float(value)))
    if values.get("lut"):
        changes["lut"] = str(values["lut"])
    return replace(base, **changes)


def post_from_block(block: Mapping[str, object]) -> PostSettings | None:
    """Reads the post stack of a v2 render block.

    Args:
        block: The block's entries.

    Returns:
        The block's 'look' (default: no look) with its single keys over it, or None when the block sets none of
        them.
    """
    base = look_named(str(block.get("look", "")))
    if base is None and not any(key in block for key in (*RANGES, "lut")):
        return None
    return adjusted(base or PostSettings(), block)


def cli_option(key: str) -> str:
    """Returns the command-line option of a post-stack key.

    Args:
        key: A RANGES key ('bloom_threshold' becomes '--bloom-threshold').
    """
    return "--" + key.replace("_", "-")


def look_arguments(post: PostSettings, script: PostSettings) -> list[str]:
    """Writes a look as command-line options (for reproduce commands).

    Args:
        post: The look the image was shown with.
        script: The script's own look (what `structura render` uses without options).

    Returns:
        [] when ``post`` is the script's look, '--look NAME' for a preset, else '--look off' and one option
        per setting that differs from the defaults.
    """
    if post == script:
        return []
    name = next((key.lower() for key, look in LOOKS.items() if look == post), None)
    if name is not None:
        return ["--look", name]
    default, args = PostSettings(), ["--look", "off"]
    for key in RANGES:
        if getattr(post, key) != getattr(default, key):
            args += [cli_option(key), f"{getattr(post, key):g}"]
    return args + (["--lut", post.lut] if post.lut else [])
