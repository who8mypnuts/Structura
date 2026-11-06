"""Provenance hover (docs/12 §2.3, docs/08 §6): resting the mouse on a call site in the editor highlights
every instance that call produced in the viewport. (Clicking in the viewport already flashes the call site.)
Only primitive call sites map to instances: a rule call's descendants are not tracked per instance."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

import numpy as np
from PySide6.QtCore import QObject, QTimer

from .documents import EditorTab

if TYPE_CHECKING:
    from .app_window import MainWindow

HOVER_MS = 90


class ProvenanceHover(QObject):
    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.w = window
        self._pending: tuple[EditorTab, int] | None = None
        self._shown: int | None = None  # the action currently highlighted
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(HOVER_MS)
        self._timer.timeout.connect(self._apply)
        window.tabs.tab_added.connect(self._watch)

    def _watch(self, tab: EditorTab) -> None:
        tab.editor.hovered.connect(partial(self._hovered, tab))

    def _hovered(self, tab: EditorTab, position: int) -> None:
        self._pending = (tab, position)
        self._timer.start()

    def rows_for(self, tab: EditorTab, position: int) -> tuple[int | None, np.ndarray]:
        """(action, SceneIR rows) for a text position of ``tab``; no rows when the scene is out of date."""
        analysis, outcome = tab.analysis, tab.outcome
        current = analysis is not None and analysis.version == tab.version and analysis.digest == tab.built_digest
        if position < 0 or outcome is None or not current or analysis is None:
            return None, np.zeros(0, np.int64)  # the scene or the positions are out of date
        action = analysis.action_at(position)
        if action is None:
            return None, np.zeros(0, np.int64)
        return action, np.nonzero(outcome.scene.source == action)[0]

    def _apply(self) -> None:
        if self._pending is None:
            return
        tab, position = self._pending
        action, rows = self.rows_for(tab, position) if tab is self.w.tabs.current() else (None, np.zeros(0))
        if action == self._shown:
            return
        self._shown = action if len(rows) else None
        scene = tab.outcome.scene if tab.outcome is not None else None
        self.w.viewport.highlight(rows if len(rows) else None, len(scene) if scene is not None else 0)
