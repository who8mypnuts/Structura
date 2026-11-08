"""The Render view's tool bar controls (docs/09 §9): what to render, how to display it, progress."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QToolBar,
    QWidget,
)

from ...compute.select import NAMES
from ...render.aov_display import CHANNELS
from ...render.denoise import METHODS
from ...render.settings import AUTO_PASSES, INTEGRATORS, VIEWS, RenderSettings
from ..i18n import tr
from .presets import BY_NAME, CUSTOM, PRESETS, image_size

DENOISE_OFF = "off"


def _combo(items: list[str] | tuple[str, ...], current: str, tip: str) -> QComboBox:
    box = QComboBox()
    box.addItems(list(items))
    box.setCurrentText(current)
    box.setToolTip(tip)
    return box


class RenderControls:
    """Owns the widgets; RenderView connects them. Buttons come first so they never overflow."""

    def __init__(self) -> None:
        self.render_button, self.stop_button = QPushButton(tr("Render")), QPushButton(tr("Stop"))
        self.save_button, self.snapshot_button = QPushButton(tr("Save…")), QPushButton(tr("A/B"))
        self.resume_button = QPushButton(tr("Resume"))
        self.resume_button.setToolTip(tr("Continue the stopped render where it left off"))
        self.resume_button.setEnabled(False)
        self.report_button = QPushButton(tr("Report…"))
        self.report_button.setToolTip(tr("Save a detailed report of the render: PDF, HTML, Markdown, text, JSON, CSV"))
        self.snapshot_button.setToolTip(
            tr("Snapshot the current image and compare it with the next render (drag the split; click again to clear)")
        )
        self.render_button.setProperty("accent", True)
        self.preset = _combo([*(p.name for p in PRESETS), CUSTOM], "Standard",
                             tr("Render preset: samples, image size, noise threshold and denoising"))  # fmt: skip
        self.preset.setAccessibleName(tr("Render preset"))
        self.integrator = _combo(sorted(INTEGRATORS), "path", tr("Integrator"))
        self.device = _combo(NAMES, "auto", tr("Compute device"))
        self.samples = QSpinBox()
        self.samples.setRange(1, 65536)
        self.samples.setValue(128)
        self.samples.setPrefix("spp ")
        self.samples.setMaximumWidth(96)
        self.samples.setAccessibleName(tr("Samples per pixel"))
        self.denoise = _combo((DENOISE_OFF, *METHODS), "auto", tr("Denoise when finished (auto: OIDN, else À-Trous)"))
        self.exposure = QDoubleSpinBox()
        self.exposure.setRange(-10.0, 10.0)
        self.exposure.setSingleStep(0.25)
        self.exposure.setPrefix("EV ")
        self.exposure.setToolTip(tr("Exposure in stops (applies live, without re-rendering)"))
        self.exposure.setAccessibleName(tr("Exposure"))
        self.view_box = _combo(VIEWS, "auto", tr("View transform: auto = AgX (classic: standard)"))
        self.channel = _combo(CHANNELS, "beauty", tr("Shown channel: the image or one of its AOVs"))
        self.progress, self.info, self.pixel = QProgressBar(), QLabel(""), QLabel("")
        self.pixel.setObjectName("Muted")
        self.pixel.setToolTip(tr("The linear value of the pixel under the cursor; Shift+drag re-renders a region"))
        self.progress.setMinimumWidth(60)
        self.info.setObjectName("Muted")
        # status text changes while rendering: it is clipped rather than allowed to widen the window
        self.info.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.info.setMinimumWidth(80)
        self.preset.currentTextChanged.connect(self.apply_preset)
        self.samples.valueChanged.connect(self._samples_edited)
        self.apply_preset(self.preset.currentText())

    def widgets(self) -> tuple[QWidget, ...]:
        return (self.render_button, self.stop_button, self.resume_button, self.save_button, self.report_button,
                self.snapshot_button,
                self.preset, self.integrator,
                self.samples, self.device, self.denoise, self.exposure, self.view_box, self.channel,
                self.progress, self.info, self.pixel)  # fmt: skip

    def tool_bar(self) -> QToolBar:
        # A tool bar, not a box layout: controls that do not fit move behind its overflow button, so the
        # render view never forces the window (or the editor beside it) wider.
        bar = QToolBar()
        bar.setObjectName("RenderBar")
        for widget in self.widgets():
            bar.addWidget(widget)
        return bar

    def apply_preset(self, name: str) -> None:
        preset = BY_NAME.get(name)
        if preset is None:
            return
        self.samples.blockSignals(True)
        self.samples.setValue(preset.samples)
        self.samples.blockSignals(False)
        self.denoise.setCurrentText(preset.denoise)

    def _samples_edited(self) -> None:
        preset = BY_NAME.get(self.preset.currentText())
        if preset is not None and preset.samples != self.samples.value():
            self.preset.setCurrentText(CUSTOM)

    def image_size(self, viewport: tuple[int, int]) -> tuple[int, int]:
        preset = BY_NAME.get(self.preset.currentText())
        return image_size(viewport, preset.long_edge if preset else None)

    def settings(self, width: int, height: int) -> RenderSettings:
        preset = BY_NAME.get(self.preset.currentText())
        return RenderSettings(
            width=width, height=height, samples=self.samples.value(), samples_per_pass=AUTO_PASSES,
            integrator=self.integrator.currentText(), aovs=True,
            noise_threshold=preset.noise_threshold if preset else 0.0,
        )  # fmt: skip

    def denoise_method(self) -> str | None:
        method = self.denoise.currentText()
        return None if method == DENOISE_OFF else method

    def view_transform(self) -> str:
        view = self.view_box.currentText()
        if view != "auto":
            return view
        return "standard" if self.integrator.currentText() == "classic" else "agx"
