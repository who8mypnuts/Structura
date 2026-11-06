"""Scene settings derived from a build's ordered scene events (background, legacy camera, raytracer keys)."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..color import parse_color
from ..lang.compile.setops import SceneEvent
from .camera import LegacyView

RGB = tuple[float, float, float]


@dataclass(frozen=True)
class SceneSettings:
    background: RGB = (0.0, 0.0, 0.0)  # Structure Synth's OpenGL default
    view: LegacyView = field(default_factory=LegacyView)
    has_view: bool = False  # the script set at least one camera value
    raytracer: tuple[tuple[str, str], ...] = ()  # ('samples', '6'), ('shiny::reflection', '0.3'), …


def _numbers(value: str) -> list[float]:
    return [float(p) for p in value.replace("[", "").replace("]", "").split(" ")]


def settings_from_events(events: tuple[tuple[SceneEvent, int, int], ...]) -> SceneSettings:
    background: RGB = (0.0, 0.0, 0.0)
    view = LegacyView()
    view_values: dict[str, object] = {}
    raytracer: list[tuple[str, str]] = []
    for event, _gen, _before in events:
        key, value = event.key, event.value
        if key == "background":
            c = parse_color(value)
            if c is not None:
                background = (c.r / 65535, c.g / 65535, c.b / 65535)
        elif key in ("translation", "pivot") or key == "rotation":
            view_values[key] = tuple(_numbers(value))
        elif key == "scale":
            view_values[key] = float(value)
        elif key == "perspective-angle":
            view_values["fov_y_deg"] = float(value)
        elif key.startswith("raytracer::"):
            raytracer.append((key.removeprefix("raytracer::"), value.replace("[", "").replace("]", "")))
    if view_values:
        view = LegacyView(**view_values)  # type: ignore[arg-type]
    return SceneSettings(background, view, bool(view_values), tuple(raytracer))
