"""Banners and the stale-scene badge (docs/14 §5.2, §6; docs/12 §2.3)."""

from __future__ import annotations

from pytestqt.qtbot import QtBot

from structura.ui.app_window import MainWindow
from structura.ui.banners import FALLBACK, LEGACY


def test_legacy_raytracer_scripts_offer_the_legacy_look_once(qtbot: QtBot, window: MainWindow) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("set raytracer::shadows false\nbox\n")
    qtbot.waitUntil(window.banner.isVisible, timeout=30000)
    assert window.banner.key == LEGACY and len(window.banner.buttons) == 2
    window.banner.buttons[0].click()  # Legacy Look
    assert window.render_view.integrator.currentText() == "classic" and not window.banner.isVisible()
    tab.editor.setPlainText("set raytracer::shadows true\nbox\n")
    qtbot.waitUntil(lambda: tab.outcome is not None and "true" in str(tab.outcome.scene.events), timeout=30000)
    assert not window.banner.isVisible()  # offered once per document


def test_fallback_banner_is_not_shown_on_headless_platforms(window: MainWindow) -> None:
    window.banners.preview_mode("cpu")
    assert not window.banner.isVisible() and FALLBACK not in window.banners.offered


def test_errors_mark_the_shown_scene_stale(qtbot: QtBot, window: MainWindow) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("box\n")
    qtbot.waitUntil(lambda: tab.outcome is not None, timeout=30000)
    tab.editor.setPlainText("box {\n")
    qtbot.waitUntil(lambda: window.viewport.overlay.stale, timeout=30000)
    tab.editor.setPlainText("sphere\n")
    qtbot.waitUntil(lambda: not window.viewport.overlay.stale, timeout=30000)
