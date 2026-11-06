"""Colour pools for 'color random' (docs/05 §6.2).

Every pool entry is pre-converted to QColor-quantised HSV integers (hue, sat 0..255, value 0..255) so the
kernel only draws indices. Pools: randomhue, greyscale/grayscale, randomrgb, image:FILE, list:C1,C2,…
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path

import numpy as np
from PIL import Image

from ...color import hsv_ints, parse_color
from ...color.qcolor_compat import hsv_ints_array


class PoolKind(IntEnum):
    RANDOM_HUE = 0
    GREYSCALE = 1
    RANDOM_RGB = 2
    IMAGE = 3
    LIST = 4


@dataclass
class PoolTable:
    kinds: list[int] = field(default_factory=list)
    starts: list[int] = field(default_factory=list)
    counts: list[int] = field(default_factory=list)
    widths: list[int] = field(default_factory=list)
    rows: list[np.ndarray] = field(default_factory=list)
    size: int = 0

    def add(self, kind: PoolKind, hsv: np.ndarray | None = None, width: int = 0) -> int:
        data = hsv if hsv is not None else np.zeros((0, 3), np.int32)
        self.kinds.append(int(kind))
        self.starts.append(self.size)
        self.counts.append(len(data))
        self.widths.append(width)
        self.rows.append(data)
        self.size += len(data)
        return len(self.kinds) - 1

    def hsv_table(self) -> np.ndarray:
        return np.concatenate(self.rows) if self.rows else np.zeros((0, 3), np.int32)


def _find_image(name: str, script_dir: Path | None) -> Path | None:
    candidates = [Path(name)] if Path(name).is_absolute() else [Path.cwd() / name]
    if script_dir is not None and not Path(name).is_absolute():
        candidates.insert(0, script_dir / name)
    for path in candidates:
        if path.exists():
            return path
        folder = path.parent
        if folder.is_dir():  # the script text is lower-cased by the tokenizer: match case-insensitively
            for entry in folder.iterdir():
                if entry.name.lower() == path.name.lower():
                    return entry
    return None


def _image_pool(table: PoolTable, name: str, script_dir: Path | None) -> tuple[int, str]:
    path = _find_image(name, script_dir)
    if path is None:
        return -1, f"Could not open file: {name}"
    try:
        image = Image.open(path).convert("RGB")
    except OSError:
        return -1, f"Could not parse image file: {path}"
    pixels = np.asarray(image, dtype=np.int32).reshape(-1, 3)  # row-major: index = y * width + x
    return table.add(PoolKind.IMAGE, hsv_ints_array(pixels), image.width), ""


def _list_pool(table: PoolTable, spec: str) -> tuple[int, str]:
    rows = []
    for name in spec.split(","):
        color = parse_color(name)
        if color is None:
            return -1, f"Could not parse color in colorlist: {spec}"
        rows.append(hsv_ints(color)[:3])
    return table.add(PoolKind.LIST, np.asarray(rows, dtype=np.int32)), ""


def parse_pool(value: str, script_dir: Path | None, table: PoolTable) -> tuple[int, str]:
    """Returns (pool index, error message)."""
    spec = value.lower()
    simple = {
        "randomhue": PoolKind.RANDOM_HUE,
        "greyscale": PoolKind.GREYSCALE,
        "grayscale": PoolKind.GREYSCALE,
        "randomrgb": PoolKind.RANDOM_RGB,
    }
    if spec in simple:
        return table.add(simple[spec]), ""
    if spec.startswith("image:"):
        return _image_pool(table, spec.removeprefix("image:"), script_dir)
    if spec.startswith("list:"):
        return _list_pool(table, spec.removeprefix("list:"))
    return -1, (
        "Could not understand the color pool: "
        + spec
        + ". Try: RandomHue, RandomRGB, GrayScale, Image:test.png, List:#234,Red,Blue"
    )
