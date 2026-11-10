"""GUI bootstrap (docs/02 §3 'structura.app'): Qt application, fonts, OpenGL surface format, main window."""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from PySide6.QtGui import QSurfaceFormat
from PySide6.QtWidgets import QApplication

from ..services.settings import SettingsService
from ..ui.app_window import MainWindow
from ..ui.fonts import register_fonts
from ..ui.i18n import install as install_translators
from ..ui.viewport import xwayland
from ..ui.viewport.gl_probe import preferred_format, probe
from ..ui.viewport.host import apply_backend_preference, preferred_backend
from ..ui.warmup import WarmUp
from ..ui.watchdog import StallWatchdog
from .diagnostics import Diagnostics


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
    settings = SettingsService()
    diagnostics = Diagnostics(settings.directory() / "logs")
    diagnostics.install()
    xwayland.apply_hint(settings)
    apply_backend_preference(settings)
    app = create_app(args)
    gl_ok = preferred_backend() == "gpu"  # runs the OpenGL probe before any window exists
    if not gl_ok:
        xwayland.retry_on_xwayland(QApplication.platformName())  # restarts the process when it can
    xwayland.remember(settings, gl_ok)
    install_translators(str(settings.value("appearance/language", "system")))
    window = MainWindow(settings)
    window.errors.log_dir = diagnostics.directory
    diagnostics.on_error = window.errors.report
    window.start([Path(a) for a in args[1:] if not a.startswith("-")])
    window.show()
    WarmUp(window).start()
    watchdog = StallWatchdog(float(os.environ["STRUCTURA_WATCHDOG"])) if "STRUCTURA_WATCHDOG" in os.environ else None
    code = int(app.exec())
    for stall in watchdog.stop() if watchdog else ():  # STRUCTURA_WATCHDOG=50: report GUI stalls over 50 ms
        logging.getLogger("structura.watchdog").warning("GUI stall of %.0f ms\n%s", stall.milliseconds, stall.stack)
    return code


if __name__ == "__main__":
    sys.exit(main())
