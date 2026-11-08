"""'#javascript' scripts in the window (docs/16 §3): recognised, highlighted, run in a separate process."""

from __future__ import annotations

from pathlib import Path

from pytestqt.qtbot import QtBot

from structura.core.lang.analysis import analyze
from structura.ui.app_window import MainWindow

SCRIPT = """#javascript
Builder.load("tiny.es");
Builder.setSize(32, 24);
for (var i = 0; i < 2; i++) {
  Builder.reset();
  Builder.define("_rz", 20 * i);
  Builder.build();
  Builder.raytraceToFile("frame" + i + ".png", true);
}
"""


def test_javascript_is_not_linted_as_eisenscript() -> None:
    analysis = analyze(SCRIPT)
    assert [d.code for d in analysis.diagnostics] == ["I204"] and analysis.program is None


def test_run_javascript_writes_files_in_the_background(qtbot: QtBot, tmp_path: Path, window: MainWindow) -> None:
    (tmp_path / "tiny.es").write_text("set raytracer::samples 1\n{ rz _rz } box\n")
    (tmp_path / "movie.es").write_text(SCRIPT)
    tab = window.docs.open_file(tmp_path / "movie.es")
    assert tab is not None and tab.is_javascript and window.status.labels["dialect"].text() == "JavaScript"
    qtbot.waitUntil(lambda: tab.editor.highlighter.javascript, timeout=2000)
    assert window.registry.action("build.run_js").isEnabled()
    with qtbot.waitSignal(window.scripts.process.finished, timeout=120000) as finished:
        window.registry.trigger("build.run_js")
    assert finished.args == [0, ""]
    assert (tmp_path / "frame0.png").exists() and (tmp_path / "frame1.png").exists()
    assert any("raytraced frame1.png" in line for line, _ in window.console.records)
    assert window.viewport.scene is not None  # Builder.build showed its scene


def test_a_pure_javascript_loop_never_blocks_the_window_and_cancel_stops_it(qtbot: QtBot, window: MainWindow) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("#javascript\nDebug.Info('looping'); while (true) {}\n")
    window.scripts.run()
    qtbot.waitUntil(lambda: any("looping" in line for line, _ in window.console.records), timeout=60000)
    with qtbot.waitSignal(window.scripts.process.finished, timeout=10000) as finished:
        window.registry.trigger("build.cancel")
    assert finished.args[0] == -1  # killed


def test_debug_questions_are_answered_from_the_window(qtbot: QtBot, window: MainWindow) -> None:
    tab = window.docs.new_script()
    tab.editor.setPlainText("#javascript\nDebug.waitForMouseButton(); Debug.Message('clicked');\n")
    window.scripts.run()
    qtbot.waitUntil(lambda: window.scripts.ui.waiting, timeout=60000)
    window.scripts.ui.click(True)
    qtbot.waitUntil(lambda: any("clicked" in line for line, _ in window.console.records), timeout=10000)
