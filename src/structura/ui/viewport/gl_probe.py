"""OpenGL capability probe (docs/08 §9): find a context format the GPU preview can use *before* any
QOpenGLWidget exists.

Why before: a window that contains a QOpenGLWidget is composited through an OpenGL context (Qt's RHI
backing store). If that context cannot be created, the window never produces a frame, and on Wayland it is
never shown at all. Falling back after the widget failed is therefore too late. The probe tries the
preferred format first, then progressively more permissive ones; the first that yields desktop OpenGL ≥ 3.3
becomes the application default. If none does, the viewport uses the CPU preview and no GL widget is made.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cache

from PySide6.QtCore import QtMsgType, qInstallMessageHandler
from PySide6.QtGui import QOffscreenSurface, QOpenGLContext, QSurfaceFormat

MIN_VERSION = (3, 3)  # GLSL 330 shaders (docs/08 §3)
HEADLESS_PLATFORMS = ("offscreen", "minimal")  # no window system: a child GL widget never initialises
GL_VERSION, GL_RENDERER = 0x1F02, 0x1F01
VERSION_RE = re.compile(r"(\d+)\.(\d+)")
Profile = QSurfaceFormat.OpenGLContextProfile


def requested_format(version: tuple[int, int] | None, profile: Profile) -> QSurfaceFormat:
    """Always *desktop* OpenGL: with the default renderable type, Qt's EGL code picks an OpenGL ES config on
    NVIDIA drivers (Wayland, EGLFS), and asking that ES config for a 3.3 core context fails with
    EGL_BAD_MATCH (Qt's 'Failed to create context: 3009'); the driver default then comes back as ES 3.2."""
    fmt = QSurfaceFormat()
    fmt.setRenderableType(QSurfaceFormat.RenderableType.OpenGL)
    if version is not None:
        fmt.setVersion(*version)
        fmt.setProfile(profile)
    fmt.setDepthBufferSize(24)
    return fmt


def preferred_format() -> QSurfaceFormat:
    """3.3 core: the format macOS requires, and the first one tried everywhere."""
    return requested_format(MIN_VERSION, Profile.CoreProfile)


CANDIDATES: tuple[tuple[str, tuple[int, int] | None, Profile], ...] = (
    ("OpenGL 3.3 core", MIN_VERSION, Profile.CoreProfile),
    ("OpenGL 3.3 compatibility", MIN_VERSION, Profile.CompatibilityProfile),
    ("driver default", None, Profile.NoProfile),
)


@dataclass(frozen=True)
class Attempt:
    label: str
    ok: bool
    detail: str  # the GL version and renderer, or why the attempt failed


@dataclass(frozen=True)
class GlProbe:
    format: QSurfaceFormat | None  # the format to use, or None when the GPU preview is unavailable
    attempts: tuple[Attempt, ...]

    @property
    def ok(self) -> bool:
        return self.format is not None

    def summary(self) -> str:
        return "; ".join(f"{a.label}: {a.detail}" for a in self.attempts)


@contextmanager
def captured_qt_messages() -> Iterator[list[str]]:
    """Collect Qt's warnings (e.g. 'QEGLPlatformContext: Failed to create context: 3009') instead of
    printing them; they become the failure detail of the attempt."""
    messages: list[str] = []

    def handler(_kind: QtMsgType, _context: object, message: str) -> None:
        messages.append(message)

    previous = qInstallMessageHandler(handler)
    try:
        yield messages
    finally:
        qInstallMessageHandler(previous)


def parse_version(text: str) -> tuple[int, int] | None:
    match = VERSION_RE.search(text)
    return (int(match.group(1)), int(match.group(2))) if match else None


def _query(context: QOpenGLContext, fmt: QSurfaceFormat) -> tuple[str, str] | str:
    """(GL_VERSION, GL_RENDERER) with the context current, or the reason it could not be made current."""
    surface = QOffscreenSurface()
    surface.setFormat(fmt)
    surface.create()
    try:
        if not context.makeCurrent(surface):
            return "the context could not be made current"
        functions = context.functions()
        version, renderer = functions.glGetString(GL_VERSION), functions.glGetString(GL_RENDERER)
        context.doneCurrent()
        return str(version or ""), str(renderer or "")
    finally:
        surface.destroy()


def try_format(label: str, fmt: QSurfaceFormat) -> Attempt:
    context = QOpenGLContext()
    context.setFormat(fmt)
    with captured_qt_messages() as messages:
        created = context.create()
        result = _query(context, context.format()) if created else None
    if not created or result is None:
        return Attempt(label, False, " | ".join(messages) or "context creation failed")
    if isinstance(result, str):
        return Attempt(label, False, result)
    version_text, renderer = result
    version = parse_version(version_text)
    if context.isOpenGLES() or "OpenGL ES" in version_text:
        return Attempt(label, False, f"OpenGL ES only ({version_text}); the preview needs desktop OpenGL 3.3")
    if version is None or version < MIN_VERSION:
        return Attempt(label, False, f"version {version_text or 'unknown'} is below 3.3 ({renderer})")
    return Attempt(label, True, f"{version_text} on {renderer}")


def run_probe() -> GlProbe:
    """Try each candidate in order (needs a QGuiApplication)."""
    attempts: list[Attempt] = []
    for label, version, profile in CANDIDATES:
        fmt = requested_format(version, profile)
        attempt = try_format(label, fmt)
        attempts.append(attempt)
        if attempt.ok:
            return GlProbe(fmt, tuple(attempts))
    return GlProbe(None, tuple(attempts))


@cache
def probe() -> GlProbe:
    """The probe result for this process (run once)."""
    return run_probe()
