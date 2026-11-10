"""Render progress before the first pass, in the status bar and the window title (PLAN Q8), and recovery of
internal errors (PLAN Q6)."""

from __future__ import annotations

from pytestqt.qtbot import QtBot

from structura.ui.app_window import MainWindow


def test_the_render_says_what_it_prepares_then_counts_up(qtbot: QtBot, window: MainWindow) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("8 * { x 1.2 } box\n")
    qtbot.waitUntil(lambda: tab.outcome is not None, timeout=30000)
    phases: list[str] = []
    titles: list[str] = []
    window.renders.phase.connect(lambda _doc, text: phases.append(text))
    window.render_view.activity.connect(lambda _text: titles.append(window.windowTitle()))
    window.render_view.samples.setValue(2)
    window.render_actions.start_render()
    assert window.render_view.controls.progress.maximum() == 0  # a moving bar until the first pass
    qtbot.waitUntil(lambda: window.render_view.last is not None and window.render_view.last.fraction >= 1.0,
                    timeout=120000)  # fmt: skip
    qtbot.waitUntil(lambda: window.windowTitle() == "Structura", timeout=30000)  # the denoiser ran, then idle
    assert any("Packing" in p for p in phases) and any("BVH" in p for p in phases)
    assert any(t.startswith("Structura — Rendering") for t in titles)
    assert window.render_view.controls.progress.maximum() == 100 and window.status.labels["render"].text() == ""


def test_an_internal_error_keeps_the_work_and_offers_a_report(qtbot: QtBot, window: MainWindow) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("// precious\nbox\n")
    window.errors.report("RuntimeError: boom", "Traceback (most recent call last): …")
    qtbot.waitUntil(lambda: window.banner.key == "internal-error", timeout=5000)
    assert window.session.recovery.exists() and "// precious" in window.session.recovery.path.read_text()
    assert "boom" in window.errors.report_text() and "Python" in window.errors.report_text()
