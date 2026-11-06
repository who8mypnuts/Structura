"""XWayland fallback for the GPU preview (docs/08 §9).

On Wayland the GPU preview needs a desktop OpenGL context through EGL. A few driver stacks cannot give one to
Qt's Wayland client; the same GPU is then fully usable through XWayland (GLX). When the probe fails on the
Wayland platform and an X display is reachable, the app restarts itself once on the 'xcb' platform, before
any window exists. If OpenGL works there, the choice is remembered (per Qt version), so later starts go
straight to XWayland; `structura doctor` shows what the native session gives.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Protocol

log = logging.getLogger(__name__)
RETRY_ENV = "STRUCTURA_XWAYLAND_RETRY"
HINT_KEY = "viewport/xwayland_for_qt"


class Settings(Protocol):
    def value(self, key: str, default: object = None) -> object: ...

    def set_value(self, key: str, value: object) -> None: ...


def _qt_version() -> str:
    from PySide6.QtCore import qVersion  # noqa: PLC0415

    return str(qVersion())


def wayland_session() -> bool:
    return bool(os.environ.get("WAYLAND_DISPLAY")) and sys.platform.startswith("linux")


def apply_hint(settings: Settings) -> None:
    """Before the QApplication exists: use XWayland if an earlier start found that only it has OpenGL."""
    if "QT_QPA_PLATFORM" in os.environ or not wayland_session() or not os.environ.get("DISPLAY"):
        return
    if settings.value(HINT_KEY, "") == _qt_version():
        os.environ["QT_QPA_PLATFORM"] = "xcb"
        log.info("using XWayland (xcb): native Wayland gave no desktop OpenGL on an earlier start")


def restart_command() -> list[str]:
    """How to start this same program again (console script, `python -m structura`, or a frozen bundle)."""
    if getattr(sys, "frozen", False):
        return [sys.executable, *sys.argv[1:]]
    if sys.argv and sys.argv[0].endswith("__main__.py"):
        return [sys.executable, "-m", "structura", *sys.argv[1:]]
    return [sys.executable, *sys.argv]


def retry_on_xwayland(platform_name: str) -> None:
    """The probe failed: restart once on XWayland if that is possible (does not return in that case)."""
    if platform_name != "wayland" or not os.environ.get("DISPLAY") or os.environ.get(RETRY_ENV):
        return
    if os.environ.get("STRUCTURA_PREVIEW", "auto").lower() != "auto":
        return
    log.warning("no desktop OpenGL through native Wayland; restarting on XWayland for the GPU preview")
    os.environ.update({RETRY_ENV: "1", "QT_QPA_PLATFORM": "xcb"})
    command = restart_command()
    os.execv(command[0], command)


def remember(settings: Settings, gl_ok: bool) -> None:
    """After a restart on XWayland: keep the choice if OpenGL worked there."""
    if os.environ.pop(RETRY_ENV, None) and gl_ok:
        settings.set_value(HINT_KEY, _qt_version())
