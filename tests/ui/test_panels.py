"""Console filtering and the grouped Outline (docs/14 §3)."""

from __future__ import annotations

import logging

from pytestqt.qtbot import QtBot

from structura.ui.app_window import MainWindow


def test_console_filters_by_severity_and_text(window: MainWindow) -> None:
    console = window.console
    console.clear()
    console.append_record("INFO build: done", logging.INFO)
    console.append_record("WARNING export: sheared", logging.WARNING)
    console.append_record("ERROR render: failed", logging.ERROR)
    assert console.text.toPlainText().count("\n") == 2
    console.level.setCurrentIndex(console.level.findData("warnings"))
    assert "done" not in console.text.toPlainText() and "sheared" in console.text.toPlainText()
    console.search.setText("render")
    assert console.text.toPlainText().endswith("ERROR render: failed")
    console.clear()
    assert not console.text.toPlainText() and not console.records


def test_outline_groups_ambiguous_rules_with_their_chances(qtbot: QtBot, window: MainWindow) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("R\nrule R w 1 { box }\nrule R w 3 { sphere }\nrule leaf { box }\n")
    tree = window.outline.tree
    qtbot.waitUntil(lambda: tree.topLevelItemCount() == 2, timeout=20000)
    group = tree.topLevelItem(0)
    assert group.text(0) == "r  ×2" and group.childCount() == 2 and group.child(1).text(1) == "3 · 75 %"
    window.outline.filter.setText("lea")
    assert group.isHidden() and not tree.topLevelItem(1).isHidden()


def test_build_stats_explain_the_stop_and_chart_generations(qtbot: QtBot, window: MainWindow) -> None:
    import numpy as np  # noqa: PLC0415

    from structura.ui.panels.build_stats import generation_histogram  # noqa: PLC0415

    tab = window.docs.new_script()
    tab.editor.setPlainText("set maxdepth 5\nR\nrule R { { x 1 } R box }\n")
    qtbot.waitUntil(lambda: tab.outcome is not None, timeout=20000)
    stats = window.stats
    assert "maxdepth" in stats.labels["Stopped because"].text()
    assert stats.chart.counts.sum() == len(tab.outcome.scene)
    assert generation_histogram(np.arange(1000) % 500, 100).shape == (100,)
