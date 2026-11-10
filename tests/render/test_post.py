"""The post stack (PLAN F1): bloom keeps energy, the look keys of the render block, LUTs, the Display."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from structura.core.lang.v2.block_check import known_keys
from structura.render.lut import apply_lut, parse_cube
from structura.render.output import Display, save_image
from structura.render.post import LOOKS, RANGES, PostSettings, adjusted, post_from_block
from structura.render.post_image import apply_linear, bloom_light


def _spot() -> np.ndarray:
    image = np.full((64, 96, 3), 0.1, np.float32)
    image[30:34, 46:50] = 20.0  # a small emitter far above the threshold
    return image


def _identity_cube(n: int = 5) -> str:
    steps = np.linspace(0.0, 1.0, n)
    rows = [f"{r:.6f} {g:.6f} {b:.6f}" for b in steps for g in steps for r in steps]
    return 'TITLE "identity"\nLUT_3D_SIZE {}\n{}\n'.format(n, "\n".join(rows))


def test_bloom_spreads_exactly_the_light_above_the_threshold() -> None:
    image = _spot()
    luma = image @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    above = float((image * (np.maximum(luma - 1.0, 0) / luma)[..., None]).sum())
    spread = bloom_light(image, 1.0, 0.5)
    assert spread.sum() == pytest.approx(above, rel=1e-4)
    assert spread[10, 10].sum() < spread[32, 48].sum()  # strongest at the emitter
    assert spread[32, 60].sum() > 0  # and it spills around it


def test_bloom_adds_intensity_times_that_light() -> None:
    image = _spot()
    bloomed = apply_linear(image, PostSettings(bloom=0.3))
    assert (bloomed - image).sum() == pytest.approx(0.3 * bloom_light(image, 1.0, 0.5).sum(), rel=1e-4)
    dim = np.full((16, 16, 3), 0.2, np.float32)
    np.testing.assert_allclose(apply_linear(dim, PostSettings(bloom=1.0)), dim)  # nothing glows: no change


def test_vignette_darkens_corners_only() -> None:
    out = apply_linear(np.ones((50, 80, 3), np.float32), PostSettings(vignette=0.5))
    assert out[25, 40, 0] == pytest.approx(1.0)
    assert out[0, 0, 0] == pytest.approx(0.5, abs=0.02)


def test_identity_lut_round_trips() -> None:
    lut = parse_cube(_identity_cube())
    rgb = np.random.default_rng(1).random((8, 8, 3)).astype(np.float32)
    np.testing.assert_allclose(apply_lut(rgb, lut), rgb, atol=1e-5)


def test_bad_cube_files_are_refused() -> None:
    with pytest.raises(ValueError, match="3D"):
        parse_cube("LUT_3D_SIZE 4\n0 0 0\n")


def test_lut_is_relative_to_the_script(tmp_path: Path) -> None:
    text = _identity_cube().replace(_identity_cube().splitlines()[2], "1 0 0")  # black → red
    (tmp_path / "grade.cube").write_text(text, encoding="utf-8")
    display = Display(0.0, "standard", PostSettings(lut="grade.cube"), str(tmp_path))
    black = display.apply(np.zeros((2, 2, 3), np.float32))
    assert tuple(black[0, 0]) == (255, 0, 0)


def test_render_block_looks() -> None:
    assert post_from_block({"samples": 4.0}) is None
    assert post_from_block({"look": "neon"}) == LOOKS["Neon"]
    post = post_from_block({"look": "Cinematic", "bloom": 9.0, "vignette": -1.0})
    assert post is not None
    assert (post.bloom, post.vignette, post.contrast) == (2.0, 0.0, LOOKS["Cinematic"].contrast)  # clamped
    assert adjusted(PostSettings(), {"lut": "a.cube"}).lut == "a.cube"


def test_catalog_ranges_match_the_clamps() -> None:
    keys = known_keys("render")
    for key, (low, high) in RANGES.items():
        assert keys[key] == f"{low:g}..{high:g}"
    assert keys["look"] == " | ".join(name.lower() for name in LOOKS)


def test_exr_keeps_radiance_without_the_look(tmp_path: Path) -> None:
    pytest.importorskip("OpenEXR")
    import OpenEXR  # noqa: PLC0415

    image = _spot()
    save_image(image, tmp_path / "a.exr", Display(1.0, "agx", LOOKS["Neon"]))
    with OpenEXR.File(str(tmp_path / "a.exr")) as f:
        rgb = f.channels()["RGB"].pixels
    np.testing.assert_allclose(rgb, image * 2.0)


def test_an_unreadable_lut_is_skipped_with_a_warning(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    (tmp_path / "broken.cube").write_text("LUT_3D_SIZE 4\n0 0 0\n", encoding="utf-8")
    grey = np.full((2, 2, 3), 0.18, np.float32)
    plain = Display(0.0, "standard").apply(grey)
    for name in ("missing.cube", "broken.cube"):
        shown = Display(0.0, "standard", PostSettings(lut=name), str(tmp_path)).apply(grey)
        np.testing.assert_array_equal(shown, plain)  # shown without the LUT instead of failing
    assert "missing.cube" in caplog.text and "broken.cube" in caplog.text


def test_luts_and_bloom_survive_odd_images() -> None:
    lut = parse_cube(_identity_cube())
    mapped = apply_lut(np.array([[np.nan, 0.5, 2.0]], np.float32), lut)  # a NaN pixel from a broken sample
    np.testing.assert_allclose(mapped, [[0.0, 0.5, 1.0]], atol=1e-5)
    for shape in ((1, 1, 3), (1, 7, 3), (3, 2, 3)):  # smaller than the pyramid
        image = np.full(shape, 5.0, np.float32)
        assert bloom_light(image, 1.0, 0.5).sum() == pytest.approx(image.sum() * 0.8, rel=1e-5)
