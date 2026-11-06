"""Theme picker (docs/13 §8): every theme with live preview while browsing; import VS Code / base16 themes."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...services.theme import ThemeService
from ...themes.importers import import_theme
from ...themes.loader import user_dir


class ThemePicker(QDialog):
    def __init__(self, themes: ThemeService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Colour theme")
        self.themes = themes
        self.original = themes.theme.meta.id
        self.list = QListWidget()
        importer = QPushButton("Import VS Code or base16 theme…")
        importer.clicked.connect(self.import_dialog)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(self.list)
        layout.addWidget(importer)
        layout.addWidget(buttons)
        self.populate()
        self.list.currentItemChanged.connect(self._preview)
        self.resize(360, 520)

    def populate(self) -> None:
        self.list.clear()
        metas = sorted(self.themes.themes(), key=lambda m: (m.kind, m.family != "Structura", m.name))
        for meta in metas:
            item = QListWidgetItem(f"{'☾' if meta.dark else '☀'}  {meta.name}")
            item.setData(Qt.ItemDataRole.UserRole, meta.id)
            self.list.addItem(item)
            if meta.id == self.themes.theme.meta.id:
                self.list.setCurrentItem(item)

    def _preview(self, item: QListWidgetItem | None) -> None:
        if item is not None:
            self.themes.set_theme(str(item.data(Qt.ItemDataRole.UserRole)))

    def reject(self) -> None:
        self.themes.set_theme(self.original)
        super().reject()

    def import_dialog(self) -> None:
        name, _ = QFileDialog.getOpenFileName(self, "Import theme", "", "Themes (*.json *.yaml *.yml)")
        if name:
            imported = import_theme(Path(name), user_dir())
            self.populate()
            self.themes.set_theme(imported.stem)
