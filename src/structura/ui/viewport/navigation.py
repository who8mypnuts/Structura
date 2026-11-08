"""Mouse and keyboard navigation presets (docs/08 §7), shared by the GPU and the compute viewport.

| Action      | Structura (default)        | Legacy (Structure Synth 1.5) | Blender            |
|-------------|----------------------------|------------------------------|--------------------|
| Orbit       | LMB drag                   | LMB drag                     | MMB drag           |
| Pan         | MMB drag, Shift+LMB        | RMB drag, Ctrl+LMB           | Shift+MMB          |
| Zoom + roll | Alt+LMB                    | Shift+LMB, LMB+RMB           | Ctrl+MMB           |
| Fly         | RMB + WASD / QE            | —                            | —                  |
| Dolly       | wheel                      | wheel                        | wheel              |
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent

from .orbit import OrbitController

B, M = Qt.MouseButton, Qt.KeyboardModifier
FLY_KEYS = {Qt.Key.Key_W: (0, 0, 1), Qt.Key.Key_S: (0, 0, -1), Qt.Key.Key_A: (-1, 0, 0), Qt.Key.Key_D: (1, 0, 0),
            Qt.Key.Key_E: (0, 1, 0), Qt.Key.Key_Q: (0, -1, 0)}  # fmt: skip


def _structura(left: bool, middle: bool, right: bool, shift: bool, ctrl: bool, alt: bool) -> str | None:
    if middle or (left and shift):
        return "pan"
    if left and alt:
        return "zoom_roll"
    return "orbit" if left else "fly" if right else None


def _legacy(left: bool, middle: bool, right: bool, shift: bool, ctrl: bool, alt: bool) -> str | None:
    if (left and right) or (left and shift):
        return "zoom_roll"
    if right or (left and ctrl):
        return "pan"
    return "orbit" if left else None


def _blender(left: bool, middle: bool, right: bool, shift: bool, ctrl: bool, alt: bool) -> str | None:
    if not middle:
        return None
    return "pan" if shift else "zoom_roll" if ctrl else "orbit"


RULES = {"structura": _structura, "legacy": _legacy, "blender": _blender}
PRESETS = tuple(RULES)


def drag_action(preset: str, buttons: Qt.MouseButton, mods: Qt.KeyboardModifier) -> str | None:
    """'orbit', 'pan', 'zoom_roll', 'fly' or None for a drag with these buttons and modifiers."""
    pressed = (bool(buttons & b) for b in (B.LeftButton, B.MiddleButton, B.RightButton))
    held = (bool(mods & m) for m in (M.ShiftModifier, M.ControlModifier, M.AltModifier))
    return RULES.get(preset, _structura)(*pressed, *held)


class Navigator:
    """Turns mouse drags, the wheel and fly keys into OrbitController moves."""

    def __init__(self, orbit: OrbitController, preset: str = "structura") -> None:
        self.orbit, self.preset = orbit, preset
        self.last: QPoint | None = None
        self.action: str | None = None

    def press(self, event: QMouseEvent) -> None:
        self.last = event.position().toPoint()
        self.action = drag_action(self.preset, event.buttons(), event.modifiers())

    def move(self, event: QMouseEvent) -> bool:
        """True when the camera moved."""
        if self.last is None:
            return False
        pos = event.position().toPoint()
        dx, dy = pos.x() - self.last.x(), pos.y() - self.last.y()
        self.last = pos
        self.action = drag_action(self.preset, event.buttons(), event.modifiers()) or self.action
        if self.action == "pan":
            self.orbit.pan(dx, dy)
        elif self.action == "zoom_roll":
            self.orbit.dolly(-dy / 40.0)
            self.orbit.roll(dx * 0.005)
        elif self.action == "fly":
            self.orbit.look(dx, dy)
        elif self.action == "orbit":
            self.orbit.orbit(dx, dy)
        return self.action is not None

    def release(self) -> None:
        self.last, self.action = None, None

    def wheel(self, steps: float) -> None:
        self.orbit.dolly(steps)

    def key(self, event: QKeyEvent) -> bool:
        """WASD/QE while flying (the Structura preset, right button held); True when the camera moved."""
        move = FLY_KEYS.get(Qt.Key(event.key()))
        if move is None or self.action != "fly":
            return False
        self.orbit.fly(*move)
        return True


NUMPAD = {Qt.Key.Key_1: ("front", "back"), Qt.Key.Key_3: ("right", "left"), Qt.Key.Key_7: ("top", "bottom"),
          Qt.Key.Key_5: ("iso", "iso")}  # fmt: skip


def numpad_view(event: QKeyEvent) -> str | None:
    """Blender's keypad views: 1 front, 3 right, 7 top (Ctrl: the opposite side), 5 isometric."""
    if not event.modifiers() & Qt.KeyboardModifier.KeypadModifier:
        return None
    pair = NUMPAD.get(Qt.Key(event.key()))
    if pair is None:
        return None
    return pair[1] if event.modifiers() & Qt.KeyboardModifier.ControlModifier else pair[0]
