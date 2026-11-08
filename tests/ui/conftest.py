"""UI test fixtures: an isolated MainWindow (temporary settings) on the offscreen platform."""

from __future__ import annotations

import os
import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot

from structura.services.settings import SettingsService
from structura.ui.app_window import MainWindow
from structura.ui.fonts import register_fonts
from structura.ui.watchdog import StallWatchdog

# docs/18 §7 sets 50 ms on the reference machine. Shared CI runners and software rendering add first-paint
# and GIL hiccups of a few hundred ms, so the default here is 500 ms; the reference machine runs the UI
# tests with STRUCTURA_STALL_MS=50. Real mistakes (a build or a render in a slot) take seconds.
STALL_BUDGET_MS = float(os.environ.get("STRUCTURA_STALL_MS", "500"))


@pytest.fixture
def window(
    qtbot: QtBot, tmp_path: Path, request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> Iterator[MainWindow]:
    if "preview" not in request.node.name:
        monkeypatch.setenv("STRUCTURA_PREVIEW", "off")  # keep the CPU renderer out of unrelated tests
    monkeypatch.setenv("STRUCTURA_THUMBNAILS", "off")  # no example-gallery renders behind every test
    register_fonts()
    settings = SettingsService(tmp_path / "settings.ini")
    settings.set_value("appearance/reduce_motion", True)  # camera moves and toasts apply at once in tests
    w = MainWindow(settings)
    qtbot.addWidget(w, before_close_func=_discard_edits)  # no "unsaved changes" dialog at teardown
    w.show()
    qtbot.wait(30)  # the first layout passes (dock sizes, the editor split) are start-up work, not stalls
    watchdog = StallWatchdog(STALL_BUDGET_MS)
    yield w
    stalls = [s for s in watchdog.stop() if ours_in_event_loop(s.stack)]
    if stalls and not request.node.get_closest_marker("allow_stalls"):
        worst = max(stalls, key=lambda s: s.milliseconds)
        pytest.fail(f"GUI thread stalled {len(stalls)}× (worst {worst.milliseconds:.0f} ms > {STALL_BUDGET_MS:.0f} ms)"
                    f"\n{worst.stack}")  # fmt: skip


FRAME = re.compile(r'File "([^"]+)", line \d+, in (\w+)')


def ours_in_event_loop(stack: str) -> bool:
    """A stall to fail on: Structura code running inside the event loop that qtbot is spinning. Work the test
    does itself (outside the loop), closing the window (lane shutdown), and time inside Qt's C++ (first
    paints, style polish) are not counted."""
    frames = FRAME.findall(stack)
    loop = max((i for i, (path, _) in enumerate(frames) if "pytestqt" in path), default=None)
    if loop is None or any(name == "closeEvent" for _, name in frames):
        return False
    return any("/src/structura/" in path for path, _ in frames[loop + 1 :])


def _discard_edits(w: MainWindow) -> None:
    for tab in w.tabs.tabs():
        tab.editor.document().setModified(False)
