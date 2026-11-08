"""Inspector panel (docs/14 §3, docs/08 §6): the picked object — kind, generation, tag, colour, position,
size and the call site that made it — and selections of everything alike (same rule, tag or generation),
shown tinted in the viewport."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.lang.analysis import Analysis
from ...core.scene.ir import PrimitiveKind, SceneIR
from ..i18n import tr

FIELDS = ("Object", "Generation", "Tag", "Colour", "Position", "Size", "Source")


def _vec(v: np.ndarray) -> str:
    return "(" + ", ".join(f"{round(float(c), 4) + 0.0:g}" for c in v) + ")"


class InspectorPanel(QWidget):
    go_to_source = Signal(int)  # text position of the call site
    select_rows = Signal(object)  # np.ndarray of SceneIR rows, or None to clear
    isolate_rows = Signal(object)  # show only these rows in the viewport; None: show everything
    ancestry_requested = Signal(int)  # SceneIR row: trace the rule applications that made it

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.scene: SceneIR | None = None
        self.row: int | None = None
        self.selected: np.ndarray | None = None  # the last "Same …" selection
        self._span_start: int | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addLayout(self._form())
        self.source_button = QPushButton(tr("Go to Source"))
        self.source_button.clicked.connect(self._go)
        layout.addWidget(self.source_button)
        self._selection_box(layout)
        self._ancestry_box(layout)
        self.show_pick(None, None, None)

    def _form(self) -> QFormLayout:
        self.labels = {name: QLabel("—") for name in FIELDS}
        titles = {"Object": tr("Object"), "Generation": tr("Generation"), "Tag": tr("Tag"), "Colour": tr("Colour"),
                  "Position": tr("Position"), "Size": tr("Size"), "Source": tr("Source")}  # fmt: skip
        form = QFormLayout()
        for name, label in self.labels.items():
            label.setWordWrap(True)
            label.setAccessibleName(titles[name])
            form.addRow(titles[name], label)
        return form

    def _selection_box(self, layout: QVBoxLayout) -> None:
        grid = QGridLayout()
        self.buttons: dict[str, QPushButton] = {}
        similar = (("rule", tr("Same Call Site")), ("tag", tr("Same Tag")), ("generation", tr("Same Generation")),
                   ("kind", tr("Same Kind")))  # fmt: skip
        for n, (key, title) in enumerate(similar):
            button = self.buttons[key] = QPushButton(title)
            button.clicked.connect(lambda _=False, k=key: self._select(k))
            grid.addWidget(button, n // 2, n % 2)
        clear = QPushButton(tr("Clear Selection"))
        clear.clicked.connect(lambda: self.select_rows.emit(None))
        isolate, show_all = QPushButton(tr("Isolate Selection")), QPushButton(tr("Show All"))
        isolate.setToolTip(tr("Hide everything else in the viewport (renders and exports are not affected)"))
        isolate.clicked.connect(lambda: self.isolate_rows.emit(self.selected) if self.selected is not None else None)
        show_all.clicked.connect(lambda: self.isolate_rows.emit(None))
        self.selection = QLabel("")
        self.selection.setObjectName("Muted")
        row = QHBoxLayout()
        row.addWidget(isolate)
        row.addWidget(show_all)
        layout.addLayout(grid)
        layout.addWidget(clear)
        layout.addLayout(row)
        layout.addWidget(self.selection)

    def show_pick(self, scene: SceneIR | None, analysis: Analysis | None, row: int | None, text: str = "") -> None:
        """``text``: the script (for the call site's line number)."""
        self.scene, self.row = scene, row
        picked = scene is not None and row is not None and 0 <= row < len(scene)
        for button in (*self.buttons.values(), self.source_button, self.ancestry_button):
            button.setEnabled(picked)
        self.ancestry.clear()
        if not picked:
            for label in self.labels.values():
                label.setText("—")
            self.labels["Object"].setText(tr("Click an object in the viewport"))
            return
        assert scene is not None and row is not None
        self._fill(scene, analysis, row, text)

    def _fill(self, scene: SceneIR, analysis: Analysis | None, row: int, text: str) -> None:
        linear = scene.xform[row][:, :3]
        r, g, b, a = (float(c) for c in scene.rgba[row])
        hex_colour = "#" + "".join(f"{round(c * 255):02x}" for c in (r, g, b))
        span = analysis.action_span(int(scene.source[row])) if analysis is not None else None
        self._span_start = span.start if span is not None else None
        line = ""
        if span is not None:
            line = tr("line {line}").format(line=text.count("\n", 0, span.start) + 1)
        values = {
            "Object": f"{PrimitiveKind(int(scene.kind[row])).name.lower()} #{row:,}",
            "Generation": f"{int(scene.generation[row]):,}",
            "Tag": scene.tags[int(scene.tag[row])] or "—" if scene.tags else "—",
            "Colour": f'<span style="color:{hex_colour}">■</span> {hex_colour}' + (f" · α {a:.2f}" if a < 1 else ""),
            "Position": _vec(scene.xform[row][:, 3]),
            "Size": " × ".join(f"{float(v):.4g}" for v in np.linalg.norm(linear, axis=0)),
            "Source": line or "—",
        }
        for name, value in values.items():
            self.labels[name].setText(value)
        self.source_button.setEnabled(self._span_start is not None)

    def _ancestry_box(self, layout: QVBoxLayout) -> None:
        self.ancestry_button = QPushButton(tr("Show Ancestry"))
        self.ancestry_button.setToolTip(tr("The rules that made this object (re-runs the build in trace mode)"))
        self.ancestry_button.clicked.connect(self._request_ancestry)
        self.ancestry = QListWidget()
        self.ancestry.setAccessibleName(tr("Ancestry"))
        self.ancestry.itemActivated.connect(self._ancestor)
        self.ancestry.itemClicked.connect(self._ancestor)
        layout.addWidget(self.ancestry_button)
        layout.addWidget(self.ancestry, 1)

    def _request_ancestry(self) -> None:
        if self.row is not None:
            self.ancestry.clear()
            self.ancestry.addItem(tr("Tracing…"))
            self.ancestry_requested.emit(self.row)

    def show_ancestry(self, lines: list[tuple[str, int | None]]) -> None:
        """(text, source position or None) per step, from the top level down to the object."""
        self.ancestry.clear()
        for depth, (text, position) in enumerate(lines):
            item = QListWidgetItem(("  " * min(depth, 12)) + text)
            item.setData(Qt.ItemDataRole.UserRole, position)
            self.ancestry.addItem(item)

    def _ancestor(self, item: QListWidgetItem) -> None:
        position = item.data(Qt.ItemDataRole.UserRole)
        if position is not None:
            self.go_to_source.emit(int(position))

    def _go(self) -> None:
        if self._span_start is not None:
            self.go_to_source.emit(self._span_start)

    def rows_like(self, key: str) -> np.ndarray:
        """The SceneIR rows that share the picked object's call site, tag, generation or kind."""
        assert self.scene is not None and self.row is not None
        column = {"rule": self.scene.source, "tag": self.scene.tag, "generation": self.scene.generation,
                  "kind": self.scene.kind}[key]  # fmt: skip
        return np.flatnonzero(column == column[self.row])

    def _select(self, key: str) -> None:
        if self.scene is None or self.row is None:
            return
        rows = self.selected = self.rows_like(key)
        self.selection.setText(tr("{count} objects selected").format(count=f"{len(rows):,}"))
        self.select_rows.emit(rows)
