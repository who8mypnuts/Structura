"""The OpenGL probe decides the viewport backend before any GL widget exists (docs/08 §9)."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest
from PySide6.QtCore import qWarning
from PySide6.QtGui import QSurfaceFormat
from pytestqt.qtbot import QtBot

from structura.ui.app_window import MainWindow
from structura.ui.viewport import gl_probe, host
from structura.ui.viewport.gl_probe import Attempt, captured_qt_messages, parse_version


@pytest.mark.parametrize(
    ("text", "expected"),
    [("4.6.0 NVIDIA 550.54.14", (4, 6)), ("3.3 (Core Profile) Mesa 24.0", (3, 3)),
     ("OpenGL ES 3.2 Mesa 23.1", (3, 2)), ("", None)],
)  # fmt: skip
def test_parse_version(text: str, expected: tuple[int, int] | None) -> None:
    assert parse_version(text) == expected


def _fake_attempts(monkeypatch: pytest.MonkeyPatch, outcomes: dict[str, bool]) -> list[str]:
    tried: list[str] = []

    def fake(label: str, fmt: QSurfaceFormat) -> Attempt:
        tried.append(label)
        return Attempt(label, outcomes[label], "4.6 on test GPU" if outcomes[label] else "failed: 3009")

    monkeypatch.setattr(gl_probe, "try_format", fake)
    return tried


def test_probe_falls_back_to_compatibility_when_core_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    tried = _fake_attempts(monkeypatch, {"OpenGL 3.3 core": False, "OpenGL 3.3 compatibility": True})
    result = gl_probe.run_probe()
    assert result.ok and tried == ["OpenGL 3.3 core", "OpenGL 3.3 compatibility"]
    assert result.format is not None
    assert result.format.profile() == QSurfaceFormat.OpenGLContextProfile.CompatibilityProfile


def test_probe_without_a_usable_format_reports_every_attempt(monkeypatch: pytest.MonkeyPatch) -> None:
    labels = [label for label, _, _ in gl_probe.CANDIDATES]
    _fake_attempts(monkeypatch, dict.fromkeys(labels, False))
    result = gl_probe.run_probe()
    assert not result.ok and result.format is None
    assert all(label in result.summary() for label in labels)


def _fresh_process(*args: str) -> subprocess.CompletedProcess[str]:
    """Real contexts are probed in a new process, like a real launch: the test process has already used
    standalone EGL contexts (preview tests), and mixing those with Qt's GLX contexts on one X display is
    refused by the X server (BadAccess), which Xlib treats as fatal."""
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
    return subprocess.run([sys.executable, *args], capture_output=True, text=True, env=env, timeout=120, check=False)


PROBE_IMPOSSIBLE = """
from PySide6.QtGui import QGuiApplication, QSurfaceFormat
from structura.ui.viewport.gl_probe import MIN_VERSION, parse_version, requested_format, try_format
app = QGuiApplication([])
attempt = try_format("OpenGL 9.9", requested_format((9, 9), QSurfaceFormat.OpenGLContextProfile.CoreProfile))
assert attempt.detail, attempt
if attempt.ok:  # some platforms hand out their newest context: it must still be desktop GL >= 3.3
    assert (parse_version(attempt.detail) or (0, 0)) >= MIN_VERSION, attempt
print("probe-ok", attempt.ok)
"""


def test_an_impossible_format_is_rejected_not_fatal() -> None:
    result = _fresh_process("-c", PROBE_IMPOSSIBLE)
    assert result.returncode == 0 and "probe-ok" in result.stdout, result.stderr[-2000:]


def test_qt_messages_are_captured_during_the_probe_only(qtbot: QtBot) -> None:
    with captured_qt_messages() as messages:
        qWarning("QEGLPlatformContext: Failed to create context: 3009")
    assert messages == ["QEGLPlatformContext: Failed to create context: 3009"]


def test_a_failed_probe_selects_the_cpu_preview(monkeypatch: pytest.MonkeyPatch, qtbot: QtBot) -> None:
    monkeypatch.delenv("STRUCTURA_PREVIEW", raising=False)
    monkeypatch.setattr(host.QGuiApplication, "platformName", staticmethod(lambda: "wayland"))
    monkeypatch.setattr(host, "gpu_preview_usable", lambda: False)
    assert host.preferred_backend() == "cpu"
    monkeypatch.setattr(host, "gpu_preview_usable", lambda: True)
    assert host.preferred_backend() == "gpu"
    monkeypatch.setenv("STRUCTURA_PREVIEW", "gpu")  # explicit override: try the GL widget regardless
    monkeypatch.setattr(host, "gpu_preview_usable", lambda: False)
    assert host.preferred_backend() == "gpu"


def test_cpu_preview_window_is_a_raster_window(window: MainWindow) -> None:
    """Without the GL widget the window must not be composited through OpenGL: a failing GL context would
    otherwise keep it from ever being shown (Wayland)."""
    handle = window.windowHandle()
    assert handle is not None
    assert window.viewport.gl is None
    assert handle.surfaceType() == handle.SurfaceType.RasterSurface


def test_doctor_reports_the_probe() -> None:
    result = _fresh_process("-m", "structura.cli.main", "doctor", "--no-compute")
    assert result.returncode == 0, result.stderr[-2000:]
    assert "OpenGL preview" in result.stdout and "OpenGL 3.3 core" in result.stdout
    assert "Qt platform: offscreen" in result.stdout
    assert "PyMeshLab" in result.stdout and "Open Image Denoise" in result.stdout  # the libraries section


def test_every_requested_format_is_desktop_opengl() -> None:
    """The default renderable type lets Qt's EGL code pick an OpenGL ES config on NVIDIA (error 3009)."""
    for _, version, profile in gl_probe.CANDIDATES:
        assert gl_probe.requested_format(version, profile).renderableType() == QSurfaceFormat.RenderableType.OpenGL


def test_preview_labels_name_the_compute_device() -> None:
    assert host.preview_label("gpu") == "OpenGL" and host.preview_label("cpu") == "CPU"
    assert host.preview_label("cuda") == "CUDA"
