"""The theme editor (docs/13 §8): every role grouped as in roles.toml with its colour, whether the theme sets
it or it is derived, a live preview (the whole window restyles as you edit), 'Start from accent', the
contrast report with 'Fix automatically', and duplicate / export / delete. Built-ins are duplicated on save."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core.lang.analysis import analyze
from ...services.theme import ThemeService
from ...themes.authoring import ThemeDraft, delete_user_theme
from ...themes.derive import role_groups
from ...themes.writer import to_toml
from ..editor.code_editor import CodeEditor

SAMPLE = """#version 2
// The theme editor previews every syntax role
#define angle 20 (float:0-90)
set maxdepth 40
material glass { transmission 1 roughness 0.05 }
spiral
rule spiral md 30 > stem {
  { x 1 rz angle s 0.95 hue 8 color #f80 } spiral
  box::glass
  { s (sin(30)) } sphere
}
rule stem { triangle[0,0,0;1,0,0;0,1,0] }
missing_rule
"""
FLAGS = ("bold", "italic", "underline")
PREVIEW_MS = 200


def swatch(color: str) -> QIcon:
    pixmap = QPixmap(14, 14)
    pixmap.fill(QColor(color[:7]))
    return QIcon(pixmap)


class ThemeEditor(QDialog):
    def __init__(self, themes: ThemeService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Theme editor")
        self.resize(980, 640)
        self.themes = themes
        self.draft = ThemeDraft.from_id(themes.theme.meta.id)
        self.title = QLabel()
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Role", "Colour", ""])
        self.tree.itemDoubleClicked.connect(lambda item, _col: self._pick(item))
        self.tree.currentItemChanged.connect(lambda *_: self._selection_changed())
        self.preview = CodeEditor(themes.theme)
        self.preview.setPlainText(SAMPLE)
        self.preview.setReadOnly(True)
        sample = analyze(SAMPLE)  # the semantic layer too: defined, unused and undefined rules
        self.preview.highlighter.set_analysis(sample)
        self.preview.set_diagnostics(list(sample.diagnostics))
        self.flags = {name: QCheckBox(name.title()) for name in FLAGS}
        for name, box in self.flags.items():
            box.toggled.connect(lambda on, n=name: self._set_flag(n, on))
        self.contrast = QLabel()
        self.contrast.setWordWrap(True)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(PREVIEW_MS)
        self._timer.timeout.connect(self._apply_preview)
        self._layout()
        self._refresh()

    # -- layout --------------------------------------------------------------------------------------------
    def _buttons(self, specs: tuple[tuple[str, object], ...]) -> QHBoxLayout:
        row = QHBoxLayout()
        for text, handler in specs:
            button = QPushButton(text)
            button.clicked.connect(handler)
            row.addWidget(button)
        return row

    def _layout(self) -> None:
        top = self._buttons((("Start from accent…", self.start_from_accent), ("Duplicate…", self.duplicate),
                             ("Export…", self.export), ("Delete", self.delete)))  # fmt: skip
        top.insertWidget(0, self.title, 1)
        right = QVBoxLayout()
        right.addWidget(self.preview, 1)
        flags = QHBoxLayout()
        for box in self.flags.values():
            flags.addWidget(box)
        reset = QPushButton("Reset role")
        reset.clicked.connect(self._reset_role)
        flags.addStretch(1)
        flags.addWidget(reset)
        right.addLayout(flags)
        right.addWidget(self.contrast)
        right.addLayout(self._buttons((("Fix contrast automatically", self.fix_contrast),)))
        body = QHBoxLayout()
        body.addWidget(self.tree, 1)
        body.addLayout(right, 1)
        bottom = self._buttons((("Save", self.save), ("Cancel", self.reject)))
        bottom.insertStretch(0, 1)
        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addLayout(body, 1)
        layout.addLayout(bottom)

    # -- model → view ----------------------------------------------------------------------------------------
    def _refresh(self) -> None:
        theme = self.draft.theme()
        meta = theme.meta
        note = " (built-in: saving makes a copy)" if self.draft.read_only else ""
        self.title.setText(f"<b>{meta.name}</b> · {meta.kind}{note}")
        selected = self._role()
        self.tree.clear()
        for group, roles in role_groups().items():
            parent = QTreeWidgetItem(self.tree, [group])
            for role in roles:
                own = self.draft.override(role) is not None
                item = QTreeWidgetItem(parent, [role, theme[role], "set" if own else "derived"])
                item.setIcon(1, swatch(theme[role]))
                item.setData(0, Qt.ItemDataRole.UserRole, role)
                font = item.font(0)
                font.setBold(own)
                item.setFont(0, font)
                if role == selected:
                    self.tree.setCurrentItem(item)
            parent.setExpanded(group in ("ui", "editor", "syntax"))
        self.tree.resizeColumnToContents(0)
        fixes = self.draft.contrast_fixes()
        self.contrast.setText(
            "Contrast: all pairs pass." if not fixes else
            f"Contrast: {len(fixes)} role(s) adjusted to stay readable: {', '.join(sorted(fixes))}"
        )  # fmt: skip
        self.preview.set_theme(theme)
        self._timer.start()

    def _role(self) -> str | None:
        item = self.tree.currentItem()
        role = item.data(0, Qt.ItemDataRole.UserRole) if item is not None else None
        return str(role) if role else None

    def _selection_changed(self) -> None:
        role = self._role()
        syntax = bool(role and role.startswith("syntax."))
        for name, box in self.flags.items():
            box.setEnabled(syntax)
            box.blockSignals(True)
            box.setChecked(syntax and role is not None and self.draft.flag(role, name))
            box.blockSignals(False)

    def _apply_preview(self) -> None:
        self.themes.preview(self.draft.theme())

    # -- editing ---------------------------------------------------------------------------------------------
    def _pick(self, item: QTreeWidgetItem) -> None:
        role = item.data(0, Qt.ItemDataRole.UserRole)
        if not role:
            return
        current = QColor(item.text(1)[:7])
        chosen = QColorDialog.getColor(current, self, str(role))
        if chosen.isValid():
            self.draft.set_role(str(role), chosen.name().upper())
            self._refresh()

    def _reset_role(self) -> None:
        role = self._role()
        if role:
            self.draft.reset_role(role)
            self._refresh()

    def _set_flag(self, flag: str, on: bool) -> None:
        role = self._role()
        if role:
            self.draft.set_flag(role, flag, on)
            self._refresh()

    def fix_contrast(self) -> None:
        self.draft.fix_contrast()
        self._refresh()

    def start_from_accent(self) -> None:
        accent = QColorDialog.getColor(QColor(self.draft.theme()["ui.accent"][:7]), self, "Accent colour")
        if not accent.isValid():
            return
        kinds = ["Dark", "Light"]
        kind, ok = QInputDialog.getItem(self, "Start from accent", "Kind", kinds, 0, False)
        name, ok2 = QInputDialog.getText(self, "Start from accent", "Name", text="My theme")
        if ok and ok2 and name:
            self.draft = ThemeDraft.from_accent(name, accent.name().upper(), kind == "Dark")
            self._refresh()

    def duplicate(self) -> None:
        name, ok = QInputDialog.getText(self, "Duplicate theme", "Name", text=f"{self.draft.theme().meta.name} copy")
        if ok and name:
            self.draft = self.draft.duplicate(name)
            self._refresh()

    def export(self) -> None:
        name, _ = QFileDialog.getSaveFileName(self, "Export theme", f"{self.draft.id}.toml", "Theme (*.toml)")
        if name:
            Path(name).write_text(to_toml(self.draft.data), encoding="utf-8")

    def delete(self) -> None:
        if self.draft.read_only or not delete_user_theme(self.draft.id):
            QMessageBox.information(self, "Delete theme", "Built-in themes cannot be deleted.")
            return
        self.themes.reload("structura-dark")
        self.draft = ThemeDraft.from_id("structura-dark")
        self._refresh()

    # -- closing ---------------------------------------------------------------------------------------------
    def save(self) -> None:
        if self.draft.read_only:
            self.draft = self.draft.duplicate(f"{self.draft.theme().meta.name} (edited)")
        self.draft.save()
        self.themes.reload(self.draft.id)
        self.accept()

    def reject(self) -> None:
        self._timer.stop()
        self.themes.revert()
        super().reject()
