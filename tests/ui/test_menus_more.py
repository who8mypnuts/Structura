"""The remaining menu commands of docs/14 §4.1: Help (guide, quick start, what's new, system report) and
Render (legacy look, region, denoise)."""

from __future__ import annotations

import numpy as np
import pytest
from pytestqt.qtbot import QtBot

from structura.render.api import RenderProgress
from structura.services.render import RenderUpdate
from structura.ui.app_window import MainWindow
from structura.ui.dialogs import system_report
from structura.ui.dialogs.guide import HELP


def test_help_pages_open_and_link(window: MainWindow) -> None:
    assert (HELP / "README.md").exists() and (HELP / "changelog.md").exists() and (HELP / "language.md").exists()
    window.registry.trigger("help.quick_start")
    browser = window.help.guide_browser
    assert browser is not None and browser.isVisible()
    assert browser.browser.source().fileName() == "getting-started.md"
    assert "Getting started" in browser.browser.toPlainText()
    window.registry.trigger("help.whats_new")
    assert browser.browser.source().fileName() == "changelog.md"
    window.registry.trigger("help.examples")
    assert window.docks["Examples"].isVisible()


def test_the_system_report_runs_the_doctor_in_a_process(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    assert system_report.cli_command("doctor")[1][-1] == "doctor"
    monkeypatch.setattr(system_report, "cli_command", lambda *a: ("python3", ["-c", "print('structura doctor ok')"]))
    dialog = system_report.SystemReport()
    qtbot.addWidget(dialog)
    dialog.start()
    qtbot.waitUntil(lambda: "doctor ok" in dialog.text.toPlainText(), timeout=10000)


def test_render_legacy_region_and_denoise_commands(window: MainWindow, monkeypatch: pytest.MonkeyPatch) -> None:
    started: list[bool] = []
    monkeypatch.setattr(window.render_view, "start", lambda region=None: started.append(True))
    window.registry.trigger("render.legacy")
    assert window.render_view.controls.integrator.currentText() == "classic" and started
    window.render_actions.render_region()
    assert "Render first" in window.status.currentMessage()
    image = np.full((8, 8, 3), 0.3, np.float32)
    window.render_view.last = RenderUpdate(RenderProgress(image, 4, 1.0), "cpu", 4)
    window.render_actions.render_region()
    assert window.render_view.view.region_mode
    window.render_view.controls.denoise.setCurrentText("off")
    window.render_actions.denoise()
    assert window.render_view.controls.denoise.currentText() == "auto"
