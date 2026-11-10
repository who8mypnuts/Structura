"""The Render view's tool bar controls (docs/09 §9): what to render, how to display it, progress."""

from __future__ import annotations

from collections.abc import Collection

from PySide6.QtWidgets import (
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
from ...render.post import LOOKS, PostSettings
from ...render.settings import AUTO_PASSES, INTEGRATORS, VIEWS, RenderSettings, resolve_view
from ..i18n import tr
from ..widgets.fields import combo_box
from .presets import BY_NAME, CUSTOM, FRAME_CUSTOM, FRAME_VIEWPORT, FRAMES, PRESETS, frame_size

DENOISE_OFF = "off"
LOOK_SCRIPT = "Script"  # the look the script's render block declares (bloom, vignette, … keys)


class RenderControls:
    """Owns the widgets; RenderView connects them. Buttons come first so they never overflow."""

    def __init__(self) -> None:
        """Creates every tool-bar widget and applies the default preset."""
        self.render_button, self.stop_button = QPushButton(tr("Render")), QPushButton(tr("Stop"))
        self.save_button, self.snapshot_button = QPushButton(tr("Save…")), QPushButton(tr("A/B"))
        self.resume_button = QPushButton(tr("Resume"))
        self.resume_button.setToolTip(tr("Continue the stopped render where it left off"))
        self.resume_button.setEnabled(False)
        self.report_button = QPushButton(tr("Report…"))
        self.report_button.setToolTip(tr("Save a detailed report of the render: PDF, HTML, Markdown, text, JSON, CSV"))
        self.save_button.setToolTip(tr("Save the image, with a report beside it (PDF, HTML, Markdown or text)"))
        self.snapshot_button.setToolTip(
            tr("Snapshot the current image and compare it with the next render (drag the split; click again to clear)")
        )
        self.render_button.setProperty("accent", True)
        self.preset = combo_box(
            [*(p.name for p in PRESETS), CUSTOM],
            tr("Render preset"),
            "Standard",
            tr("Render preset: samples, image size, noise threshold and denoising"),
        )
        self._frame_widgets()
        self.integrator = combo_box(sorted(INTEGRATORS), current="path", tip=tr("Integrator"))
        self.device = combo_box(NAMES, current="auto", tip=tr("Compute device"))
        self.samples = QSpinBox()
        self.samples.setRange(1, 65536)
        self.samples.setValue(128)
        self.samples.setPrefix("spp ")
        self.samples.setMaximumWidth(96)
        self.samples.setAccessibleName(tr("Samples per pixel"))
        self.denoise = combo_box(
            (DENOISE_OFF, *METHODS), current="auto", tip=tr("Denoise when finished (auto: OIDN, else À-Trous)")
        )
        self._display_widgets()
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

    def _display_widgets(self) -> None:
        """How the image is shown (all live, without re-rendering): exposure, view transform, look, channel."""
        self.exposure = QDoubleSpinBox()
        self.exposure.setRange(-10.0, 10.0)
        self.exposure.setSingleStep(0.25)
        self.exposure.setPrefix("EV ")
        self.exposure.setToolTip(tr("Exposure in stops (applies live, without re-rendering)"))
        self.exposure.setAccessibleName(tr("Exposure"))
        self.view_box = combo_box(VIEWS, current="auto", tip=tr("View transform: auto = AgX (classic: standard)"))
        tip = tr("Look: bloom, vignette and colour grading (applies live; a script's render block can declare one)")
        self.look = combo_box(LOOKS, tr("Look"), "Off", tip)
        self.script_post = PostSettings()
        self.channel = combo_box(CHANNELS, current="beauty", tip=tr("Shown channel: the image or one of its AOVs"))

    def widgets(self) -> tuple[QWidget, ...]:
        """Returns the tool bar's widgets in order (buttons first, so they never overflow)."""
        return (self.render_button, self.stop_button, self.resume_button, self.save_button, self.report_button,
                self.snapshot_button,
                self.preset, self.frame, self.width, self.height, self.integrator,
                self.samples, self.device, self.denoise, self.exposure, self.view_box, self.look, self.channel,
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

    def _frame_widgets(self) -> None:
        """The frame choice and the custom width and height (shown for Custom only)."""
        tip = tr("Frame: the viewport's shape, the script's size, a ratio, or an exact size (the viewport shows it)")
        self.frame = combo_box(FRAMES, tr("Frame"), FRAME_VIEWPORT, tip)
        self.width, self.height = QSpinBox(), QSpinBox()
        for spin, name in ((self.width, tr("Width")), (self.height, tr("Height"))):
            spin.setRange(16, 16384)
            spin.setAccessibleName(name)
            spin.setMaximumWidth(80)
        self.width.setValue(1920)
        self.height.setValue(1080)
        self.frame.currentTextChanged.connect(self._frame_chosen)
        self._frame_chosen(self.frame.currentText())

    def _frame_chosen(self, frame: str) -> None:
        for spin in (self.width, self.height):
            spin.setVisible(frame == FRAME_CUSTOM)

    def image_size(self, viewport: tuple[int, int], script: tuple[int, int] | None = None) -> tuple[int, int]:
        """Returns the render size: the frame (presets.FRAMES) with the preset's long edge.

        Args:
            viewport: The viewport's size in pixels.
            script: The script's 'render { size }', or None (the viewport's size then stands in for it).
        """
        preset = BY_NAME.get(self.preset.currentText())
        custom = (self.width.value(), self.height.value())
        return frame_size(self.frame.currentText(), viewport, preset.long_edge if preset else None,
                          script or viewport, custom)  # fmt: skip

    def settings(self, width: int, height: int) -> RenderSettings:
        preset = BY_NAME.get(self.preset.currentText())
        return RenderSettings(
            width=width, height=height, samples=self.samples.value(), samples_per_pass=AUTO_PASSES,
            integrator=self.integrator.currentText(), aovs=True,
            noise_threshold=preset.noise_threshold if preset else 0.0,
        )  # fmt: skip

    def show_script(self, script: RenderSettings, declared: Collection[str]) -> None:
        """Shows the script's render choices in the tool bar.

        The integrator always; the view transform, exposure and denoising when the render block sets them (otherwise
        the user's choices stay); the 'Script' look while the block declares one.

        Args:
            script: The script's render settings.
            declared: The keys the script's render block sets.
        """
        self.integrator.setCurrentText(script.integrator)
        if "view" in declared:
            self.view_box.setCurrentText(script.view)
        if "exposure" in declared:
            self.exposure.setValue(script.exposure)
        if "denoise" in declared:
            self.denoise.setCurrentText(script.denoise)
        self._show_script_look(script.post)

    def _show_script_look(self, post: PostSettings) -> None:
        """Offer (and choose) the 'Script' look while the script declares one; remove it when it no longer does."""
        self.script_post = post
        index = self.look.findText(LOOK_SCRIPT)
        if post.active:
            if index < 0:
                self.look.addItem(LOOK_SCRIPT)
            self.look.setCurrentText(LOOK_SCRIPT)
        elif index >= 0:
            self.look.removeItem(index)  # (Qt moves the selection off it)

    def post(self) -> PostSettings:
        """Returns the post stack of the chosen look (the script's own for 'Script')."""
        name = self.look.currentText()
        return self.script_post if name == LOOK_SCRIPT else LOOKS.get(name, PostSettings())

    def denoise_method(self) -> str | None:
        method = self.denoise.currentText()
        return None if method == DENOISE_OFF else method

    def view_transform(self) -> str:
        """Returns the chosen view transform, with 'auto' resolved for the chosen integrator."""
        return resolve_view(self.view_box.currentText(), self.integrator.currentText())
