"""What the viewport shows of a scene (docs/08 §5–6): colour-by mode, X-ray and isolation. Only the viewport
uses it; renders and exports always get the scene as built.

Hidden rows keep their place (their frames collapse to a point), so SceneIR row numbers — provenance, picking,
the Inspector — stay valid."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np

from .color_by import recolored
from .ir import SceneIR

XRAY_ALPHA = 0.22


@dataclass(frozen=True)
class ViewFilter:
    color_by: str = "authored"
    xray: bool = False
    isolate: np.ndarray | None = field(default=None, compare=False)  # rows to show; None: all

    def apply(self, scene: SceneIR) -> SceneIR:
        shown = recolored(scene, self.color_by)
        if self.xray and len(shown):
            rgba = np.array(shown.rgba, np.float32)
            rgba[:, 3] = np.minimum(rgba[:, 3], XRAY_ALPHA)
            shown = replace(shown, rgba=rgba)
        if self.isolate is not None and len(shown) and int(self.isolate.max(initial=-1)) < len(shown):
            xform = np.array(shown.xform, np.float32)
            hidden = np.ones(len(shown), bool)
            hidden[self.isolate] = False
            xform[hidden, :, :3] = 0.0  # a point: nothing to draw, nothing to pick
            shown = replace(shown, xform=xform)
        return shown
