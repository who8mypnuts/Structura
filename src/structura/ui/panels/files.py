"""Files panel (docs/14 §3): the scripts, projects and templates in a folder. It follows the current script's
folder until the user opens a folder of their own. QFileSystemModel reads the disk on its own thread, so the
GUI never waits for a slow drive."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QDir, QModelIndex, QPoint, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog,
    QFileSystemModel,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from ..i18n import tr

PATTERNS = ["*.es", "*.structura", "*.rendertemplate", "*.py", "*.png", "*.exr"]
NEW_SCRIPT = "// A new EisenScript\nset maxdepth 100\nbox\n"


class FilesPanel(QWidget):
    open_path = Signal(Path)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.model = QFileSystemModel(self)
        self.model.setNameFilters(PATTERNS)
        self.model.setNameFilterDisables(False)  # hide other files instead of greying them out
        self.model.setFilter(QDir.Filter.AllDirs | QDir.Filter.Files | QDir.Filter.NoDotAndDotDot)
        self.tree = QTreeView()
        self.tree.setAccessibleName(tr("Files"))
        self.tree.setModel(self.model)
        for column in (1, 2, 3):
            self.tree.hideColumn(column)  # name only: size, type and date do not fit the side bar
        self.tree.setHeaderHidden(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._menu)
        self.tree.activated.connect(self._activate)
        self.folder_label = QLabel()
        self.folder_label.setObjectName("Muted")
        self.folder_label.setWordWrap(True)
        choose = QPushButton(tr("Open Folder…"))
        choose.clicked.connect(self.choose_folder)
        row = QHBoxLayout()
        row.addWidget(self.folder_label, 1)
        row.addWidget(choose)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addLayout(row)
        layout.addWidget(self.tree, 1)
        self.pinned = False  # True once the user chose a folder: it no longer follows the current script
        self.folder: Path | None = None
        self.set_folder(Path.home())

    def set_folder(self, folder: Path) -> None:
        self.folder = folder
        self.tree.setRootIndex(self.model.setRootPath(str(folder)))
        self.folder_label.setText(folder.name or str(folder))
        self.folder_label.setToolTip(str(folder))

    def follow(self, script: Path | None) -> None:
        """The current tab changed: show its folder (unless the user picked one)."""
        if script is not None and not self.pinned and script.parent != self.folder:
            self.set_folder(script.parent)

    def choose_folder(self) -> None:
        name = QFileDialog.getExistingDirectory(self, tr("Open Folder"), str(self.folder or Path.home()))
        if name:
            self.pinned = True
            self.set_folder(Path(name))

    def path_at(self, index: QModelIndex) -> Path:
        return Path(self.model.filePath(index))

    def _activate(self, index: QModelIndex) -> None:
        path = self.path_at(index)
        if path.is_file() and path.suffix in (".es", ".structura", ".png", ".exr"):
            self.open_path.emit(path)

    def _menu(self, position: QPoint) -> None:
        index = self.tree.indexAt(position)
        path = self.path_at(index) if index.isValid() else self.folder
        if path is None:
            return
        folder = path if path.is_dir() else path.parent
        menu = QMenu(self)
        if path.is_file():
            menu.addAction(tr("Open")).triggered.connect(lambda: self.open_path.emit(path))
            menu.addAction(tr("Rename…")).triggered.connect(lambda: self.rename(path))
            menu.addAction(tr("Delete…")).triggered.connect(lambda: self.delete(path))
        menu.addAction(tr("New Script Here…")).triggered.connect(lambda: self.new_script(folder))
        menu.addAction(tr("Show in File Manager")).triggered.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
        )
        menu.exec(self.tree.viewport().mapToGlobal(position))

    def new_script(self, folder: Path, name: str | None = None) -> Path | None:
        if name is None:
            name, ok = QInputDialog.getText(self, tr("New Script"), tr("File name"), text="untitled.es")
            if not ok or not name.strip():
                return None
        path = folder / (name if name.endswith(".es") else f"{name}.es")
        if path.exists():
            QMessageBox.warning(self, tr("New Script"), tr("{name} already exists.").format(name=path.name))
            return None
        path.write_text(NEW_SCRIPT, encoding="utf-8")
        self.open_path.emit(path)
        return path

    def rename(self, path: Path, name: str | None = None) -> Path | None:
        if name is None:
            name, ok = QInputDialog.getText(self, tr("Rename"), tr("New name"), text=path.name)
            if not ok or not name.strip() or name == path.name:
                return None
        target = path.with_name(name)
        if target.exists():
            QMessageBox.warning(self, tr("Rename"), tr("{name} already exists.").format(name=target.name))
            return None
        return path.rename(target)

    def delete(self, path: Path, confirmed: bool = False) -> bool:
        question = tr("Delete {name}? This cannot be undone.").format(name=path.name)
        buttons = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        if (
            not confirmed
            and QMessageBox.question(self, tr("Delete"), question, buttons) != QMessageBox.StandardButton.Yes
        ):
            return False
        path.unlink()
        return True
