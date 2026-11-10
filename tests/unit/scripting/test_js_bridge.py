"""The '#javascript' Builder bridge (docs/16 §3), with a recording host instead of a renderer."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest

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
        return command == "allowed"

    def execute(self, command: str, arguments: str, wait: bool) -> None:
        self.log.append(f"exec {command} {arguments} {wait}")

    def cancelled(self) -> bool:
        return len(self.rendered) >= self.stop_after or time.perf_counter() > self.deadline

    def info(self, text: str) -> None:
        self.log.append(f"info {text}")

    def message(self, text: str) -> None:
        self.log.append(f"message {text}")

    def progress(self, caption: str | None, fraction: float | None) -> None:
        self.log.append(f"progress {caption} {fraction}")

    def sleep(self, ms: int) -> None:
        self.log.append(f"sleep {ms}")

    def wait_for_click(self) -> bool:
        return self.click

    def show_scene(self, scene: Any) -> None:
        self.shown.append(scene)

    stop_after = 10**9
    deadline = float("inf")
    click = True

    @property
    def log(self) -> list[str]:
        self.__dict__.setdefault("_log", [])
        return self.__dict__["_log"]

    @property
    def shown(self) -> list[Any]:
        self.__dict__.setdefault("_shown", [])
        return self.__dict__["_shown"]


@pytest.fixture(autouse=True)
def app(qapp: Any) -> Any:
    """pytest-qt's QApplication: a plain QCoreApplication here would break later tests that need a GUI one."""
    return qapp


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


def test_debug_world_and_vector3(tmp_path: Path) -> None:
    (tmp_path / "a.es").write_text("box\n")
    script = ("#javascript\nDebug.Info('hi'); Debug.ShowProgress('work'); Debug.SetProgress(0.5);\n"
              "Debug.HideProgress();\n"
              "Debug.Sleep(5); Debug.Message('note');\nBuilder.load('a.es'); Builder.build();\n"
              "World.setColor(new Vector3(1, 0, 0), 0.5); World.addSphere(new Vector3(1, 2, 3), 0.5);\n"
              "Builder.execute('allowed', '-x', true); Builder.execute('other', '', false);\n")  # fmt: skip
    host = Host()
    run_javascript(script, tmp_path, host)
    assert host.log == ["info hi", "progress work 0.0", "progress None 0.5", "progress None None", "sleep 5",
                        "message note", "exec allowed -x True"]  # fmt: skip
    assert host.shown[0] == 1  # Builder.build shows its scene
    world = host.shown[-1]
    assert len(world) == 1 and world.rgba[0].tolist() == [1.0, 0.0, 0.0, 0.5]
    assert world.xform[0, :, 3].tolist() == [0.5, 1.5, 2.5]  # the sphere's frame: centre − radius


def test_a_right_click_ends_the_script_quietly(tmp_path: Path) -> None:
    host = Host()
    host.click = False
    run_javascript("#javascript\nDebug.waitForMouseButton(); Builder.build();\n", tmp_path, host)
    assert host.built == []
