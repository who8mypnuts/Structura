"""Viewport navigation presets (docs/08 §7)."""

from __future__ import annotations

import numpy as np
import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent

from structura.core.scene.camera import Camera
from structura.ui.viewport.navigation import Navigator, drag_action
from structura.ui.viewport.orbit import OrbitController

B, M = Qt.MouseButton, Qt.KeyboardModifier
NONE = M.NoModifier


@pytest.mark.parametrize(
    ("preset", "buttons", "mods", "action"),
    [("structura", B.LeftButton, NONE, "orbit"), ("structura", B.MiddleButton, NONE, "pan"),
     ("structura", B.LeftButton, M.ShiftModifier, "pan"), ("structura", B.LeftButton, M.AltModifier, "zoom_roll"),
     ("structura", B.RightButton, NONE, "fly"),
     ("legacy", B.LeftButton, NONE, "orbit"), ("legacy", B.RightButton, NONE, "pan"),
     ("legacy", B.LeftButton, M.ControlModifier, "pan"), ("legacy", B.LeftButton | B.RightButton, NONE, "zoom_roll"),
     ("blender", B.LeftButton, NONE, None), ("blender", B.MiddleButton, NONE, "orbit"),
     ("blender", B.MiddleButton, M.ShiftModifier, "pan"), ("blender", B.MiddleButton, M.ControlModifier, "zoom_roll")],
)  # fmt: skip
def test_presets_map_buttons_to_actions(preset: str, buttons: object, mods: object, action: str | None) -> None:
    assert drag_action(preset, buttons, mods) == action  # type: ignore[arg-type]


def _mouse(kind: QMouseEvent.Type, pos: QPoint, buttons: Qt.MouseButton) -> QMouseEvent:
    return QMouseEvent(kind, QPointF(pos), QPointF(pos), Qt.MouseButton.NoButton, buttons, NONE)


def test_flying_turns_about_the_eye_and_wasd_moves_it(qapp: object) -> None:
    orbit = OrbitController(Camera((0.0, 0.0, 10.0), (0.0, 0.0, 0.0)))
    nav = Navigator(orbit)
    nav.press(_mouse(QMouseEvent.Type.MouseButtonPress, QPoint(0, 0), B.RightButton))
    nav.move(_mouse(QMouseEvent.Type.MouseMove, QPoint(40, 0), B.RightButton))
    assert np.allclose(orbit.camera().eye, (0.0, 0.0, 10.0)) and not np.allclose(orbit.camera().target, (0, 0, 0))
    before = np.asarray(orbit.camera().eye)
    assert nav.key(QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_W, NONE))
    moved = np.asarray(orbit.camera().eye) - before
    assert np.allclose(moved / np.linalg.norm(moved), orbit.forward) and np.isclose(np.linalg.norm(moved), 0.5)
    nav.release()
    assert not nav.key(QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_W, NONE))  # only while flying


def test_trackball_orbits_about_the_view_and_passes_the_poles() -> None:
    turntable, trackball = OrbitController(), OrbitController()
    trackball.trackball = True
    for orbit in (turntable, trackball):
        for _ in range(40):
            orbit.orbit(0, -10)  # a long vertical drag, in small moves
    assert abs(turntable.forward[1]) < 0.999  # stopped short of the pole
    assert not np.allclose(trackball.forward, turntable.forward)


@pytest.mark.parametrize(("key", "mods", "view"), [(Qt.Key.Key_1, M.KeypadModifier, "front"),
                                                   (Qt.Key.Key_7, M.KeypadModifier | M.ControlModifier, "bottom"),
                                                   (Qt.Key.Key_5, M.KeypadModifier, "iso"),
                                                   (Qt.Key.Key_1, NONE, None)])  # fmt: skip
def test_keypad_standard_views(qapp: object, key: Qt.Key, mods: object, view: str | None) -> None:
    from structura.ui.viewport.navigation import numpad_view  # noqa: PLC0415

    assert numpad_view(QKeyEvent(QKeyEvent.Type.KeyPress, key, mods)) == view  # type: ignore[arg-type]
