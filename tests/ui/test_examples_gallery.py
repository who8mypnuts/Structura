"""The Examples gallery (docs/14 §3): filtering, thumbnails, opening copies."""

from __future__ import annotations

from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot

from structura.ui.app_window import MainWindow
from structura.ui.panels import examples
from structura.ui.panels.examples import Thumbnails, example_files


def test_gallery_lists_filters_and_opens_copies(window: MainWindow) -> None:
    panel = window.examples
    assert panel.gallery.count() == len(example_files()) > 100
    panel.search.setText("menger")
    assert "Menger" in panel.visible_names() and all("menger" in n.lower() for n in panel.visible_names())
    panel.search.setText("")
    panel.group.setCurrentText("Community")
    assert 0 < len(panel.visible_names()) < panel.gallery.count()
    path = next(p for _, p in example_files() if p.name == "Menger.es")
    original = path.read_text(encoding="utf-8")
    panel.open_example.emit(path)
    tab = window.tabs.current()
    assert tab is not None and tab.path is None and tab.display_name == "Menger.es" and not tab.modified
    assert tab.text() == original


def test_thumbnails_are_rendered_once_then_read_from_the_cache(
    qtbot: QtBot, window: MainWindow, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(examples, "CACHE", tmp_path)
    monkeypatch.setenv("STRUCTURA_PREVIEW", "auto")
    monkeypatch.setenv("STRUCTURA_THUMBNAILS", "on")
    script = tmp_path / "tiny.es"
    script.write_text("{ color #f80 } box\n")
    shown: list[tuple[Path, object]] = []
    first = Thumbnails(window.runner, window)
    first.ready.connect(lambda p, image: shown.append((p, image)))
    first.start([script])
    qtbot.waitUntil(lambda: len(shown) == 1, timeout=60000)
    assert shown[0][1].width() == examples.TILE[0] and len(list(tmp_path.glob("*.png"))) == 1
    again = Thumbnails(window.runner, window)
    monkeypatch.setattr(examples, "_render", lambda path: pytest.fail("rendered again despite the cache"))
    again.ready.connect(lambda p, image: shown.append((p, image)))
    again.start([script])
    qtbot.waitUntil(lambda: len(shown) == 2, timeout=30000)
