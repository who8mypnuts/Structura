"""Quick Open (Ctrl+P) and Open Recent (docs/14 §4)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QMenu

from structura.core.lang.analysis import analyze
from structura.ui.app_window import MainWindow


def test_recent_files_feed_the_menu_and_quick_open(tmp_path: Path, window: MainWindow) -> None:
    for name in ("a.es", "b.es"):
        (tmp_path / name).write_text("box\n")
        window.docs.open_file(tmp_path / name)
    assert [p.name for p in window.docs.recent.paths()] == ["b.es", "a.es"]
    menu = QMenu()
    window.docs.fill_recent_menu(menu)
    assert [a.text().split()[0] for a in menu.actions()[:2]] == ["b.es", "a.es"]
    labels = [label for label, _, _ in window.quick_open.entries("")]
    assert "a.es" in labels and any(label.endswith(".es") for label in labels[2:])  # examples follow the tabs


def test_at_lists_rules_and_colon_goes_to_a_line(window: MainWindow) -> None:
    tab = window.docs.new_script()
    text = "set maxdepth 4\nspiral\nrule spiral { { x 1 } spiral box }\nrule leaf { sphere }\n"
    tab.editor.setPlainText(text)
    tab.editor.set_analysis(analyze(text))
    tab.analysis = analyze(text)
    rules = window.quick_open.entries("@lea")
    assert rules[0][0] == "rule leaf"
    window.quick_open.activate(rules[0][2])
    assert tab.editor.textCursor().blockNumber() == 3
    window.quick_open.activate(window.quick_open.entries(":2")[0][2])
    assert tab.editor.textCursor().blockNumber() == 1


def test_choosing_a_file_opens_it(tmp_path: Path, window: MainWindow) -> None:
    (tmp_path / "c.es").write_text("sphere\n")
    window.docs.recent.add(tmp_path / "c.es")
    entry = next(e for e in window.quick_open.entries("c.es") if e[0] == "c.es")
    window.quick_open.activate(entry[2])
    current = window.tabs.current()
    assert current is not None and current.path is not None and current.path.name == "c.es"


def test_find_in_files_searches_open_tabs_and_the_folder(tmp_path: Path, window: MainWindow) -> None:
    (tmp_path / "main.es").write_text("spiral\nrule spiral { box }\n")
    (tmp_path / "other.es").write_text("rule helper { sphere }\nspiral\n")
    tab = window.docs.open_file(tmp_path / "main.es")
    assert tab is not None
    tab.editor.setPlainText("spiral\nrule spiral { box }\n// unsaved: spiral\n")
    window.search.show()
    window.search.panel.query.setText("spiral")
    matches = window.search.panel.search_in(*window.search.sources())
    assert sorted({m.source.split("/")[-1] for m in matches}) == ["other.es", f"tab:{tab.doc_id}"]
    assert len([m for m in matches if m.source.startswith("tab:")]) == 3  # the unsaved text is searched
    other = next(m for m in matches if m.source.endswith("other.es"))
    window.search.open_match(other.source, other.offset)
    current = window.tabs.current()
    assert current is not None and current.path is not None and current.path.name == "other.es"
    assert current.editor.textCursor().blockNumber() == 1
