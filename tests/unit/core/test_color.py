"""QColor-compatible parsing/quantisation and the legacy HSV conversion (docs/06 §8)."""

from __future__ import annotations

import random

import numpy as np
import pytest

from structura.core.color import hsv_ints, hsv_to_rgb, parse_color
from structura.core.color.qcolor_compat import Rgba16, _raw_hsv, hsv_ints_array


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("#f80", Rgba16.from8(255, 136, 0)),
        ("#FF8800", Rgba16.from8(255, 136, 0)),
        ("#80ff8800", Rgba16.from8(255, 136, 0, 128)),
        ("red", Rgba16.from8(255, 0, 0)),
        ("Light Blue", Rgba16.from8(173, 216, 230)),
        ("transparent", Rgba16(0, 0, 0, 0)),
        ("#fff000fff", Rgba16(65535, 0, 65535)),
    ],
)
def test_parse_color_forms(text: str, expected: Rgba16) -> None:
    assert parse_color(text) == expected


@pytest.mark.parametrize("text", ["", "#12345", "#ggg", "notacolor", "123"])
def test_invalid_colors(text: str) -> None:
    assert parse_color(text) is None


def test_qt5_rounding_confirmed_by_original_engine() -> None:
    # Values observed from Structure Synth 1.5 (Qt 5.15 golden harness): firebrick → saturation 206,
    # #aa5705 → saturation 247 (Qt 6 would report 248 because it computes in single precision).
    assert hsv_ints(parse_color("firebrick")) == (0, 206, 178, 255)  # type: ignore[arg-type]
    assert hsv_ints(parse_color("#aa5705"))[1] == 247  # type: ignore[arg-type]
    assert hsv_ints(parse_color("#808080")) == (-1, 0, 128, 255)  # type: ignore[arg-type]


def _near_rounding_boundary(color: Rgba16) -> bool:
    _, sat16, _ = _raw_hsv(color)
    exact = (max(color.r, color.g, color.b) - min(color.r, color.g, color.b)) / max(1, color.r, color.g, color.b)
    return abs(exact * 65535 - round(exact * 65535)) > 0.499 or sat16 % 257 in (127, 128, 129)


def test_matches_pyside6_away_from_float_boundaries() -> None:
    qtgui = pytest.importorskip("PySide6.QtGui")
    rng = random.Random(7)
    for _ in range(3000):
        text = f"#{rng.randrange(1 << 24):06x}"
        ours = parse_color(text)
        assert ours is not None
        if _near_rounding_boundary(ours):
            continue
        q = qtgui.QColor(text).toHsv()
        assert hsv_ints(ours) == (q.hue(), q.saturation(), q.value(), q.alpha())


def test_vectorised_hsv_equals_scalar() -> None:
    rng = np.random.default_rng(3)
    pixels = rng.integers(0, 256, size=(5000, 3))
    expected = np.array([hsv_ints(Rgba16.from8(*map(int, p)))[:3] for p in pixels])
    assert (hsv_ints_array(pixels) == expected).all()


@pytest.mark.parametrize(
    ("hsv", "rgb"),
    [
        ((0.0, 1.0, 1.0), (1.0, 0.0, 0.0)),
        ((120.0, 1.0, 1.0), (0.0, 1.0, 0.0)),
        ((360.0, 1.0, 1.0), (1.0, 0.0, 0.0)),
        ((-1.0, 0.0, 0.5), (0.5, 0.5, 0.5)),
    ],
)
def test_legacy_hsv_to_rgb(hsv: tuple[float, float, float], rgb: tuple[float, float, float]) -> None:
    assert hsv_to_rgb(*hsv) == pytest.approx(rgb)
