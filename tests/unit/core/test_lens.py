"""The lens model (PLAN Q5): photographic conversions, the camera block, script round trips."""

from __future__ import annotations

import math

import pytest

from structura.core.lang.v2.blocks import extract_blocks
from structura.core.scene.camera import Camera
from structura.core.scene.camera_block import camera_from_block
from structura.core.scene.camera_script import camera_text
from structura.core.scene.lens import (
    Lens,
    amount_for_fstop,
    focal_length_mm,
    fov_for,
    fstop_for_amount,
    hyperfocal,
    parse_lens,
    pupil_radius,
    sensor_of,
)

FALLBACK = Camera((0.0, 0.0, 10.0), (0.0, 0.0, 0.0))


def test_focal_length_and_field_of_view_convert_exactly() -> None:
    assert fov_for(50.0) == pytest.approx(26.9915, abs=1e-3)  # a 50 mm lens on full frame, vertically
    for mm in (14.0, 35.0, 85.0, 200.0):
        assert focal_length_mm(fov_for(mm)) == pytest.approx(mm)
    assert focal_length_mm(fov_for(50.0, 15.6), 15.6) == pytest.approx(50.0)


def test_f_stops_make_apertures_and_hyperfocal_distances() -> None:
    lens = Lens(fstop=2.0)
    assert pupil_radius(lens, 50.0) == pytest.approx(0.0125)  # 50 mm / f/2 = 25 mm across
    assert pupil_radius(Lens(fstop=2.0, units_per_metre=100.0), 50.0) == pytest.approx(1.25)  # centimetre units
    h = hyperfocal(Lens(fstop=8.0), 50.0)
    assert h == pytest.approx(0.05**2 / (8.0 * Lens().coc_mm / 1000.0) + 0.05, rel=1e-9)  # f²/(N c) + f
    assert math.isinf(hyperfocal(Lens(), 50.0))  # a pinhole has no hyperfocal distance
    assert fstop_for_amount(0.0) == 22.0 and fstop_for_amount(1.0) == pytest.approx(1.2)
    assert amount_for_fstop(fstop_for_amount(0.37)) == pytest.approx(0.37)


def test_the_sharp_range_brackets_the_focus() -> None:
    camera = Camera((0.0, 0.0, 10.0), (0.0, 0.0, 0.0), lens=Lens(fstop=2.8)).with_focal_length(85.0)
    near, far = camera.sharp_range
    assert near < camera.focus < far and camera.focus == pytest.approx(10.0)
    hyper = camera.with_lens(focus_mode="hyperfocal")
    assert math.isinf(hyper.sharp_range[1]) and hyper.sharp_range[0] == pytest.approx(hyper.focus / 2, rel=0.01)
    assert Camera((0.0, 0.0, 10.0), (0.0, 0.0, 0.0)).sharp_range == (0.0, math.inf)


def test_lens_text_and_sensors_parse() -> None:
    assert parse_lens("85mm f/1.8") == (85.0, 1.8) and parse_lens("f2") == (None, 2.0)
    assert parse_lens("24mm") == (24.0, None) and parse_lens("50mm normal") == (50.0, None)
    with pytest.raises(ValueError, match="not a lens"):
        parse_lens("zoom")
    assert sensor_of("aps-c") == (23.6, 15.6) and sensor_of("36x24") == (36.0, 24.0) and sensor_of("huge") is None


def _block(text: str) -> Camera:
    extracted = extract_blocks(f"#version 2\n{text}\nbox\n")
    assert not extracted.diagnostics, extracted.diagnostics
    return camera_from_block(extracted.declarations.camera, FALLBACK)


def test_the_camera_block_speaks_photography() -> None:
    camera = _block('camera { position [0 2 12] lens "85mm f/1.8" focus hyperfocal sensor aps-c blades 7 }')
    assert camera.focal_length_mm == pytest.approx(85.0) and camera.lens.fstop == 1.8
    assert camera.lens.sensor_mm == (23.6, 15.6) and camera.lens.focus_mode == "hyperfocal" and camera.lens.blades == 7
    plain = _block("camera { position [0 2 12] fov 30 aperture 0.1 focus 8 shift [0 0.1] tilt [5 0] }")
    assert plain.fov_y_deg == 30.0 and plain.aperture_radius == 0.1 and plain.focus == 8.0
    assert plain.lens.shift == (0.0, 0.1) and plain.lens.tilt == (5.0, 0.0)


@pytest.mark.parametrize(
    "lens",
    [
        Lens(),
        Lens(
            fstop=2.8, focus_mode="manual", focus_distance=8.0, blades=6, units_per_metre=10.0, sensor_mm=(23.6, 15.6)
        ),
        Lens(aperture_radius=0.2, bokeh_bias=0.5, anamorphic=1.5, shift=(0.1, -0.05), tilt=(3.0, 0.0)),
        Lens(projection="orthographic", ortho_height=6.0),
        Lens(projection="fisheye", fisheye_fov_deg=200.0, fisheye_mapping="equisolid"),
    ],
)
def test_copy_camera_to_script_round_trips_the_lens(lens: Lens) -> None:
    camera = Camera((1.0, 2.0, 10.0), (0.0, 0.5, 0.0), (0.0, 1.0, 0.0), 30.0, lens)
    back = _block(camera_text(camera, v2=True))
    assert back.lens == lens
    if lens.projection == "perspective":
        assert back.fov_y_deg == pytest.approx(30.0, abs=1e-4)
