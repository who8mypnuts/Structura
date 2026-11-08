"""The report's content, independent of the output format."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass(frozen=True)
class Row:
    label: str
    value: Any  # the raw value (JSON / CSV)
    text: str  # how people read it
    note: str = ""  # a short explanation of what the number means


@dataclass(frozen=True)
class Table:
    title: str
    columns: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class Section:
    key: str  # stable id (JSON)
    title: str
    rows: tuple[Row, ...] = ()
    tables: tuple[Table, ...] = ()


@dataclass(frozen=True)
class Swatch:
    hex: str
    share: float  # fraction of the image


@dataclass(frozen=True)
class Report:
    title: str
    subtitle: str
    created: str  # ISO 8601, local time with offset
    highlights: tuple[tuple[str, str], ...]  # "at a glance" cards: (label, value)
    sections: tuple[Section, ...]
    thumbnail: np.ndarray | None = None  # uint8 (H, W, 3) display image, at most THUMB_SIZE pixels wide
    histogram: np.ndarray | None = None  # float (BINS, 4): R, G, B, luminance of the display image, max 1
    palette: tuple[Swatch, ...] = field(default_factory=tuple)

    def section(self, key: str) -> Section:
        return next(s for s in self.sections if s.key == key)


def row(label: str, value: Any, text: str | None = None, note: str = "") -> Row:
    """A row whose text defaults to str(value)."""
    return Row(label, value, str(value) if text is None else text, note)
