"""Convert the 'Structura' wordmark to SVG path data using the bundled Inter variable font.

Outlines make the logo independent of installed fonts. Layout uses advance widths plus a tracking value;
the word has no problematic kerning pairs at display sizes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

FONT = Path(__file__).resolve().parents[2] / "src/structura/resources/fonts/Inter-Variable.ttf"


@dataclass(frozen=True)
class TextPath:
    d: str  # SVG path data, baseline at y=0, x starting at 0 (y down)
    width: float  # advance width in output units
    cap_height: float


def text_path(text: str, size: float, weight: int = 700, tracking: float = -0.01) -> TextPath:
    """Outline ``text`` at font ``size`` (px). ``tracking`` is in em (negative = tighter)."""
    font = instantiateVariableFont(TTFont(FONT), {"wght": weight, "opsz": 32})
    glyphs = font.getGlyphSet()
    cmap = font.getBestCmap()
    scale = size / font["head"].unitsPerEm
    pen = SVGPathPen(glyphs)
    x = 0.0
    for ch in text:
        name = cmap[ord(ch)]
        # font units, y-up → output px, y-down; glyph origin shifted by the running advance
        glyphs[name].draw(TransformPen(pen, (scale, 0, 0, -scale, x, 0)))
        x += glyphs[name].width * scale + tracking * size
    cap = font["OS/2"].sCapHeight * scale
    return TextPath(pen.getCommands(), x - tracking * size, cap)
