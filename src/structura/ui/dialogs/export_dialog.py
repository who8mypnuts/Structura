"""The export sheet (docs/14 §5.5, docs/15 §7): where the file goes, what is in it, and the exporter's options.

It opens after the Save As dialog. It shows the full destination path (with Change… to pick another), a
summary of the scene, and the options generated from the exporter's ParamSpecs.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.params import resolve
from ...core.scene.ir import SceneIR
from ...export.base import Exporter
from ...export.presets import load_preset, preset_names, save_preset
from ..i18n import tr
from ..widgets.param_form import ParamForm

ChangePath = Callable[[Exporter, Path], Path | None]


def scene_summary(scene: SceneIR) -> str:
    counts = scene.kind_counts()
    kinds = ", ".join(f"{count:,} {kind}" for kind, count in list(counts.items())[:4])
    more = f", {len(counts) - 4} more kinds" if len(counts) > 4 else ""
    return f"{len(scene):,} objects" + (f" ({kinds}{more})" if kinds else "")


class ExportDialog(QDialog):
    def __init__(
        self, exporter: Exporter, path: Path, scene: SceneIR, values: dict[str, object], change: ChangePath,
        parent: QWidget | None = None,
    ) -> None:  # fmt: skip
        super().__init__(parent)
        self.exporter, self.path, self._change = exporter, path, change
        self.setWindowTitle(tr("Export — {format}").format(format=exporter.title))
        self.form = ParamForm(exporter.params, values)
        head = QFormLayout()
        head.addRow(tr("Save to"), self._destination_row())
        head.addRow(tr("Contents"), QLabel(scene_summary(scene)))
        head.addRow(tr("Preset"), self._preset_row())
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(tr("Export"))
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(head)
        layout.addWidget(self.form)
        layout.addWidget(buttons)
        self._show_path()

    def _destination_row(self) -> QHBoxLayout:
        self.destination = QLabel()
        self.destination.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.destination.setWordWrap(True)
        self.destination.setAccessibleName(tr("Destination"))
        change_button = QPushButton(tr("Change…"))
        change_button.clicked.connect(self._change_path)
        row = QHBoxLayout()
        row.addWidget(self.destination, 1)
        row.addWidget(change_button)
        return row

    def _preset_row(self) -> QHBoxLayout:
        self.presets = QComboBox()
        self.presets.setAccessibleName(tr("Export preset"))
        self._fill_presets()
        self.presets.activated.connect(self._load_preset)
        save_button = QPushButton(tr("Save Preset…"))
        save_button.setToolTip(tr("Keep these options under a name (also for 'structura export --preset')"))
        save_button.clicked.connect(self._save_preset)
        row = QHBoxLayout()
        row.addWidget(self.presets, 1)
        row.addWidget(save_button)
        return row

    def _fill_presets(self, current: str = "") -> None:
        self.presets.clear()
        self.presets.addItem(tr("(current options)"), "")
        for name in preset_names(self.exporter.name):
            self.presets.addItem(name, name)
        if current:
            self.presets.setCurrentIndex(self.presets.findData(current))

    def _load_preset(self) -> None:
        name = self.presets.currentData()
        if name:
            values = resolve(self.exporter.params, load_preset(self.exporter.name, str(name)))
            self.form.set_values(values)

    def _save_preset(self) -> None:
        name, ok = QInputDialog.getText(self, tr("Save Preset"), tr("Preset name"))
        if ok and name.strip():
            self.save_preset_as(name.strip())

    def save_preset_as(self, name: str) -> None:
        save_preset(self.exporter.name, name, self.form.values())
        self._fill_presets(name)

    def _show_path(self) -> None:
        self.destination.setText(str(self.path))

    def _change_path(self) -> None:
        chosen = self._change(self.exporter, self.path)
        if chosen is not None:
            self.path = chosen
            self._show_path()

    def _accept(self) -> None:
        """Create the folder if needed; files chosen with Change… were confirmed by the Save As dialog."""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            QMessageBox.warning(self, self.windowTitle(), tr("Cannot create the folder: {error}").format(error=exc))
            return
        self.accept()
