"""Where a render goes (docs/09 §8, docs/14 §5.4): the image file and, written beside it, a render report in the
chosen format (PDF, HTML, Markdown, plain text, JSON, CSV or OpenDocument). Used by Save Render, Final Render
and Add to Render Queue; the report type is remembered. For final renders it also picks the quality preset and
offers "Render Only" (no files)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...render.report.writers import FORMATS
from ..i18n import tr
from ..save_paths import SavePaths, with_extension

IMAGE_FILTERS = ["PNG image (*.png)", "OpenEXR, with AOV layers (*.exr)", "JPEG image (*.jpg)", "WebP image (*.webp)",
                 "TIFF image (*.tif)"]  # fmt: skip
IMAGE_SUFFIXES = (".png", ".exr", ".jpg", ".jpeg", ".webp", ".tif", ".tiff")
FINAL_PRESETS = ("Final", "Print 4K")
REPORT_KEY, REPORT_DEFAULT = "render/report_format", ".pdf"


@dataclass(frozen=True)
class RenderOutput:
    image: Path
    report: Path | None  # beside the image: '<name>-report.<ext>'; None: no report
    preset: str = ""  # final renders: the preset to render with
    save: bool = True  # False: "Render Only" — render without writing files


def report_beside(image: Path, suffix: str) -> Path | None:
    """'renders/tree.png' + '.md' → 'renders/tree-report.md' ('' → no report)."""
    return image.with_name(f"{image.stem}-report{suffix}") if suffix else None


def image_path(text: str, chosen_filter: str = "") -> Path | None:
    """A typed or chosen file name as an image path: without a known extension the chosen filter's (else PNG)."""
    if not text.strip():
        return None
    path = Path(text.strip()).expanduser()
    if path.suffix.lower() in IMAGE_SUFFIXES:
        return path
    extension = chosen_filter.rsplit("*", 1)[-1].rstrip(")") if "*" in chosen_filter else ".png"
    return with_extension(path, (extension,))


class RenderOutputDialog(QDialog):
    def __init__(
        self, paths: SavePaths, suggestion: Path, title: str, action: str,
        presets: tuple[str, ...] = (), parent: QWidget | None = None,
    ) -> None:  # fmt: skip
        super().__init__(parent)
        self.setWindowTitle(title)
        self.paths, self.render_only = paths, False
        self.path = QLineEdit(str(suggestion))
        self.path.setAccessibleName(tr("Image file"))
        self.path.setMinimumWidth(420)
        browse = QPushButton(tr("Browse…"))
        browse.clicked.connect(self._browse)
        row = QHBoxLayout()
        row.addWidget(self.path, 1)
        row.addWidget(browse)
        self.report = QComboBox()
        self.report.setAccessibleName(tr("Report"))
        self.report.addItem(tr("No report"), "")
        for suffix, (name, about) in FORMATS.items():
            self.report.addItem(f"{name} ({suffix})  —  {tr(about)}", suffix)
        remembered = str(paths.settings.value(REPORT_KEY, REPORT_DEFAULT))
        self.report.setCurrentIndex(max(0, self.report.findData(remembered)))
        self.where = QLabel()
        self.where.setObjectName("Muted")
        form = QFormLayout()
        form.addRow(tr("Image"), row)
        form.addRow(tr("Report"), self.report)
        form.addRow("", self.where)
        self.preset = self._preset_row(form, presets)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self._buttons(action, bool(presets)))
        self.path.textChanged.connect(self._describe)
        self.report.currentIndexChanged.connect(self._describe)
        self._describe()

    def _preset_row(self, form: QFormLayout, presets: tuple[str, ...]) -> QComboBox | None:
        if not presets:
            return None
        box = QComboBox()
        box.addItems(list(presets))
        box.setAccessibleName(tr("Quality"))
        box.setToolTip(tr("Samples, image size, noise threshold and denoising of the final render"))
        form.insertRow(0, tr("Quality"), box)
        return box

    def _buttons(self, action: str, final: bool) -> QDialogButtonBox:
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(action)
        if final:
            only = buttons.addButton(tr("Render Only"), QDialogButtonBox.ButtonRole.ActionRole)
            only.setToolTip(tr("Render without saving; use Save… afterwards"))
            only.clicked.connect(self._render_only)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        return buttons

    def _browse(self) -> None:
        current = image_path(self.path.text()) or Path.home() / "render.png"
        answer = self.paths.ask(self, "render", self.windowTitle(), current, IMAGE_FILTERS, self._filter_of(current))
        if answer is not None:
            chosen = image_path(str(answer[0]), answer[1])
            self.path.setText(str(chosen) if chosen else "")

    @staticmethod
    def _filter_of(path: Path) -> str:
        return next((f for f in IMAGE_FILTERS if f"*{path.suffix.lower()}" in f), IMAGE_FILTERS[0])

    def _describe(self) -> None:
        image = image_path(self.path.text())
        report = report_beside(image, str(self.report.currentData())) if image else None
        self.where.setText(tr("Written beside the image: {name}").format(name=report.name) if report else "")

    def _render_only(self) -> None:
        self.render_only = True
        self.accept()

    def _accept(self) -> None:
        image = image_path(self.path.text())
        if image is None:
            self.path.setFocus()
            return
        if image.exists() and not _confirm_replace(self, image):
            return
        self.paths.settings.set_value(REPORT_KEY, str(self.report.currentData()))
        self.paths.remember("render", image)
        self.accept()

    def output(self) -> RenderOutput | None:
        image = image_path(self.path.text())
        if image is None:
            return None
        preset = self.preset.currentText() if self.preset is not None else ""
        return RenderOutput(image, report_beside(image, str(self.report.currentData())), preset, not self.render_only)


def _confirm_replace(parent: QWidget, image: Path) -> bool:
    buttons = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    answer = QMessageBox.question(parent, tr("Replace File"), tr("{name} exists. Replace it?").format(name=image.name),
                                  buttons, QMessageBox.StandardButton.No)  # fmt: skip
    return bool(answer == QMessageBox.StandardButton.Yes)


def choose_output(
    parent: QWidget, paths: SavePaths, suggestion: Path, title: str, action: str, presets: tuple[str, ...] = ()
) -> RenderOutput | None:
    """Show the dialog; the chosen output, or None when cancelled (tests replace this function)."""
    dialog = RenderOutputDialog(paths, suggestion, title, action, presets, parent)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return dialog.output()
