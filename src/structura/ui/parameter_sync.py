"""Keeps the GUI parameters in step (docs/14 §3): the Parameters panel, the editor's inline sliders and the
tab's values. A change in either view updates the tab, rebuilds, and mirrors into the other view."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Slot

from ..core.lang.analysis import Analysis
from .documents import EditorTab

if TYPE_CHECKING:
    from .app_window import MainWindow


class ParameterSync(QObject):
    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.w = window
        window.parameters.changed.connect(self._from_panel)
        window.parameters.released.connect(self._released)
        window.tabs.tab_added.connect(self._watch)

    @Slot(object)
    def _watch(self, tab: EditorTab) -> None:
        tab.editor.inline_params.changed.connect(self._from_editor)
        tab.editor.inline_params.released.connect(self._released)

    @Slot(str)
    def _released(self, _name: str) -> None:
        self.w.workbench.finish_drag()

    def show(self, tab: EditorTab, analysis: Analysis) -> None:
        """After an analysis of the current tab: both views show its parameters and values."""
        self.w.parameters.show_parameters(analysis.parameters, tab.params)
        tab.editor.inline_params.show(analysis.parameters, tab.params)

    @Slot(str, float)
    def _from_panel(self, name: str, value: float) -> None:
        self.w.workbench.set_parameter(name, value, self.w.parameters.dragging())
        tab = self.w.tabs.current()
        if tab is not None:
            tab.editor.inline_params.set_value(name, value)

    @Slot(str, float)
    def _from_editor(self, name: str, value: float) -> None:
        tab = self.w.tabs.current()
        self.w.workbench.set_parameter(name, value, tab is not None and tab.editor.inline_params.dragging())
        self.w.parameters.set_value(name, value)
