"""Timeline model: keys, interpolation, camera tracks, JSON (docs/16 §2)."""

from __future__ import annotations

import pytest

from structura.core.animation.camera import camera_at, has_camera_tracks, key_camera
from structura.core.animation.timeline import Interp, Timeline, from_dict, to_dict
from structura.core.scene.camera import Camera


def test_interpolation_modes_and_holds() -> None:
    tl = Timeline().set_key("param:a", 0, 0.0, Interp.LINEAR).set_key("param:a", 10, 10.0)
    assert tl.value("param:a", -5) == 0.0 and tl.value("param:a", 4) == pytest.approx(4.0)
    assert tl.value("param:a", 99) == 10.0
    smooth = tl.set_key("param:a", 0, 0.0, Interp.SMOOTH)
    assert smooth.value("param:a", 2) == pytest.approx(10 * (0.2**2 * (3 - 0.4)))  # eases in
    held = tl.set_key("param:a", 0, 0.0, Interp.CONSTANT)
    assert held.value("param:a", 9.9) == 0.0
    assert Timeline().set_key("seed", 0, 1).set_key("seed", 10, 11).value("seed", 5) == 1  # seeds step


def test_keys_replace_and_remove() -> None:
    tl = Timeline().set_key("param:a", 5, 1.0).set_key("param:a", 5, 2.0).set_key("param:b", 1, 3.0)
    assert [k.value for k in tl.track("param:a").keys] == [2.0]  # type: ignore[union-attr]
    assert tl.params_at(0) == {"a": 2.0, "b": 3.0} and tl.key_frames() == [1, 5]
    tl = tl.remove_key("param:a", 5)
    assert tl.track("param:a") is None and tl.remove_key("missing", 1) is tl


def test_camera_tracks() -> None:
    base = Camera((0.0, 0.0, 10.0), (0.0, 0.0, 0.0))
    tl = key_camera(Timeline(), 0, base)
    tl = key_camera(tl, 10, Camera((10.0, 0.0, 10.0), (0.0, 0.0, 0.0), fov_y_deg=40.0))
    tl = tl.set_key("camera:eye.x", 0, 0.0, Interp.LINEAR)
    mid = camera_at(tl, 5, base)
    assert mid.eye[0] == pytest.approx(5.0) and 22.0 < mid.fov_y_deg < 40.0 and has_camera_tracks(tl)
    assert camera_at(Timeline(), 5, base) == base and not has_camera_tracks(Timeline())


def test_json_round_trip_is_tolerant() -> None:
    tl = Timeline(30.0, 1, 48).set_key("param:a", 1, 0.5, Interp.CONSTANT).set_key("param:a", 48, 2.0)
    assert from_dict(to_dict(tl)) == tl
    assert from_dict({"tracks": [{"target": "param:x", "keys": [[0, 1, "bouncy"], "junk"]}]}).value("param:x", 3) == 1
    assert from_dict(None) == Timeline()
