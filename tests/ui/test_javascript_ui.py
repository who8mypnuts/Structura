"""'#javascript' scripts in the window (docs/16 §3): recognised, highlighted, run as a background job."""

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
    with qtbot.waitSignal(window.scripts.service.finished, timeout=60000) as finished:
        window.registry.trigger("build.run_js")
    assert finished.args[1] == 2
    assert (tmp_path / "frame0.png").exists() and (tmp_path / "frame1.png").exists()
