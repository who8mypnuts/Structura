"""The viewport menu, the orbit lock, looks against X-ray, and the forced viewport engine."""

from __future__ import annotations

import os

import pytest
from PySide6.QtCore import QPoint
from pytestqt.qtbot import QtBot

from structura.ui.app_window import MainWindow
from structura.ui.viewport.host import apply_backend_preference
from structura.ui.viewport_menu import SECTIONS


def test_the_viewport_menu_offers_the_view_commands(window: MainWindow) -> None:
    menu = window.viewport_menu.build()
    titles = [a.text() for a in menu.actions() if a.text()]
    assert "Frame All" in titles and "Look" in titles and "Orbit Lock" in titles and "Controls" in titles
    assert sum(1 for _, ids in SECTIONS for _ in ids) == sum(
        len(m.actions()) if m else 1 for m in (a.menu() for a in menu.actions() if a.text())
    )
    window.viewport.compute.menu_requested.emit(QPoint(10, 10))  # a right-click: pops up without errors


def test_orbit_lock_and_controls_are_preferences(window: MainWindow) -> None:
    window.registry.trigger("view.orbit_lock_horizontal")
    assert window.viewport.orbit_lock == "horizontal"
    assert window.settings.value("viewport/orbit_lock", "free") == "horizontal"
    assert window.registry.action("view.orbit_lock_horizontal").isChecked()
    window.registry.trigger("view.controls_legacy")
    assert window.viewport.compute.navigator.preset == "legacy" and window.viewport.compute.orbit.trackball
    window.registry.trigger("view.controls_structura")
    window.registry.trigger("view.orbit_lock_free")


def test_choosing_a_look_ends_xray(qtbot: QtBot, window: MainWindow) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("box\n")
    qtbot.waitUntil(lambda: tab.outcome is not None, timeout=30000)
    window.registry.trigger("view.xray")
    assert window.workbench.view.xray and not window.registry.action("view.look_studio").isChecked()
    window.registry.trigger("view.look_clay")
    assert not window.workbench.view.xray and window.viewport.options.look == "clay"
    assert window.registry.action("view.look_clay").isChecked()


def test_the_viewport_engine_preference_sets_the_environment(
    window: MainWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("STRUCTURA_PREVIEW", raising=False)
    window.settings.set_value("viewport/backend", "gpu")
    apply_backend_preference(window.settings)
    assert os.environ["STRUCTURA_PREVIEW"] == "gpu"
    monkeypatch.setenv("STRUCTURA_PREVIEW", "cpu")
    apply_backend_preference(window.settings)
    assert os.environ["STRUCTURA_PREVIEW"] == "cpu"  # the environment wins


def test_v2_blocks_ask_before_converting_and_need_a_build(window: MainWindow, monkeypatch: pytest.MonkeyPatch) -> None:
    from PySide6.QtWidgets import QMessageBox  # noqa: PLC0415

    tab = window.docs.new_script()
    tab.editor.setPlainText("box\n")
    window.exports.start("obj")  # nothing built yet: the status bar says so, nothing is asked
    assert "Build the script first (F5), then export." in window.status.currentMessage()
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No)
    assert not window.editor_actions.ensure_v2("Add Light", "Lights are")  # declined: the script stays v1
    assert tab.text() == "box\n"
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    assert window.editor_actions.ensure_v2("Add Light", "Lights are") and tab.text().startswith("#version 2")
