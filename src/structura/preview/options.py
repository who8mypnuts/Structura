"""Preview look and effect options (docs/08 §5). Colours are linear RGB."""

from __future__ import annotations

from dataclasses import dataclass

RGB = tuple[float, float, float]
LOOKS = {"studio": 0, "legacy": 1, "clay": 2, "flat": 3}


@dataclass(frozen=True)
class PreviewOptions:
    look: str = "studio"
    ssao: bool = True
    shadows: bool = True
    background_top: RGB = (0.09, 0.10, 0.12)
    background_bottom: RGB = (0.03, 0.035, 0.045)
    line_width: float = 1.5  # pixels
    exposure: float = 0.0
    selected: int | None = None  # SceneIR row to outline
    select_color: RGB = (1.0, 0.62, 0.15)  # display (sRGB) colour of the outline
    sun_direction: RGB = (0.4397, 0.7660, 0.4698)  # world, towards the sun (RenderSettings default)
    sky: RGB = (0.55, 0.62, 0.75)
    ground: RGB = (0.20, 0.19, 0.18)
    key: RGB = (0.95, 0.92, 0.86)

    @property
    def look_index(self) -> int:
        return LOOKS.get(self.look, 0)

    @property
    def effects(self) -> int:
        studio = self.look in ("studio", "clay")
        return (1 if self.ssao and studio else 0) | (2 if self.shadows and studio else 0)
