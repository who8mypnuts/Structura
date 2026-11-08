"""Timeline behaviour (docs/16 §2.2): scrubbing, playback and keying for the current tab.

A frame change applies the timeline to the tab (keyed parameters, seed, camera), then re-analyses; the
workbench rebuilds only when the program changed, so camera-only animation never rebuilds.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QTimer, Slot

from ..core.animation.camera import camera_at, has_camera_tracks, key_camera
from ..core.animation.timeline import Interp, Timeline
from .documents import EditorTab

if TYPE_CHECKING:
    from .app_window import MainWindow


class TimelineActions(QObject):
    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)
        self.w, self.panel = window, window.timeline_panel
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        p = self.panel
        p.frame_requested.connect(self.set_frame)
        p.play_toggled.connect(self.play)
        p.range_edited.connect(self._range)
        p.key_camera.connect(self.key_camera)
        p.key_params.connect(self.key_parameters)
        p.key_action.connect(self._key_action)
        p.render_animation.connect(window.animations.render)
        window.parameters.key_toggled.connect(self.toggle_parameter_key)
        window.tabs.current_tab_changed.connect(self.refresh)

    def _tab(self) -> EditorTab | None:
        return self.w.tabs.current()

    @Slot()
    def refresh(self) -> None:
        tab = self._tab()
        timeline, frame = (tab.timeline, tab.frame) if tab else (Timeline(), 0)
        self.panel.show_state(timeline, frame, self.timer.isActive())
        self.w.parameters.show_keys(timeline, frame)

    # -- frames ----------------------------------------------------------------------------------------------
    @Slot(int)
    def set_frame(self, frame: int) -> None:
        tab = self._tab()
        if tab is None:
            return
        tab.frame = max(tab.timeline.start, min(tab.timeline.end, frame))
        self._apply(tab)
        self.refresh()

    def _apply(self, tab: EditorTab) -> None:
        tl, frame = tab.timeline, tab.frame
        for name, value in tl.params_at(frame).items():
            tab.params[name] = value
            self.w.parameters.set_value(name, value)
            tab.editor.inline_params.set_value(name, value)
        seed = tl.value("seed", frame)
        if seed is not None:
            tab.seed = int(seed)
            self.w.header.set_seed(tab.seed)
        if has_camera_tracks(tl):
            self.w.viewport.set_camera(camera_at(tl, frame, self.w.viewport.camera()))
        self.w.workbench.follow_frame(tab)

    def step(self, delta: int) -> None:
        tab = self._tab()
        if tab is not None:
            self.set_frame(tab.frame + delta)

    @Slot(bool)
    def play(self, on: bool) -> None:
        tab = self._tab()
        if on and tab is not None:
            self.timer.start(max(1, round(1000 / tab.timeline.fps)))
        else:
            self.timer.stop()
        self.refresh()

    @Slot()
    def _tick(self) -> None:
        tab = self._tab()
        if tab is None:
            self.play(False)
            return
        nxt = tab.frame + 1
        self.set_frame(tab.timeline.start if nxt > tab.timeline.end else nxt)

    # -- editing ---------------------------------------------------------------------------------------------
    def _edit(self, tab: EditorTab, timeline: Timeline) -> None:
        tab.timeline = timeline
        self.refresh()

    @Slot(int, int, float)
    def _range(self, start: int, end: int, fps: float) -> None:
        tab = self._tab()
        if tab is not None:
            self._edit(tab, replace(tab.timeline, start=start, end=end, fps=fps))
            if self.timer.isActive():
                self.timer.setInterval(max(1, round(1000 / fps)))

    @Slot(str)
    def toggle_parameter_key(self, name: str) -> None:
        tab = self._tab()
        if tab is None:
            return
        target = f"param:{name}"
        if tab.timeline.has_key(target, tab.frame):
            self._edit(tab, tab.timeline.remove_key(target, tab.frame))
        else:
            value = tab.params.get(name, self._default(tab, name))
            self._edit(tab, tab.timeline.set_key(target, tab.frame, value))

    @staticmethod
    def _default(tab: EditorTab, name: str) -> float:
        params = tab.analysis.parameters if tab.analysis else ()
        return next((p.default for p in params if p.name == name), 0.0)

    @Slot()
    def key_parameters(self) -> None:
        tab = self._tab()
        if tab is None or tab.analysis is None:
            return
        timeline = tab.timeline
        for p in (p for p in tab.analysis.parameters if p.numeric):  # colours and choices do not interpolate
            timeline = timeline.set_key(f"param:{p.name}", tab.frame, tab.params.get(p.name, p.default))
        self._edit(tab, timeline)

    @Slot()
    def key_camera(self) -> None:
        tab = self._tab()
        if tab is not None:
            self._edit(tab, key_camera(tab.timeline, tab.frame, self.w.viewport.camera()))

    @Slot(str, int, str)
    def _key_action(self, target: str, frame: int, action: str) -> None:
        tab = self._tab()
        if tab is None:
            return
        if action == "delete":
            self._edit(tab, tab.timeline.remove_key(target, frame))
        else:
            self._edit(tab, tab.timeline.set_interp(target, frame, Interp(action)))
