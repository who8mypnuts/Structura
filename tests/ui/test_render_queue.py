"""The render queue and the Activity panel (docs/14 §3)."""

from __future__ import annotations

from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot

from structura.ui import render_actions
from structura.ui.app_window import MainWindow
from structura.ui.dialogs.render_output import RenderOutput


def test_queued_renders_run_in_order_and_save_with_reports(
    qtbot: QtBot, window: MainWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("{ color #f80 } sphere\n{ x 1.2 } box\n")
    qtbot.waitUntil(lambda: tab.outcome is not None, timeout=30000)
    window.render_view.samples.setValue(2)
    outputs = iter([RenderOutput(tmp_path / "first.png", None),
                    RenderOutput(tmp_path / "second.png", tmp_path / "second-report.pdf")])  # fmt: skip
    monkeypatch.setattr(render_actions, "choose_output", lambda *a, **k: next(outputs))
    window.registry.trigger("render.queue")
    window.render_actions.queue_render()
    queue = window.render_queue
    assert [e.state for e in queue.entries] == ["queued", "queued"] and window.docks["Render Queue"].isVisible()
    qtbot.waitUntil(lambda: all(e.state == "done" for e in queue.entries), timeout=180000)
    assert (tmp_path / "first.png").exists() and (tmp_path / "second-report.pdf").exists()
    assert window.queue_panel.tree.topLevelItemCount() == 2
    names = [window.activity.tree.topLevelItem(i).text(0) for i in range(window.activity.tree.topLevelItemCount())]
    assert any(name.startswith("render queue:") for name in names) and any(n.startswith("save ") for n in names)
    queue.clear_finished()
    assert not queue.entries and window.queue_panel.tree.topLevelItemCount() == 0


def test_activity_panel_is_hidden_until_asked_for(window: MainWindow) -> None:
    assert not window.docks["Activity"].isVisible()
    window.registry.trigger("view.panel.activity")
    assert window.docks["Activity"].isVisible()


def test_a_stopped_render_resumes_where_it_left_off(qtbot: QtBot, window: MainWindow) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("{ color #f80 } sphere\n{ x 1.2 } box\n")
    qtbot.waitUntil(lambda: tab.outcome is not None, timeout=30000)
    view = window.render_view
    view.samples.setValue(12)
    view.controls.denoise.setCurrentText("off")
    window.render_actions.start_render()
    qtbot.waitUntil(lambda: view.last is not None and view.last.progress.samples >= 1, timeout=60000)
    view.stop()
    qtbot.waitUntil(lambda: not window.renders.busy("render-view"), timeout=60000)
    stopped = view.last.progress.samples
    assert stopped < 12 and view.controls.resume_button.isEnabled()
    view.controls.resume_button.click()
    qtbot.waitUntil(lambda: view.last.progress.samples == 12, timeout=180000)
    assert view.last.progress.seconds >= 0 and not view.controls.resume_button.isEnabled()
