"""Build ▸ Build Limits… and Show Ancestry, and the capped builds while a parameter slider is dragged
(docs/04 §4, docs/14 §4.1)."""

from __future__ import annotations

import pytest
from pytestqt.qtbot import QtBot

from structura.services.build import PREVIEW_OBJECTS, BuildLimits, BuildRequest
from structura.ui.app_window import MainWindow
from structura.ui.dialogs.build_limits import BuildLimitsDialog


def test_limits_are_stored_applied_and_reported(qtbot: QtBot, window: MainWindow) -> None:
    dialog = BuildLimitsDialog(window.settings, window)
    dialog.form.set_values({"build/max_objects": 50})
    window.workbench.limits = dialog.apply()
    assert window.workbench.limits == BuildLimits(max_objects=50) and window.settings.value("build/max_objects") == 50
    tab = window.docs.new_script()
    tab.editor.setPlainText("set maxdepth 12\nR\nrule R { { x 1 } R { y 1 } R box }\n")
    qtbot.waitUntil(lambda: "Build stopped at" in window.status.currentMessage(), timeout=30000)
    assert "object limit" in window.status.currentMessage()


def test_dragging_a_slider_caps_the_build_until_release(window: MainWindow, monkeypatch: pytest.MonkeyPatch) -> None:
    requests: list[BuildRequest] = []
    monkeypatch.setattr(window.workbench.builds, "request", requests.append)
    tab = window.docs.new_script()
    tab.analysis = None
    window.workbench.dragging = True
    from structura.core.lang.analysis import analyze  # noqa: PLC0415

    window.workbench._start_build(tab, analyze("box\n"))
    assert requests[-1].limits.max_objects == PREVIEW_OBJECTS
    monkeypatch.setattr(window.workbench, "build", lambda tab=None: requests.append(BuildRequest("again", None)))  # type: ignore[arg-type]
    window.workbench.finish_drag()
    assert not window.workbench.dragging and requests[-1].doc_id == "again"


def test_show_ancestry_from_the_build_menu(qtbot: QtBot, window: MainWindow) -> None:
    tab = window.docs.new_script()
    window.registry.trigger("build.ancestry")
    assert "Pick an object" in window.status.currentMessage()
    tab.editor.setPlainText("R\nrule R md 3 { { x 1 } R box }\n")
    qtbot.waitUntil(lambda: tab.outcome is not None and tab.analysis is not None, timeout=30000)
    window.on_picked(0)
    window.registry.trigger("build.ancestry")
    qtbot.waitUntil(lambda: window.inspector.ancestry.count() > 1, timeout=30000)


def test_a_repeated_build_comes_from_the_scene_cache(
    qtbot: QtBot, window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("3 * { x 1 } box\n")
    qtbot.waitUntil(lambda: tab.outcome is not None and tab.analysis is not None, timeout=30000)
    first = tab.outcome
    requests: list[BuildRequest] = []
    monkeypatch.setattr(window.workbench.builds, "request", requests.append)
    window.workbench.build(tab)
    qtbot.waitUntil(lambda: tab.outcome is not first, timeout=10000)
    assert requests == [] and tab.outcome.scene is first.scene
