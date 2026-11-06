"""The '#javascript' Builder bridge (docs/16 §3), with a recording host instead of a renderer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import QCoreApplication

from structura.scripting.js_bridge import js_string, run_javascript


class Host:
    def __init__(self) -> None:
        self.built: list[str] = []
        self.rendered: list[tuple[str, int, int]] = []

    def build(self, text: str, script_dir: Path) -> Any:
        self.built.append(text)
        return len(self.built)

    def raytrace(self, scene: Any, path: Path, width: int, height: int) -> None:
        self.rendered.append((path.name, width, height))

    def render_template(self, scene: Any, template: str, path: Path) -> None:
        self.rendered.append((path.name, 0, 0))

    def allow_execute(self, command: str, arguments: str) -> bool:
        return False

    def cancelled(self) -> bool:
        return len(self.rendered) >= self.stop_after

    stop_after = 10**9


@pytest.fixture(autouse=True)
def app() -> Any:
    return QCoreApplication.instance() or QCoreApplication([])


def test_load_define_build_and_render(tmp_path: Path) -> None:
    (tmp_path / "base.es").write_text("#define _rz 0\n{ rz _rz } box\n")
    script = '#javascript\nBuilder.load("base.es");\nfor (i = 0; i < 3; i++) {\n  Builder.reset();\n' \
             '  Builder.setSize(0, 100);\n  Builder.define("_rz", i * 45);\n  Builder.build();\n' \
             '  Builder.raytraceToFile("f" + i + ".png", true);\n}\n'  # fmt: skip
    host = Host()
    assert run_javascript(script, tmp_path, host) == 3
    assert host.built[2] == "#define _rz 0\n{ rz 90 } box\n"  # '#define' lines are left alone, like 1.5
    assert host.rendered == [("f0.png", 0, 100), ("f1.png", 0, 100), ("f2.png", 0, 100)]


def test_limit_stops_the_loop_and_errors_report_lines(tmp_path: Path) -> None:
    host = Host()
    loop = '#javascript\nwhile (true) { Builder.build(); Builder.raytraceToFile("x.png", true); }\n'
    assert run_javascript(loop, tmp_path, host, limit=2) == 2
    with pytest.raises(RuntimeError, match="line"):
        run_javascript("#javascript\nBuilder.load('missing.es');\n", tmp_path, host)
    assert js_string(36.0) == "36" and js_string(0.25) == "0.25"


def test_cancellation_ends_the_script_between_actions(tmp_path: Path) -> None:
    host = Host()
    host.stop_after = 2
    loop = "for (var i = 0; i < 100; i++) { Builder.build(); Builder.raytraceToFile('f' + i + '.png', true); }"
    script = f"#javascript\n{loop}\n"
    written = run_javascript(script, tmp_path, host)
    assert written == 2 and len(host.rendered) == 2  # stopped cleanly, not an error
