"""Structure Synth's '#javascript' scripts (docs/16 §3), run with QJSEngine.

The script sees a global ``Builder`` with 1.5's API: load, define, prepend, append, reset, build, setSize,
renderToFile, raytraceToFile, templateRenderToFile and execute. Building, rendering and template export
are provided by a ``JsHost`` from the layer above (dependency inversion), so this module stays a leaf.
``execute`` runs nothing unless the host allows it: templates and scripts can name arbitrary programs.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Protocol

from PySide6.QtCore import QObject, Slot
from PySide6.QtQml import QJSEngine

log = logging.getLogger(__name__)


class JsHost(Protocol):
    def build(self, text: str, script_dir: Path) -> Any: ...

    def raytrace(self, scene: Any, path: Path, width: int, height: int) -> None: ...

    def render_template(self, scene: Any, template: str, path: Path) -> None: ...

    def allow_execute(self, command: str, arguments: str) -> bool: ...


STOP = "structura: output limit reached"


def js_string(value: Any) -> str:
    """JavaScript's Number/String → string conversion, as QtScript passed values to define()."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


class BuilderApi(QObject):
    def __init__(self, engine: QJSEngine, host: JsHost, script_dir: Path, limit: int | None = None) -> None:
        super().__init__()
        self.engine, self.host, self.dir, self.limit = engine, host, script_dir, limit
        self.original = self.loaded = ""
        self.scene: Any = None
        self.width, self.height = 0, 0
        self.outputs = 0
        self.stopped = False

    def _guard(self, action: Any) -> None:
        """Run host work; Python errors become JavaScript exceptions that end the script."""
        try:
            action()
        except Exception as exc:
            self.engine.throwError(f"{type(exc).__name__}: {exc}")

    def _path(self, name: str) -> Path:
        return (self.dir / name).resolve()

    @Slot(str)
    def load(self, name: str) -> None:
        def read() -> None:
            self.loaded = self.original = self._path(name).read_text(encoding="utf-8")

        self._guard(read)

    @Slot(str, "QVariant")
    def define(self, name: str, value: Any) -> None:
        text = js_string(value)
        lines = [line if "#define" in line.lower() else line.replace(name, text) for line in self.loaded.split("\n")]
        self.loaded = "\n".join(lines)

    @Slot(str)
    def prepend(self, text: str) -> None:
        self.loaded = text + self.loaded

    @Slot(str)
    def append(self, text: str) -> None:
        self.loaded += text

    @Slot()
    def reset(self) -> None:
        self.loaded = self.original

    @Slot(int, int)
    def setSize(self, width: int, height: int) -> None:  # noqa: N802 - the 1.5 API name
        self.width, self.height = width, height

    @Slot()
    def build(self) -> None:
        def run() -> None:
            self.scene = self.host.build(self.loaded, self.dir)

        self._guard(run)

    @Slot(str, bool)
    def raytraceToFile(self, name: str, overwrite: bool) -> None:  # noqa: N802
        self._output(name, overwrite, lambda path: self.host.raytrace(self.scene, path, self.width, self.height))

    @Slot(str, bool)
    def renderToFile(self, name: str, overwrite: bool) -> None:  # noqa: N802 - 1.5 saved the GL view
        self.raytraceToFile(name, overwrite)

    @Slot(str, str, bool)
    def templateRenderToFile(self, template: str, name: str, overwrite: bool) -> None:  # noqa: N802
        self._output(name, overwrite, lambda path: self.host.render_template(self.scene, template, path))

    @Slot(str, str, bool)
    def execute(self, command: str, arguments: str, wait: bool) -> None:
        if not self.host.allow_execute(command, arguments):
            log.warning("Builder.execute(%s) was not run: external commands are disabled", command)

    def _output(self, name: str, overwrite: bool, write: Any) -> None:
        if self.limit is not None and self.outputs >= self.limit:
            self.stopped = True
            self.engine.throwError(STOP)
            return
        path = self._path(name)
        if path.exists() and not overwrite:
            log.warning("%s exists; not overwritten", path)
            return
        if self.scene is None:
            self.build()
        self._guard(lambda: write(path))
        self.outputs += 1


def javascript_body(text: str) -> str | None:
    """The JavaScript of a '#javascript' script (None for EisenScript)."""
    first, _, rest = text.partition("\n")
    return rest if first.strip().lower() == "#javascript" else None


def run_javascript(text: str, script_dir: Path, host: JsHost, limit: int | None = None) -> int:
    """Run the script; returns the number of files written. Raises RuntimeError on script errors."""
    body = javascript_body(text)
    if body is None:
        raise ValueError("not a '#javascript' script")
    engine = QJSEngine()
    api = BuilderApi(engine, host, script_dir, limit)
    QJSEngine.setObjectOwnership(api, QJSEngine.ObjectOwnership.CppOwnership)  # Python owns the API object
    engine.globalObject().setProperty("Builder", engine.newQObject(api))
    evaluated = engine.evaluate(body)
    result = evaluated[0] if isinstance(evaluated, tuple) else evaluated  # the stubs list an overload pair
    outputs, stopped = api.outputs, api.stopped
    error = None if stopped or not result.isError() else result.toString()
    line = result.property("lineNumber").toInt() if error else 0
    engine.collectGarbage()
    del engine  # before the API object it references
    if error is not None:
        raise RuntimeError(f"JavaScript error at line {line}: {error}")
    return outputs
