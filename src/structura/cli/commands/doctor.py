"""`structura doctor` — report the environment the GUI and the renderers will see: Qt platform, the OpenGL
probe (every format tried and why it failed), PyMeshLab and Open Image Denoise, and which compute backends are
available. Paste its output
into bug reports."""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
from importlib.metadata import version

HELP = "report the Qt platform, OpenGL support and compute devices (for bug reports)"
SESSION_VARS = ("XDG_SESSION_TYPE", "WAYLAND_DISPLAY", "DISPLAY", "QT_QPA_PLATFORM", "QT_XCB_GL_INTEGRATION",
                "STRUCTURA_PREVIEW")  # fmt: skip


def register(p: argparse.ArgumentParser) -> None:
    p.add_argument("--no-compute", action="store_true", help="skip probing the compute backends")
    p.add_argument("--opengl-only", action="store_true", help=argparse.SUPPRESS)  # the XWayland sub-probe


def _platform_fallbacks() -> str | None:
    """Qt's usual choice for this session, then 'offscreen' (Qt aborts if no platform plugin loads)."""
    if sys.platform in ("win32", "darwin") or "QT_QPA_PLATFORM" in os.environ:
        return None
    native = ["wayland"] if os.environ.get("WAYLAND_DISPLAY") else []
    native += ["xcb"] if os.environ.get("DISPLAY") else []
    return ";".join([*native, "offscreen"])


def _environment() -> list[str]:
    from PySide6 import __version__ as pyside  # noqa: PLC0415 - keeps `structura --help` fast
    from PySide6.QtCore import qVersion  # noqa: PLC0415

    from ... import __version__  # noqa: PLC0415

    lines = [f"structura {__version__}, Python {platform.python_version()}, PySide6 {pyside} (Qt {qVersion()})",
             f"system: {platform.platform()}"]  # fmt: skip
    lines += [f"  {name}={os.environ[name]}" for name in SESSION_VARS if name in os.environ]
    return lines


def _opengl() -> list[str]:
    from PySide6.QtGui import QGuiApplication  # noqa: PLC0415

    from ...ui.viewport.gl_probe import HEADLESS_PLATFORMS, run_probe  # noqa: PLC0415

    fallbacks = _platform_fallbacks()
    if fallbacks:
        os.environ["QT_QPA_PLATFORM"] = fallbacks
    app = QGuiApplication.instance() or QGuiApplication([sys.argv[0]])  # referenced until the probe is done
    platform_name = QGuiApplication.platformName()
    result = run_probe()
    del app
    from PySide6.QtGui import QOpenGLContext  # noqa: PLC0415

    lines = [f"Qt platform: {platform_name} (Qt OpenGL module: {QOpenGLContext.openGLModuleType().name})",
             "OpenGL preview (needs desktop OpenGL 3.3):"]  # fmt: skip
    lines += [f"  {'ok ' if a.ok else 'no '} {a.label}: {a.detail}" for a in result.attempts]
    if platform_name in HEADLESS_PLATFORMS:
        lines.append("  -> probed on Qt's headless platform (no window system reachable); run this command in your")
        lines.append("     desktop session to see what the GUI will use")
    else:
        lines.append(f"  -> {'GPU preview' if result.ok else 'no usable OpenGL context here'}")
    if not result.ok and platform_name == "wayland" and os.environ.get("DISPLAY"):
        lines += _xwayland()
    return lines


def _xwayland() -> list[str]:
    """The same probe on XWayland, in a child process (a process has one Qt platform)."""
    env = {**os.environ, "QT_QPA_PLATFORM": "xcb"}
    command = [sys.executable, "-m", "structura", "doctor", "--opengl-only"]
    try:
        out = subprocess.run(command, env=env, capture_output=True, text=True, timeout=60, check=False).stdout
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [f"XWayland: could not be probed ({exc})"]
    probed = [f"  {line}" for line in out.splitlines() if line.strip()]
    verdict = "the GUI restarts itself on XWayland (GPU preview)" if "-> GPU preview" in out else \
        "the viewport uses the compute preview"  # fmt: skip
    return ["", "XWayland (tried because native Wayland failed):", *probed, f"  => {verdict}"]


def compute_lines() -> list[str]:
    from ...compute.base import BackendUnavailableError  # noqa: PLC0415
    from ...compute.select import NAMES, select_backend  # noqa: PLC0415

    lines = ["Compute backends (precision renderer):"]
    for name in (n for n in NAMES if n != "auto"):
        try:
            backend = select_backend(name)
            lines.append(f"  ok  {name}: {backend.device_name}")
        except (BackendUnavailableError, ImportError, OSError, RuntimeError) as exc:
            lines.append(f"  no  {name}: {exc}")
    lines.append(f"  -> auto selects: {select_backend('auto').name}")
    return lines


def library_lines() -> list[str]:
    """Returns the Libraries section: whether PyMeshLab and Open Image Denoise load (and why not)."""
    from ...export.mesh.meshlab import MeshLabUnavailableError, _pymeshlab  # noqa: PLC0415
    from ...render.denoise.oidn import OidnUnavailableError, library  # noqa: PLC0415

    lines = ["Libraries:"]
    try:
        _pymeshlab()
        lines.append(f"  ok  PyMeshLab {version('pymeshlab')}")
    except MeshLabUnavailableError as exc:
        lines.append(f"  no  {exc}")
    try:
        lines.append(f"  ok  Open Image Denoise: {library().lib._name}")
    except OidnUnavailableError as exc:
        lines.append(f"  no  Open Image Denoise: {exc} (the À-Trous denoiser is used)")
    return lines


def run(args: argparse.Namespace) -> int:
    """Prints the doctor report.

    Args:
        args: The parsed command line (--no-compute, --opengl-only).

    Returns:
        0.
    """
    if args.opengl_only:
        print("\n".join(_opengl()))
        return 0
    sections = [_environment(), _opengl(), library_lines()] + ([] if args.no_compute else [compute_lines()])
    print("\n\n".join("\n".join(section) for section in sections))
    return 0
