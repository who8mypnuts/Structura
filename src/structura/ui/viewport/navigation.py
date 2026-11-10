"""Mouse and keyboard navigation presets (docs/08 §7), shared by the GPU and the compute viewport.

| Action        | Structura (default)                  | Legacy (Structure Synth 1.5) | Blender     |
|---------------|--------------------------------------|------------------------------|-------------|
| Orbit         | LMB drag                             | LMB drag                     | MMB drag    |
| Pan           | MMB or RMB drag                      | RMB drag, Ctrl+LMB           | Shift+MMB   |
| Zoom + roll   | Alt+LMB                              | Shift+LMB, LMB+RMB           | Ctrl+MMB    |
| Look around   | Alt+RMB                              | —                            | —           |
| Fly           | W A S D / Q E (the viewport focused) | —                            | —           |
| Dolly         | wheel                                | wheel                        | wheel       |
| Slow (¼)      | Shift while dragging or wheeling     | Shift + wheel                | Shift + wheel |
| One axis      | Ctrl while orbiting or panning       | —                            | —           |
| Context menu  | right-click                          | right-click                  | right-click |

An **orbit lock** (free, horizontal, vertical — View ▸ Orbit Lock, or the viewport menu) constrains every
orbit and pan the same way Ctrl does for one drag."""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent

from .orbit import OrbitController

B, M = Qt.MouseButton, Qt.KeyboardModifier
FLY_KEYS = {Qt.Key.Key_W: (0, 0, 1), Qt.Key.Key_S: (0, 0, -1), Qt.Key.Key_A: (-1, 0, 0), Qt.Key.Key_D: (1, 0, 0),
            Qt.Key.Key_E: (0, 1, 0), Qt.Key.Key_Q: (0, -1, 0)}  # fmt: skip
SLOW = 0.25  # the Shift factor
LOCK_SLOP = 4  # pixels of drag before Ctrl decides which axis a drag is locked to
LOCKS = ("free", "horizontal", "vertical")  # orbit lock choices (View ▸ Orbit Lock)


def _structura(left: bool, middle: bool, right: bool, shift: bool, ctrl: bool, alt: bool) -> str | None:
    if alt:
        return "zoom_roll" if left else "look" if right else None
    if middle or right:
        return "pan"
    return "orbit" if left else None


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
MODIFIER_KEYS = {"structura"}  # presets whose Shift (slow) and Ctrl (one axis) are free for the modifiers above


def drag_action(preset: str, buttons: Qt.MouseButton, mods: Qt.KeyboardModifier) -> str | None:
    """'orbit', 'pan', 'zoom_roll', 'look' or None for a drag with these buttons and modifiers."""
    pressed = (bool(buttons & b) for b in (B.LeftButton, B.MiddleButton, B.RightButton))
    held = (bool(mods & m) for m in (M.ShiftModifier, M.ControlModifier, M.AltModifier))
    return RULES.get(preset, _structura)(*pressed, *held)


def locked(dx: float, dy: float, lock: str) -> tuple[float, float]:
    """A drag constrained to one axis: 'horizontal' keeps dx, 'vertical' keeps dy, 'free' both."""
    if lock == "horizontal":
        return dx, 0.0
    if lock == "vertical":
        return 0.0, dy
    return dx, dy


class Navigator:
    """Turns mouse drags, the wheel and fly keys into OrbitController moves."""

    def __init__(self, orbit: OrbitController, preset: str = "structura") -> None:
        self.orbit, self.preset = orbit, preset
        self.lock = "free"  # the persistent orbit lock (LOCKS)
        self.last: QPoint | None = None
        self.action: str | None = None
        self._drag = QPoint()  # the drag so far (Ctrl picks the dominant axis once it is long enough)
        self._ctrl_lock: str | None = None

    def press(self, event: QMouseEvent) -> None:
        self.last = event.position().toPoint()
        self.action = drag_action(self.preset, event.buttons(), event.modifiers())
        self._drag, self._ctrl_lock = QPoint(), None

    def _modifiers(self, mods: Qt.KeyboardModifier) -> tuple[float, str]:
        """(speed factor, axis lock) of the current drag: Shift slows it, Ctrl locks it to its dominant axis
        (the Structura preset; the others spend Shift and Ctrl on actions), over the persistent lock."""
        if self.preset not in MODIFIER_KEYS:
            return 1.0, self.lock
        factor = SLOW if mods & M.ShiftModifier else 1.0
        if mods & M.ControlModifier:
            if self._ctrl_lock is None and self._drag.manhattanLength() >= LOCK_SLOP:
                self._ctrl_lock = "horizontal" if abs(self._drag.x()) >= abs(self._drag.y()) else "vertical"
            return factor, self._ctrl_lock or "none"
        return factor, self.lock

    def move(self, event: QMouseEvent) -> bool:
        """True when the camera moved."""
        if self.last is None:
            return False
        pos = event.position().toPoint()
        dx, dy = pos.x() - self.last.x(), pos.y() - self.last.y()
        self.last = pos
        self._drag += QPoint(dx, dy)
        self.action = drag_action(self.preset, event.buttons(), event.modifiers()) or self.action
        factor, lock = self._modifiers(event.modifiers())
        if lock == "none":  # Ctrl held, but the drag is too short to tell its axis yet
            return False
        fx, fy = dx * factor, dy * factor
        if self.action == "pan":
            self.orbit.pan(*locked(fx, fy, lock))
        elif self.action == "zoom_roll":
            self.orbit.dolly(-fy / 40.0)
            self.orbit.roll(fx * 0.005)
        elif self.action == "look":
            self.orbit.look(fx, fy)
        elif self.action == "orbit":
            self.orbit.orbit(*locked(fx, fy, lock))
        return self.action is not None

    def release(self) -> None:
        self.last, self.action = None, None

    def wheel(self, steps: float, mods: Qt.KeyboardModifier = M.NoModifier) -> None:
        self.orbit.dolly(steps * (SLOW if mods & M.ShiftModifier else 1.0))

    def key(self, event: QKeyEvent) -> bool:
        """W A S D / Q E fly the camera (the Structura preset, whenever the viewport has the focus; Shift: a
        quarter step); True when the camera moved."""
        move = FLY_KEYS.get(Qt.Key(event.key()))
        if move is None or (self.preset not in MODIFIER_KEYS and self.action != "look"):
            return False
        factor = SLOW if event.modifiers() & M.ShiftModifier else 1.0
        self.orbit.fly(*(axis * factor for axis in move))
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
