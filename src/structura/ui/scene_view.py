"""Helpers that turn scene data into view state: viewport options and picked-object descriptions."""

from __future__ import annotations

from dataclasses import replace

from ..core.color import srgb_to_linear
from ..core.color.oklab import hex_to_rgb
from ..core.lang.analysis import Analysis
from ..core.lang.source import Span
from ..core.scene.ir import PrimitiveKind, SceneIR
from ..core.scene.settings import settings_from_events
from ..preview.options import PreviewOptions
from ..themes.expr import split_alpha
from ..themes.model import Theme


def _linear(hex_color: str) -> tuple[float, float, float]:
    r, g, b = (float(v) for v in srgb_to_linear(hex_to_rgb(split_alpha(hex_color)[0])))  # type: ignore[arg-type]
    return (r, g, b)


def viewport_options(options: PreviewOptions, theme: Theme, scene: SceneIR | None) -> PreviewOptions:
    """The script's background when it sets one (renders never depend on the theme), else the theme's."""
    if scene is not None and any(event.key == "background" for event, _, _ in scene.events):
        bg = tuple(float(v) for v in srgb_to_linear(settings_from_events(scene.events).background))  # type: ignore[arg-type]
        return replace(options, background_top=bg, background_bottom=bg)  # type: ignore[arg-type]
    top, bottom = _linear(theme["viewport.bg.top"]), _linear(theme["viewport.bg.bottom"])
    return replace(
        options, background_top=top, background_bottom=bottom, select_color=hex_to_rgb(theme["viewport.selection"][:7])
    )


def describe_pick(scene: SceneIR, analysis: Analysis | None, row: int) -> tuple[str, Span | None]:
    kind = PrimitiveKind(int(scene.kind[row])).name.lower()
    tag = scene.tags[int(scene.tag[row])] if scene.tags else ""
    parts = [f"{kind} #{row:,}", f"generation {int(scene.generation[row])}"]
    if tag:
        parts.append(f"tag {tag}")
    span = analysis.action_span(int(scene.source[row])) if analysis is not None else None
    if span is not None:
        parts.append("→ source")
    return " · ".join(parts), span
