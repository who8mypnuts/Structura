"""The views' banner (docs/14 §5.2, §6): conditions worth a decision — a Structure Synth script with raytracer
settings (render it with the legacy look or the modern path tracer?), or a viewport that fell back to the
compute preview. Each is offered once per document or session; a dismissed one stays away."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Slot
from PySide6.QtGui import QGuiApplication

from .i18n import tr
from .viewport.gl_probe import HEADLESS_PLATFORMS

if TYPE_CHECKING:
    from .app_window import MainWindow
    from .documents import EditorTab
    from .workbench import PreviewReady

LEGACY = "legacy-raytracer"
FALLBACK = "compute-preview"


class Banners(QObject):
    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.w = window
        self.offered: set[str] = set()  # doc ids (legacy hint) and FALLBACK, once each

    @Slot(object, object, object, bool)
    def scene_ready(self, tab: EditorTab, ready: PreviewReady, *_: object) -> None:
        """A v1 script with 'set raytracer::…' settings: offer the legacy look once for this document."""
        if tab.doc_id in self.offered or tab.dialect != 1:
            return
        if any(event.key.startswith("raytracer::") for event, _, _ in ready.outcome.scene.events):
            self.offered.add(tab.doc_id)
            text = tr("This Structure Synth script has raytracer settings. Render it with the classic look of"
                      " Structure Synth's raytracer, or with the modern path tracer?")  # fmt: skip
            actions = ((tr("Legacy Look"), lambda: self._integrator("classic")),
                       (tr("Modern Path Tracer"), lambda: self._integrator("path")))  # fmt: skip
            self.w.banner.show_message(LEGACY, text, actions)

    def _integrator(self, name: str) -> None:
        self.w.render_view.integrator.setCurrentText(name)
        self.w.show_message(tr("Renders use the {name} integrator").format(name=name))

    @Slot(str)
    def preview_mode(self, mode: str) -> None:
        """The viewport is not OpenGL: say so once per session, with what to do about it."""
        headless = QGuiApplication.platformName() in HEADLESS_PLATFORMS  # never a GPU viewport: nothing to fix
        if mode in ("gpu", "off", "rendered") or FALLBACK in self.offered or headless:
            return
        self.offered.add(FALLBACK)
        text = tr("OpenGL 3.3 is not available, so the viewport draws with the render kernels ({mode}). "
                  "'structura doctor' shows why; the troubleshooting guide lists fixes.")  # fmt: skip
        text = text.format(mode=mode.upper())
        self.w.banner.show_message(FALLBACK, text)
