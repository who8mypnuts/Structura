"""The template export sheet's pages (docs/15 §5.2): the options with the template's description and
"autosave script", the template editor (XML with its {placeholders} highlighted; edits are kept as a user
template) and the output preview (the first 64 KB)."""

from __future__ import annotations

import re

from PySide6.QtCore import Signal
from PySide6.QtGui import QSyntaxHighlighter, QTextDocument
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ...export.templates.template_file import all_templates, load_template, save_user_template
from ...themes.model import Theme
from ..fonts import use_code_font
from ..i18n import tr
from ..theming import syntax_format
from ..widgets.param_form import ParamForm

RULES = (  # (pattern, syntax role), later rules paint over earlier ones
    (r"</?[\w:]+|/?>", "keyword"),
    (r"\b[\w:]+(?==)", "set.key"),
    (r'"[^"\n]*"', "string"),
    (r"<!\[CDATA\[|\]\]>", "preprocessor"),
    (r"\{[A-Za-z0-9_.]+\}", "number"),
    (r"<!--.*?-->", "comment"),
)


class TemplateHighlighter(QSyntaxHighlighter):
    def __init__(self, document: QTextDocument, theme: Theme) -> None:
        super().__init__(document)
        self.rules = [(re.compile(p), syntax_format(theme, role)) for p, role in RULES]

    def highlightBlock(self, text: str) -> None:  # noqa: N802 - Qt override
        for pattern, fmt in self.rules:
            for m in pattern.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)


def _code_view(read_only: bool, name: str) -> QPlainTextEdit:
    view = QPlainTextEdit()
    view.setReadOnly(read_only)
    use_code_font(view)
    view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
    view.setAccessibleName(name)
    return view


class TemplatePages(QTabWidget):
    template_saved = Signal(str)  # the user template's name

    def __init__(self, form: ParamForm, theme: Theme, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.form = form
        self.setAccessibleName(tr("Template export pages"))
        self.addTab(self._options_page(), tr("Options"))
        self.addTab(self._editor_page(theme), tr("Template"))
        self.preview = _code_view(True, tr("Output preview"))
        self.preview.setPlaceholderText(tr("generating…"))
        self.addTab(self.preview, tr("Preview"))
        form.changed.connect(self._template_changed)
        self._template_changed()

    def _options_page(self) -> QWidget:
        page = QWidget()
        column = QVBoxLayout(page)
        self.description = QLabel()
        self.description.setWordWrap(True)
        self.description.setObjectName("Muted")
        self.autosave = QCheckBox(tr("Autosave the script with its seed and camera (.es next to the file)"))
        for widget in (self.description, self.form, self.autosave):
            column.addWidget(widget)
        return page

    def _editor_page(self, theme: Theme) -> QWidget:
        page = QWidget()
        column = QVBoxLayout(page)
        self.editor = _code_view(False, tr("Template text"))
        self.highlighter = TemplateHighlighter(self.editor.document(), theme)
        save = QPushButton(tr("Save as My Template…"))
        save.setToolTip(tr("Keep the edited template under a new name; it joins the template list"))
        save.clicked.connect(self._ask_save)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr("Edits are used once saved as your own template.")), 1)
        row.addWidget(save)
        column.addWidget(self.editor, 1)
        column.addLayout(row)
        return page

    def template_name(self) -> str:
        return str(self.form.values().get("template", ""))

    def _template_changed(self, *_: object) -> None:
        name = self.template_name()
        if name == getattr(self, "_shown", None):
            return
        self._shown = name
        path = all_templates().get(name)
        if path is None:
            return
        self.description.setText(load_template(path).description.strip() or tr("(no description)"))
        self.editor.setPlainText(path.read_text(encoding="utf-8"))

    def show_preview(self, text: str) -> None:
        self.preview.setPlainText(text)

    def _ask_save(self) -> None:
        name, ok = QInputDialog.getText(self, tr("Save Template"), tr("Template name"),
                                        text=f"{self.template_name()} (mine)")  # fmt: skip
        if ok and name.strip():
            self.save_as(name.strip())

    def save_as(self, name: str) -> bool:
        try:
            path = save_user_template(name, self.editor.toPlainText())
        except ValueError as exc:
            QMessageBox.warning(self, tr("Save Template"), str(exc))
            return False
        self.template_saved.emit(path.stem)
        return True
