"""Structure Synth '#javascript' scripts (docs/16 §3): the BuilderHost that builds, raytraces and exports
templates for the JavaScript Builder, Debug and World objects. `structura run` uses it headless; the window
runs the same command in a separate process (services/script_process.py) because QJSEngine keeps Python's
GIL while JavaScript runs — in-process, a long JavaScript loop would freeze the GUI.

In that child process a Channel carries what the window must show or answer: JSON lines on stdout, answers on
stdin. Cancel ends the process.
"""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any, TextIO

from ..compute.base import Backend
from ..core.build.api import build_scene
from ..core.lang.api import compile_script
from ..core.scene.ir import SceneIR
from ..core.scene.ir_io import save_scene
from ..export.templates.engine import TemplateExport
from ..export.templates.template_file import all_templates, load_template
from ..render.api import render, script_settings
from ..render.output import save_image
from ..render.settings import AUTO_PASSES

Report = Callable[[str], None]
SLEEP_STEP = 0.05  # seconds: Debug.Sleep and Builder.execute(wait) check for Cancel this often
PREFIX = "@@structura "  # marks the channel's lines among anything else the script process prints


class Channel:
    """The child side of the script protocol: ``send`` a message, ``ask`` and read the yes/no answer."""

    def __init__(self, out: TextIO = sys.stdout, answers: TextIO = sys.stdin) -> None:
        self.out, self.answers = out, answers
        self.folder = Path(tempfile.mkdtemp(prefix="structura-js-"))
        self.scenes = 0

    def send(self, **message: Any) -> None:
        self.out.write(PREFIX + json.dumps(message) + "\n")
        self.out.flush()

    def ask(self, **question: Any) -> bool:
        self.send(ask=question)
        return self.answers.readline().strip() == "1"

    def scene_file(self, scene: SceneIR) -> Path:
        self.scenes += 1
        path = self.folder / f"scene{self.scenes % 2}.npz"  # two files: the window may still be reading one
        save_scene(scene, path, compressed=False)
        return path


class BuilderHost:
    """What the JavaScript objects call into (scripting.js_bridge.JsHost)."""

    def __init__(self, backend: Backend, samples: int | None = None, allow_execute: bool = False,
                 report: Report | None = None, cancelled: Callable[[], bool] | None = None,
                 channel: Channel | None = None) -> None:  # fmt: skip
        self.backend, self.samples, self.may_execute = backend, samples, allow_execute
        self.report = report or (lambda _message: None)
        self._cancelled = cancelled or (lambda: False)
        self.channel = channel  # None: headless — messages go to the report, waits return at once
        self.allowed: set[str] = set()

    def build(self, text: str, script_dir: Path) -> SceneIR:
        return build_scene(compile_script(text, 0, None, script_dir).program).scene

    def raytrace(self, scene: Any, path: Path, width: int, height: int) -> None:
        settings = replace(script_settings(scene), integrator="classic")
        if width or height:
            w, h = width or round(height * 4 / 3), height or round(width * 3 / 4)
            settings = replace(settings, width=w, height=h)
        if self.samples:
            settings = replace(settings, samples=self.samples)
        result = render(scene, replace(settings, samples_per_pass=AUTO_PASSES), self.backend)
        save_image(result.image, path, 0.0, "standard")
        self.info(f"raytraced {path.name}")

    def render_template(self, scene: Any, template: str, path: Path) -> None:
        name = Path(template).stem
        path.write_text(TemplateExport(load_template(all_templates()[name])).render(scene), encoding="utf-8")
        self.info(f"exported {path.name}")

    def allow_execute(self, command: str, arguments: str) -> bool:
        """Headless runs need --allow-execute; in the window the user confirms each command once."""
        line = f"{command} {arguments}".strip()
        if self.may_execute or line in self.allowed:
            return True
        if self.channel is not None and self.channel.ask(kind="confirm", command=line):
            self.allowed.add(line)
            return True
        self.info(f"Builder.execute({command}) was not run")
        return False

    def execute(self, command: str, arguments: str, wait: bool) -> None:
        process = subprocess.Popen([command, *shlex.split(arguments)])
        while wait and process.poll() is None:
            if self.cancelled():
                process.terminate()
                return
            time.sleep(SLEEP_STEP)

    def cancelled(self) -> bool:
        return self._cancelled()

    # -- Debug and World ---------------------------------------------------------------------------------------
    def info(self, text: str) -> None:
        if self.channel is None:
            self.report(text)
        else:
            self.channel.send(info=text)

    def message(self, text: str) -> None:
        if self.channel is None:
            self.report(text)
        else:
            self.channel.send(message=text)

    def progress(self, caption: str | None, fraction: float | None) -> None:
        if self.channel is not None:
            self.channel.send(progress=[caption, fraction])

    def sleep(self, ms: int) -> None:
        end = time.perf_counter() + ms / 1000
        while time.perf_counter() < end and not self.cancelled():
            time.sleep(min(SLEEP_STEP, max(0.0, end - time.perf_counter())))

    def wait_for_click(self) -> bool:
        return True if self.channel is None else self.channel.ask(kind="click")

    def show_scene(self, scene: Any) -> None:
        if self.channel is not None and isinstance(scene, SceneIR):
            self.channel.send(scene=str(self.channel.scene_file(scene)))
