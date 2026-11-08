"""Inline parameter sliders (docs/12 §2.3): a compact slider after each '#define NAME V (float:A-B)' or
'#param' line, mirroring the Parameters panel. Sliders follow scrolling and hide with folded lines."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QRect, Signal

from ...core.lang.legacy.preprocessor import GuiParameter
from ..widgets.param_slider import ParamSlider

if TYPE_CHECKING:
    from .code_editor import CodeEditor

GAP = "    "  # space between the line's text and its slider


class InlineParams(QObject):
    changed = Signal(str, float)
    released = Signal(str)

    def __init__(self, editor: CodeEditor) -> None:
        super().__init__(editor)
        self.editor = editor
        self.sliders: list[ParamSlider] = []
        self._signature: tuple[tuple[str, str, float, float, int], ...] = ()
        editor.updateRequest.connect(lambda *_: self.place())

    def show(self, params: tuple[GuiParameter, ...], values: dict[str, float]) -> None:
        """Recreate the sliders when the declarations change; otherwise only refresh their values."""
        signature = tuple((p.name, p.kind, p.minimum, p.maximum, p.line) for p in params)
        if signature != self._signature:
            self._signature = signature
            for slider in self.sliders:
                slider.deleteLater()
            self.sliders = []
            for p in (p for p in params if p.numeric):  # colours, switches and choices: the Parameters panel
                slider = ParamSlider(p, values.get(p.name, p.default), compact=True, parent=self.editor.viewport())
                slider.changed.connect(self.changed)
                slider.released.connect(self.released)
                self.sliders.append(slider)
        for slider in self.sliders:
            slider.set_value(values.get(slider.param.name, slider.param.default))
        self.place()

    def dragging(self) -> bool:
        return any(slider.dragging for slider in self.sliders)

    def set_value(self, name: str, value: float) -> None:
        for slider in self.sliders:
            if slider.param.name == name:
                slider.set_value(value)

    def place(self) -> None:
        editor, metrics = self.editor, self.editor.fontMetrics()
        offset, margin = editor.contentOffset(), editor.document().documentMargin()
        for slider in self.sliders:
            block = editor.document().findBlockByNumber(slider.param.line)
            if not block.isValid() or not block.isVisible():
                slider.hide()
                continue
            top = editor.blockBoundingGeometry(block).translated(offset).top()
            x = round(offset.x() + margin + metrics.horizontalAdvance(block.text() + GAP))
            height = metrics.height()
            slider.setGeometry(QRect(x, round(top), slider.width(), height))
            slider.setVisible(-height < top < editor.viewport().height())
