"""The application stylesheet, rendered from one Jinja2 template (docs/13 §5). Qt-free: returns text."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path

import jinja2

from .expr import split_alpha
from .model import Theme

TEMPLATES = Path(__file__).resolve().parent / "templates"
DENSITY_PAD = {"comfortable": 4, "compact": 2}


@dataclass(frozen=True)
class Fonts:
    ui: str = "Inter"
    ui_size: int = 10
    code: str = "JetBrains Mono"
    code_size: int = 11


def css_color(value: str) -> str:
    """'#RRGGBBAA' → 'rgba(r, g, b, a)'; opaque colours stay hex."""
    rgb, a = split_alpha(value)
    if a >= 0.999:
        return rgb
    r, g, b = (int(rgb[i : i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r}, {g}, {b}, {round(a * 255)})"


@cache
def _template() -> jinja2.Template:
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATES), autoescape=False, keep_trailing_newline=True)
    return env.get_template("app.qss.j2")


def render_qss(
    theme: Theme, fonts: Fonts | None = None, density: str = "comfortable", assets: dict[str, str] | None = None
) -> str:
    """``assets`` maps icon names to image files (e.g. 'close' for tab close buttons)."""
    f = fonts or Fonts()
    return _template().render(
        assets=assets or {},
        c=lambda role: css_color(theme[role]),
        pad=DENSITY_PAD.get(density, 4),
        ui_font=f.ui,
        ui_size=f.ui_size,
        code_font=f.code,
        code_size=f.code_size,
    )
