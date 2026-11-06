"""GUI bootstrap (docs/02 §3 'structura.app'): Qt application, fonts, OpenGL surface format, main window."""

from __future__ import annotations

import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from PySide6.QtGui import QSurfaceFormat
from PySide6.QtWidgets import QApplication

from ..ui.app_window import MainWindow
from ..ui.fonts import register_fonts
from ..ui.viewport.gl_probe import preferred_format, probe
from ..ui.viewport.host import preferred_backend


def create_app(argv: Sequence[str]) -> QApplication:
    QSurfaceFormat.setDefaultFormat(preferred_format())  # before the QApplication: macOS needs core here
    app = QApplication.instance() or QApplication(list(argv))
    assert isinstance(app, QApplication)
    configure_opengl()
    app.setApplicationName("Structura")
    app.setOrganizationName("Structura")
    register_fonts()
    return app


def configure_opengl() -> None:
    """Make the probed format the default before any window exists (the GL widget and the window's
    compositing context must agree). Without a usable format the viewport uses the CPU preview instead."""
    if preferred_backend() == "gpu":
        QSurfaceFormat.setDefaultFormat(probe().format or preferred_format())


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv if argv is None else argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    app = create_app(args)
    window = MainWindow()
    files = [Path(a) for a in args[1:] if not a.startswith("-")]
    for path in files:
        window.docs.open_file(path)
    if not files:
        window.docs.new_script()
    window.show()
    return int(app.exec())


if __name__ == "__main__":
    sys.exit(main())
