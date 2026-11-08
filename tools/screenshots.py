"""Reproducible screenshots for the docs (docs/screenshots): the main window in several themes and the
GL preview engine rendered headless.

    PYTHONPATH=src:. python -m tools.screenshots

The window shots use Qt's offscreen platform with a 1920×1200 virtual screen (so the window gets its real
default size) unless QT_QPA_PLATFORM is set.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image
from PySide6.QtCore import QEventLoop, QTimer

from structura.app.main import create_app
from structura.core.build.api import build_scene
from structura.core.lang.api import compile_script
from structura.core.scene.camera import framed
from structura.core.scene.settings import settings_from_events
from structura.services.settings import SettingsService
from structura.ui.app_window import MainWindow

OUT = Path(__file__).resolve().parents[1] / "docs" / "screenshots"
EXAMPLES = Path(__file__).resolve().parents[1] / "src" / "structura" / "resources" / "legacy" / "examples"


def _wait(app: object, ms: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def window_shots(app: object) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        for theme, script in (("nord", "Default.es"), ("structura-dark", "Nouveau.es"), ("github-light", "Menger.es")):
            w = MainWindow(SettingsService(Path(tmp) / f"{theme}.ini"))
            w.themes.set_theme(theme)
            w.show()
            w.docs.open_example(EXAMPLES / script)
            w.panels.show("Examples")
            _wait(app, 20000)
            w.grab().save(str(OUT / f"window-{theme}.png"))
            for i in range(w.tabs.count()):
                w.tabs.widget(i).editor.document().setModified(False)  # type: ignore[union-attr]
            w.close()


def preview_shots() -> None:
    import moderngl  # noqa: PLC0415

    from structura.preview.instances import preview_scene  # noqa: PLC0415
    from structura.preview.options import PreviewOptions  # noqa: PLC0415
    from structura.preview.renderer import ACCUMULATE, PreviewRenderer  # noqa: PLC0415

    ctx = moderngl.create_standalone_context(require=330, backend="egl")
    renderer = PreviewRenderer(ctx)
    w, h = 960, 600
    fbo = ctx.framebuffer([ctx.texture((w, h), 4)])
    tiles = []
    for script in ("Default.es", "Nouveau.es", "Reflection.es", "City of Glass.es"):
        scene = build_scene(compile_script((EXAMPLES / script).read_text()).program).scene
        ps = preview_scene(scene)
        renderer.set_scene(ps)
        view = settings_from_events(scene.events)
        camera = view.view.camera() if view.has_view else framed(view.view.camera(), ps.lo, ps.hi, w / h)
        bg = tuple(float(c) ** 2.2 for c in view.background)
        options = (
            PreviewOptions(background_top=bg, background_bottom=bg)
            if view.background != (0, 0, 0)
            else PreviewOptions()
        )
        for _ in range(ACCUMULATE):
            renderer.render(camera, fbo, (w, h), options)
        tiles.append(np.frombuffer(fbo.read(components=3), np.uint8).reshape(h, w, 3)[::-1])
    grid = np.vstack([np.hstack(tiles[:2]), np.hstack(tiles[2:])])
    Image.fromarray(grid).save(OUT / "preview-engine.png")


SCREEN = {"screens": [{"name": "docs", "x": 0, "y": 0, "width": 1920, "height": 1200, "logicalDpi": 96,
                       "logicalBaseDpi": 96, "dpr": 1}]}  # fmt: skip


def _virtual_screen() -> None:
    if "QT_QPA_PLATFORM" not in os.environ:
        config = Path(tempfile.gettempdir()) / "structura-screenshots-screen.json"
        config.write_text(json.dumps(SCREEN), encoding="utf-8")
        os.environ["QT_QPA_PLATFORM"] = f"offscreen:configfile={config}"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    _virtual_screen()
    preview_shots()
    app = create_app(sys.argv)
    window_shots(app)
    print(f"screenshots written to {OUT}")


if __name__ == "__main__":
    main()
