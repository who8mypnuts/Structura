"""Generate every Structura brand asset into src/structura/resources/brand/.

Usage:  QT_QPA_PLATFORM=offscreen python -m tools.brand.make_logo
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from .compose import INK_DARK_BG, INK_LIGHT_BG, icon_svg, lockup_svg, mark_svg
from .raster import render_png

OUT = Path(__file__).resolve().parents[2] / "src/structura/resources/brand"
ICON_SIZES = (16, 24, 32, 48, 64, 128, 256, 512, 1024)
COMPACT_MAX = 48


def write_svgs() -> dict[str, str]:
    svgs = {
        "structura-mark.svg": mark_svg(),
        "structura-mark-compact.svg": mark_svg(compact=True),
        "structura-icon.svg": icon_svg(),
        "structura-icon-compact.svg": icon_svg(compact=True),
        "structura-logo-on-dark.svg": lockup_svg(INK_DARK_BG),
        "structura-logo-on-light.svg": lockup_svg(INK_LIGHT_BG),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    for name, text in svgs.items():
        (OUT / name).write_text(text, encoding="utf-8")
    return svgs


def write_pngs(svgs: dict[str, str]) -> None:
    for size in ICON_SIZES:
        icon = svgs["structura-icon-compact.svg" if size <= COMPACT_MAX else "structura-icon.svg"]
        render_png(icon, OUT / f"png/icon-{size}.png", size)
    render_png(svgs["structura-mark.svg"], OUT / "png/mark-1024.png", 1024)
    for name in ("structura-logo-on-dark", "structura-logo-on-light"):
        svg = svgs[f"{name}.svg"]
        w = int(svg.split('width="')[1].split('"')[0])
        h = int(svg.split('height="')[1].split('"')[0])
        render_png(svg, OUT / f"png/{name}@2x.png", w * 2, h * 2)


def write_platform_icons() -> None:
    images = {s: Image.open(OUT / f"png/icon-{s}.png") for s in ICON_SIZES}
    ico_sizes = [(s, s) for s in (16, 24, 32, 48, 64, 128, 256)]
    images[256].save(
        OUT / "structura.ico", sizes=ico_sizes, append_images=[images[s] for s in (16, 24, 32, 48, 64, 128)]
    )
    images[1024].save(OUT / "structura.icns")


def write_review_sheet() -> None:
    sheet = Image.new("RGBA", (1400, 760), "#0B1022")
    light = Image.new("RGBA", (700, 200), "#F5F7FB")
    sheet.paste(light, (700, 560))
    x = 30
    for s in (16, 24, 32, 48, 64, 128, 256):
        icon = Image.open(OUT / f"png/icon-{s}.png")
        sheet.alpha_composite(icon, (x, 40 + (256 - s) // 2))
        x += s + 30
    mark = Image.open(OUT / "png/mark-1024.png").resize((300, 300))
    sheet.alpha_composite(mark, (1060, 20))
    for name, pos in (("structura-logo-on-dark", (40, 380)), ("structura-logo-on-light", (730, 590))):
        logo = Image.open(OUT / f"png/{name}@2x.png")
        logo = logo.resize((620, round(620 * logo.height / logo.width)))
        sheet.alpha_composite(logo, pos)
    sheet.convert("RGB").save(OUT / "brand-sheet.png")


def main() -> None:
    svgs = write_svgs()
    write_pngs(svgs)
    write_platform_icons()
    write_review_sheet()
    print(f"brand assets written to {OUT}")


if __name__ == "__main__":
    main()
