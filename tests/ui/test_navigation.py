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
     ("structura", B.LeftButton, M.ShiftModifier, "orbit"), ("structura", B.LeftButton, M.AltModifier, "zoom_roll"),
     ("structura", B.RightButton, NONE, "pan"), ("structura", B.RightButton, M.AltModifier, "look"),
     ("structura", B.LeftButton, M.ControlModifier, "orbit"),
     ("legacy", B.LeftButton, NONE, "orbit"), ("legacy", B.RightButton, NONE, "pan"),
     ("legacy", B.LeftButton, M.ControlModifier, "pan"), ("legacy", B.LeftButton | B.RightButton, NONE, "zoom_roll"),
     ("blender", B.LeftButton, NONE, None), ("blender", B.MiddleButton, NONE, "orbit"),
     ("blender", B.MiddleButton, M.ShiftModifier, "pan"), ("blender", B.MiddleButton, M.ControlModifier, "zoom_roll")],
)  # fmt: skip
def test_presets_map_buttons_to_actions(preset: str, buttons: object, mods: object, action: str | None) -> None:
    assert drag_action(preset, buttons, mods) == action  # type: ignore[arg-type]


def _mouse(
    kind: QMouseEvent.Type, pos: QPoint, buttons: Qt.MouseButton, mods: Qt.KeyboardModifier = NONE
) -> QMouseEvent:
    return QMouseEvent(kind, QPointF(pos), QPointF(pos), Qt.MouseButton.NoButton, buttons, mods)


def _drag(nav: Navigator, buttons: Qt.MouseButton, *points: tuple[int, int], mods: Qt.KeyboardModifier = NONE) -> None:
    nav.press(_mouse(QMouseEvent.Type.MouseButtonPress, QPoint(0, 0), buttons, mods))
    for x, y in points:
        nav.move(_mouse(QMouseEvent.Type.MouseMove, QPoint(x, y), buttons, mods))
    nav.release()


def test_looking_around_turns_about_the_eye_and_wasd_flies(qapp: object) -> None:
    orbit = OrbitController(Camera((0.0, 0.0, 10.0), (0.0, 0.0, 0.0)))
    nav = Navigator(orbit)
    nav.press(_mouse(QMouseEvent.Type.MouseButtonPress, QPoint(0, 0), B.RightButton, M.AltModifier))
    nav.move(_mouse(QMouseEvent.Type.MouseMove, QPoint(40, 0), B.RightButton, M.AltModifier))
    assert np.allclose(orbit.camera().eye, (0.0, 0.0, 10.0)) and not np.allclose(orbit.camera().target, (0, 0, 0))
    nav.release()
    before = np.asarray(orbit.camera().eye)
    assert nav.key(QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_W, NONE))  # whenever the viewport has the focus
    moved = np.asarray(orbit.camera().eye) - before
    assert np.allclose(moved / np.linalg.norm(moved), orbit.forward) and np.isclose(np.linalg.norm(moved), 0.5)
    before = np.asarray(orbit.camera().eye)
    assert nav.key(QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_W, M.ShiftModifier))  # Shift: a quarter step
    assert np.isclose(np.linalg.norm(np.asarray(orbit.camera().eye) - before), 0.125)
    nav.preset = "legacy"
    assert not nav.key(QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_W, NONE))  # 1.5 controls have no flying


def test_shift_slows_and_ctrl_locks_a_drag_to_one_axis(qapp: object) -> None:
    def orbited(mods: Qt.KeyboardModifier, *points: tuple[int, int]) -> np.ndarray:
        """The eye after a left drag through ``points`` with ``mods`` held."""
        orbit = OrbitController(Camera((0.0, 0.0, 10.0), (0.0, 0.0, 0.0)))
        _drag(Navigator(orbit), B.LeftButton, *points, mods=mods)
        return np.asarray(orbit.camera().eye)

    plain, slow = orbited(NONE, (40, 0)), orbited(M.ShiftModifier, (40, 0))
    assert abs(slow[0]) < abs(plain[0]) / 3  # a quarter of the turn
    diagonal = orbited(NONE, (30, 20))
    assert diagonal[0] != 0 and diagonal[1] != 0
    locked = orbited(M.ControlModifier, (6, 2), (30, 20))  # mostly horizontal: the eye stays level
    assert locked[0] != 0 and np.isclose(locked[1], 0.0)
    vertical = orbited(M.ControlModifier, (2, 6), (20, 30))
    assert np.isclose(vertical[0], 0.0) and vertical[1] != 0


def test_the_orbit_lock_constrains_every_drag(qapp: object) -> None:
    orbit = OrbitController(Camera((0.0, 0.0, 10.0), (0.0, 0.0, 0.0)))
    nav = Navigator(orbit)
    nav.lock = "horizontal"
    _drag(nav, B.LeftButton, (30, 30))
    assert np.isclose(orbit.camera().eye[1], 0.0) and orbit.camera().eye[0] != 0
    nav.lock = "vertical"
    _drag(nav, B.RightButton, (30, 30))  # pan, locked too
    assert np.isclose(orbit.camera().target[0], 0.0) and orbit.camera().target[1] != 0
    nav.wheel(1.0, M.ShiftModifier)
    assert orbit.distance > 10 * 0.88  # a slow wheel step


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
