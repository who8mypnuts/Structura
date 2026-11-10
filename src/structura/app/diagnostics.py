"""Crash diagnostics for the GUI (PLAN Q6): a rotating log file, faulthandler for hard crashes (Numba, CUDA,
OpenGL drivers), and hooks that catch Python exceptions nobody handled — in Qt slots (sys.excepthook) and in
plain threads (threading.excepthook) — log them and hand them to the window (an error banner and an immediate
recovery snapshot) instead of letting the app limp on silently.

    <data folder>/logs/structura.log   everything logged, 5 × 1 MB
    <data folder>/logs/crash.log       tracebacks of every thread when the process dies hard
"""

from __future__ import annotations

import faulthandler
import logging
import sys
import threading
import traceback
from collections.abc import Callable
from logging.handlers import RotatingFileHandler
from pathlib import Path
from types import TracebackType
from typing import TextIO

log = logging.getLogger("structura.crash")
LOG_BYTES, LOG_FILES = 1_000_000, 5
ErrorHandler = Callable[[str, str], None]  # (summary, traceback)


class Diagnostics:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.log_file = directory / "structura.log"
        self.crash_file = directory / "crash.log"
        self.on_error: ErrorHandler | None = None  # set by the window once it exists
        self._crash_stream: TextIO | None = None
        self._handler: logging.Handler | None = None
        self._previous = (sys.excepthook, threading.excepthook)

    def install(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(self.log_file, maxBytes=LOG_BYTES, backupCount=LOG_FILES, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logging.getLogger().addHandler(handler)
        self._handler = handler
        self._crash_stream = self.crash_file.open("a", encoding="utf-8")  # stays open: faulthandler writes here
        faulthandler.enable(self._crash_stream, all_threads=True)
        sys.excepthook = self._excepthook
        threading.excepthook = self._thread_hook

    def close(self) -> None:
        """Undo install() (tests; the app keeps its diagnostics until it exits)."""
        sys.excepthook, threading.excepthook = self._previous
        if self._handler is not None:
            logging.getLogger().removeHandler(self._handler)
            self._handler.close()
        if self._crash_stream is not None:
            faulthandler.enable()  # back to standard error
            self._crash_stream.close()

    def _report(self, kind: type[BaseException], value: BaseException, tb: TracebackType | None) -> None:
        details = "".join(traceback.format_exception(kind, value, tb))
        log.error("Unhandled exception\n%s", details)
        if self.on_error is not None:
            self.on_error(f"{kind.__name__}: {value}", details)

    def _excepthook(self, kind: type[BaseException], value: BaseException, tb: TracebackType | None) -> None:
        if issubclass(kind, KeyboardInterrupt):
            self._previous[0](kind, value, tb)
            return
        self._report(kind, value, tb)

    def _thread_hook(self, args: threading.ExceptHookArgs) -> None:
        if args.exc_value is not None:
            self._report(args.exc_type, args.exc_value, args.exc_traceback)
