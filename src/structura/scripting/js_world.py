"""The 1.5 JavaScript globals besides Builder (docs/16 §3): ``Debug`` (console, messages, progress, sleeping,
waiting for a click) and ``World`` (direct scene edits: spheres in the current colour). ``Vector3`` is a plain
JavaScript constructor. Everything visible goes through the JsHost, so the GUI stays on its own thread."""

from __future__ import annotations

from typing import Any

import numpy as np
from PySide6.QtCore import QObject, Slot
from PySide6.QtQml import QJSEngine, QJSValue

from ..core.scene.ir import PrimitiveKind, SceneIR

VECTOR3 = "function Vector3(x, y, z) { this.x = x || 0; this.y = y || 0; this.z = z || 0; }"
CANCELLED = "structura: cancelled"


def _xyz(value: QJSValue) -> tuple[float, float, float]:
    """A JavaScript {x, y, z} object (a Vector3) as a tuple."""
    x, y, z = (float(value.property(k).toNumber()) for k in "xyz")
    return x, y, z


Sphere = tuple[tuple[float, ...], float, tuple[float, ...], float]  # centre, radius, rgb, alpha


def spheres_scene(spheres: list[Sphere], base: SceneIR | None) -> SceneIR:
    """``base`` (or nothing) with World.addSphere's spheres appended (a sphere fills its frame's inscribed ball)."""
    n = len(spheres)
    xform = np.zeros((n, 3, 4), np.float32)
    rgba = np.zeros((n, 4), np.float32)
    for i, (centre, radius, rgb, alpha) in enumerate(spheres):
        xform[i, :, :3] = np.eye(3) * 2 * radius
        xform[i, :, 3] = np.asarray(centre) - radius
        rgba[i] = (*rgb, alpha)
    rows = SceneIR(np.full(n, PrimitiveKind.SPHERE, np.uint8), xform, rgba, np.zeros(n, np.int32),
                   np.full(n, -1, np.int32), np.zeros(n, np.int32), np.full(n, -1, np.int32),
                   np.zeros((0, 13), np.float32), ("",))  # fmt: skip
    if not isinstance(base, SceneIR) or not len(base):
        return rows

    def joined(name: str) -> np.ndarray:
        return np.concatenate([getattr(base, name), getattr(rows, name)])

    untagged = base.tags.index("") if "" in base.tags else 0
    tag = np.concatenate([base.tag, np.full(n, untagged, np.int32)])
    return SceneIR(joined("kind"), joined("xform"), joined("rgba"), tag, joined("source"), joined("generation"),
                   joined("aux"), base.aux_data.copy(), base.tags, base.events, base.declarations)  # fmt: skip


class DebugApi(QObject):
    def __init__(self, engine: QJSEngine, host: Any) -> None:
        super().__init__()
        self.engine, self.host = engine, host

    @Slot(str)
    def Info(self, text: str) -> None:  # noqa: N802 - the 1.5 API names
        self.host.info(text)

    @Slot(str)
    def Message(self, text: str) -> None:  # noqa: N802
        self.host.message(text)

    @Slot(str)
    def ShowProgress(self, caption: str) -> None:  # noqa: N802
        self.host.progress(caption, 0.0)

    @Slot(float)
    def SetProgress(self, fraction: float) -> None:  # noqa: N802
        self.host.progress(None, max(0.0, min(1.0, fraction)))

    @Slot()
    def HideProgress(self) -> None:  # noqa: N802
        self.host.progress(None, None)

    @Slot(int)
    def Sleep(self, ms: int) -> None:  # noqa: N802
        self.host.sleep(ms)

    @Slot()
    def waitForMouseButton(self) -> None:  # noqa: N802
        """Left click in the viewport continues; right click (or Cancel) ends the script."""
        if not self.host.wait_for_click():
            self.engine.throwError(CANCELLED)


class WorldApi(QObject):
    def __init__(self, host: Any, builder: Any) -> None:
        super().__init__()
        self.host, self.builder = host, builder
        self.spheres: list[Sphere] = []
        self.rgb, self.alpha = (1.0, 1.0, 1.0), 1.0

    @Slot(QJSValue, float)
    def addSphere(self, centre: Any, radius: float) -> None:  # noqa: N802
        self.spheres.append((_xyz(centre), float(radius), self.rgb, self.alpha))
        self.show()

    @Slot(QJSValue, float)
    def setColor(self, rgb: Any, alpha: float) -> None:  # noqa: N802
        self.rgb, self.alpha = _xyz(rgb), float(alpha)

    @Slot()
    def clear(self) -> None:
        self.spheres = []
        self.show()

    def show(self) -> None:
        scene = self.builder.scene
        self.host.show_scene(spheres_scene(self.spheres, scene) if self.spheres else scene)
