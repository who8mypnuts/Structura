"""Editor tabs: one EditorTab per open script, holding its latest analysis and build (docs/14 §2)."""

from __future__ import annotations

import uuid
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QFileSystemWatcher, Qt, Signal, Slot
from PySide6.QtWidgets import QMessageBox, QSplitter, QTabWidget, QVBoxLayout, QWidget

from ..core import text_file
from ..core.animation.timeline import Timeline
from ..core.lang.analysis import Analysis
from ..core.lang.source import detect_dialect, is_javascript
from ..core.scene.camera import Camera
from ..core.text_file import TextFile
from ..services.build import BuildOutcome
from ..themes.model import Theme
from .editor.breadcrumbs import Breadcrumbs
from .editor.code_editor import CodeEditor
from .editor.completion import CompletionController
from .editor.find_bar import FindBar
from .editor.signature import SignatureHelp
from .panels.history import Snapshot

NEW_SCRIPT = """// A new Structura script (EisenScript v1, Structure Synth compatible)
set maxdepth 20
set background #1b1f27

R1

rule R1 {
  { x 1.2 rz 12 ry 6 s 0.95 hue 8 } R1
  { color #4ad } box
}
"""


class EditorTab(QWidget):
    edited = Signal()
    saved = Signal()  # after writing the file (its encoding may have changed)
    retitled = Signal()  # the title changed for another reason than the modified flag (e.g. a project)

    def __init__(self, theme: Theme, text: str = NEW_SCRIPT, path: Path | None = None,
                 file: TextFile | None = None) -> None:  # fmt: skip
        super().__init__()
        self.doc_id = uuid.uuid4().hex[:10]
        self.path = path
        self.file = file or TextFile(text)  # encoding and line endings used when saving
        self.version = 0
        self.seed = 0
        self.params: dict[str, float] = {}
        self.timeline = Timeline()  # keyframes (docs/16 §2); saved in the project
        self.frame = 0  # the timeline's current frame
        self.bookmarks: dict[str, Camera] = {}  # saved views (Camera panel); saved in the project
        self.snapshots: list[Snapshot] = []  # History panel (kept for the session)
        self.suggested_name = ""  # an unsaved copy's name (examples): shown in the tab and offered by Save As
        self.render_overrides: dict[str, object] = {}  # Render Settings edits over the script's values
        self.project_path: Path | None = None  # the .structura file this tab was opened from or saved to
        self.initial_camera: Camera | None = None  # a project's camera, used instead of the script's at first
        self.analysis: Analysis | None = None
        self.outcome: BuildOutcome | None = None
        self.built_digest = ""
        self.camera_applied = False
        self.camera_locked = False  # Camera ▸ Lock to Script: every build shows the script's camera
        self.editor = CodeEditor(theme)
        self.completion = CompletionController(self.editor)
        self.signature_help = SignatureHelp(self.editor)
        self.editor.setPlainText(text)
        self.editor.document().setModified(False)
        self.find_bar = FindBar(self.editor)
        self.secondary: CodeEditor | None = None  # split view: a second view of the same document
        self._secondary_assist: tuple[CompletionController, SignatureHelp] | None = None
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.editor)
        self.breadcrumbs = Breadcrumbs(self.editor)
        self.breadcrumbs.set_file(self.display_name)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.breadcrumbs)
        layout.addWidget(self.splitter, 1)
        layout.addWidget(self.find_bar)
        self.editor.textChanged.connect(self._changed)

    @Slot()
    def _changed(self) -> None:
        self.version += 1
        self.edited.emit()

    def text(self) -> str:
        return self.editor.toPlainText()

    def views(self) -> list[CodeEditor]:
        return [self.editor] + ([self.secondary] if self.secondary is not None else [])

    def toggle_split(self) -> None:
        """Show or hide a second view of this script beside the first (own cursor and scroll position)."""
        if self.secondary is not None:
            self.editor.mirrors.remove(self.secondary)
            self.secondary.deleteLater()
            self.secondary, self._secondary_assist = None, None
            self.editor.setFocus()
            return
        view = CodeEditor(self.editor.theme, shared=self.editor)
        view.set_options(self.editor.options)
        view.set_analysis(self.editor.analysis)
        view.set_diagnostics(self.editor.diagnostics)
        view.setTextCursor(self.editor.textCursor())
        self._secondary_assist = (CompletionController(view), SignatureHelp(view))
        self.secondary = view
        self.splitter.addWidget(view)
        view.setFocus()

    @property
    def dialect(self) -> int:
        return detect_dialect(self.text())

    @property
    def language_label(self) -> str:
        """Status-bar label: 'JavaScript' for '#javascript' scripts, else 'EisenScript v1' / 'v2'."""
        return "JavaScript" if self.is_javascript else f"EisenScript v{self.dialect}"

    @property
    def is_javascript(self) -> bool:
        return is_javascript(self.text())

    @property
    def modified(self) -> bool:
        return self.editor.document().isModified()

    @property
    def display_name(self) -> str:
        source = self.project_path or self.path
        return source.name if source else (self.suggested_name or "Untitled")

    @property
    def title(self) -> str:
        return f"{self.display_name} ●" if self.modified else self.display_name

    def retitle(self) -> None:
        self.retitled.emit()

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
        self.file = text_file.write(target, replace(self.file, text=self.text()))
        self.path = target
        self.editor.document().setModified(False)
        self.saved.emit()


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
        tab.retitled.connect(self._retitle)
        self.watch(tab)
        self.tab_added.emit(tab)
        self.setCurrentIndex(self.addTab(tab, tab.title))
        return tab

    def new_document(self, text: str = NEW_SCRIPT, path: Path | None = None, file: TextFile | None = None) -> EditorTab:
        return self.add(EditorTab(self.theme, text, path, file))

    def open_file(self, path: Path) -> EditorTab:
        for tab in self.tabs():
            if tab.path is not None and tab.path.resolve() == path.resolve():
                self.setCurrentWidget(tab)
                return tab
        file = text_file.read(path)
        return self.new_document(file.text, path, file)

    def watch(self, tab: EditorTab) -> None:
        if tab.path is not None and str(tab.path) not in self.watcher.files():
            self.watcher.addPath(str(tab.path))

    @Slot(str)
    def _file_changed(self, name: str) -> None:
        """Reload silently when there are no local edits; otherwise let the window ask."""
        for tab in self.tabs():
            if tab.path is None or str(tab.path) != name or not tab.path.exists():
                continue
            text = text_file.read_script(tab.path)
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
            tab.breadcrumbs.set_file(tab.display_name)
            self.setTabToolTip(i, str(tab.project_path or tab.path or "Unsaved script"))

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
