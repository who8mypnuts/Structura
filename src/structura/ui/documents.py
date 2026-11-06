"""Editor tabs: one EditorTab per open script, holding its latest analysis and build (docs/14 §2)."""

from __future__ import annotations

import uuid
from pathlib import Path

from PySide6.QtCore import QFileSystemWatcher, Signal, Slot
from PySide6.QtWidgets import QMessageBox, QTabWidget, QVBoxLayout, QWidget

from ..core.lang.analysis import Analysis
from ..core.lang.source import detect_dialect
from ..services.build import BuildOutcome
from ..themes.model import Theme
from .editor.code_editor import CodeEditor
from .editor.completion import CompletionController
from .editor.find_bar import FindBar
from .editor.signature import SignatureHelp

NEW_SCRIPT = """// A new Structura script (EisenScript v1, Structure Synth compatible)
set maxdepth 20
set background #1b1f27

R1

rule R1 {
  { x 1.2 rz 12 ry 6 s 0.95 hue 8 } R1
  { color #4ad } box
}
"""


def read_text(path: Path) -> str:
    data = path.read_bytes()
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")  # legacy Windows files (docs/12 §2.1)


class EditorTab(QWidget):
    edited = Signal()

    def __init__(self, theme: Theme, text: str = NEW_SCRIPT, path: Path | None = None) -> None:
        super().__init__()
        self.doc_id = uuid.uuid4().hex[:10]
        self.path = path
        self.version = 0
        self.seed = 0
        self.params: dict[str, float] = {}
        self.analysis: Analysis | None = None
        self.outcome: BuildOutcome | None = None
        self.built_digest = ""
        self.camera_applied = False
        self.editor = CodeEditor(theme)
        self.completion = CompletionController(self.editor)
        self.signature_help = SignatureHelp(self.editor)
        self.editor.setPlainText(text)
        self.editor.document().setModified(False)
        self.find_bar = FindBar(self.editor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.editor, 1)
        layout.addWidget(self.find_bar)
        self.editor.textChanged.connect(self._changed)

    @Slot()
    def _changed(self) -> None:
        self.version += 1
        self.edited.emit()

    def text(self) -> str:
        return self.editor.toPlainText()

    @property
    def dialect(self) -> int:
        return detect_dialect(self.text())

    @property
    def modified(self) -> bool:
        return self.editor.document().isModified()

    @property
    def title(self) -> str:
        name = self.path.name if self.path else "Untitled"
        return f"{name} ●" if self.modified else name

    def reload(self, text: str) -> None:
        """Replace the text from disk, keeping the cursor line."""
        line = self.editor.textCursor().blockNumber()
        self.editor.setPlainText(text)
        self.editor.document().setModified(False)
        block = self.editor.document().findBlockByNumber(min(line, self.editor.blockCount() - 1))
        cursor = self.editor.textCursor()
        cursor.setPosition(block.position())
        self.editor.setTextCursor(cursor)

    def save(self, path: Path | None = None) -> None:
        target = path or self.path
        if target is None:
            raise ValueError("no path to save to")
        target.write_text(self.text(), encoding="utf-8")
        self.path = target
        self.editor.document().setModified(False)


class DocumentTabs(QTabWidget):
    current_tab_changed = Signal(object)  # EditorTab | None
    tab_edited = Signal(object)  # EditorTab
    tab_added = Signal(object)  # EditorTab
    external_change = Signal(object)  # EditorTab whose file changed on disk while it had unsaved edits

    def __init__(self, theme: Theme, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.theme = theme
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setDocumentMode(True)
        self.tabCloseRequested.connect(self.close_tab)
        self.currentChanged.connect(lambda _i: self.current_tab_changed.emit(self.current()))
        self.watcher = QFileSystemWatcher(self)
        self.watcher.fileChanged.connect(self._file_changed)

    def tabs(self) -> list[EditorTab]:
        return [w for i in range(self.count()) if isinstance(w := self.widget(i), EditorTab)]

    def current(self) -> EditorTab | None:
        widget = self.currentWidget()
        return widget if isinstance(widget, EditorTab) else None

    def add(self, tab: EditorTab) -> EditorTab:
        tab.edited.connect(self._edited)
        tab.editor.modificationChanged.connect(self._retitle)
        self.watch(tab)
        self.tab_added.emit(tab)
        self.setCurrentIndex(self.addTab(tab, tab.title))
        return tab

    def new_document(self, text: str = NEW_SCRIPT, path: Path | None = None) -> EditorTab:
        return self.add(EditorTab(self.theme, text, path))

    def open_file(self, path: Path) -> EditorTab:
        for tab in self.tabs():
            if tab.path is not None and tab.path.resolve() == path.resolve():
                self.setCurrentWidget(tab)
                return tab
        return self.new_document(read_text(path), path)

    def watch(self, tab: EditorTab) -> None:
        if tab.path is not None and str(tab.path) not in self.watcher.files():
            self.watcher.addPath(str(tab.path))

    @Slot(str)
    def _file_changed(self, name: str) -> None:
        """Reload silently when there are no local edits; otherwise let the window ask."""
        for tab in self.tabs():
            if tab.path is None or str(tab.path) != name or not tab.path.exists():
                continue
            text = read_text(tab.path)
            if text == tab.text():
                continue
            if tab.modified:
                self.external_change.emit(tab)
            else:
                tab.reload(text)
        self.watcher.addPath(name)  # editors that save by replacing the file drop the watch

    @Slot()
    def _edited(self) -> None:
        tab = self.sender()
        if isinstance(tab, EditorTab):
            self.tab_edited.emit(tab)

    @Slot()
    def _retitle(self) -> None:
        for i, tab in enumerate(self.tabs()):
            self.setTabText(i, tab.title)
            self.setTabToolTip(i, str(tab.path or "Unsaved script"))

    def close_tab(self, index: int) -> bool:
        tab = self.widget(index)
        if isinstance(tab, EditorTab) and tab.modified:
            answer = QMessageBox.question(
                self, "Unsaved changes", f"Close {tab.title} without saving?",
                QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            )  # fmt: skip
            if answer != QMessageBox.StandardButton.Discard:
                return False
        self.removeTab(index)
        if isinstance(tab, EditorTab):
            tab.deleteLater()
        return True

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        for tab in self.tabs():
            tab.editor.set_theme(theme)
