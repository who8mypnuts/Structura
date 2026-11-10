"""Report sections about the machine and how to reproduce the image."""

from __future__ import annotations

import os
import platform
import shlex
from functools import cache
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import psutil

from ... import __version__
from ..output import Display
from ..post import LOOKS, PostSettings
from ..settings import RenderSettings
from .model import Row, Section, row

PACKAGES = ("numpy", "numba", "PySide6", "wgpu", "pyopencl", "cuda-python", "usd-core", "pymeshlab")


@cache
def cpu_name() -> str:
    """The CPU's marketing name where the OS tells it (platform.processor() is often empty on Linux)."""
    try:
        for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or platform.machine()


def peak_memory() -> int:
    """The process's peak resident memory in bytes (0 when the platform does not tell)."""
    info = psutil.Process().memory_info()
    peak = getattr(info, "peak_wset", 0)  # Windows
    if peak:
        return int(peak)
    try:
        import resource  # noqa: PLC0415 - POSIX only

        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(usage if platform.system() == "Darwin" else usage * 1024)  # macOS: bytes; Linux: KiB
    except (ImportError, OSError):
        return int(info.rss)


def _package(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "not installed"


def system_section(extra: dict[str, str]) -> Section:
    memory = psutil.virtual_memory().total
    rows: list[Row] = [
        row("Structura", __version__),
        row("Operating system", platform.platform()),
        row("Python", platform.python_version(), f"{platform.python_version()} ({platform.python_implementation()})"),
        row("CPU", cpu_name(), f"{cpu_name()} — {os.cpu_count()} logical cores"),
        row("Memory", memory, f"{memory / 2**30:.1f} GiB"),
        *(row(label, value) for label, value in extra.items()),
        *(row(name, _package(name)) for name in PACKAGES),
    ]  # fmt: skip
    return Section("system", "System", tuple(rows))


def _look_args(post: PostSettings, script: PostSettings) -> list[str]:
    """--look / --bloom / --vignette / --lut for a look that is not the script's own."""
    if post == script:
        return []
    name = next((key.lower() for key, look in LOOKS.items() if look == post), None)
    if name is not None:
        return ["--look", name]
    args = ["--look", "off"]
    for key in ("bloom", "vignette"):
        if getattr(post, key):
            args += [f"--{key}", f"{getattr(post, key):g}"]
    return args + (["--lut", post.lut] if post.lut else [])


def reproduce_command(
    script: Path | None, settings: RenderSettings, seed: int, device: str, camera_from: Path | None = None,
    display: Display | None = None,
) -> str:  # fmt: skip
    """A `structura render` command line that renders the same image: with the camera (and lens) stored in
    ``camera_from`` (the saved image), else the script's; shown with ``display`` (default: the script's)."""
    shown = display or settings.display
    name, backend = str(script) if script else "script.es", device.split(" ", maxsplit=1)[0] or "auto"
    args = ["structura", "render", name, "-o", "render.png", "--seed", str(seed), "--size",
            f"{settings.width}x{settings.height}", "--samples", str(settings.samples), "--integrator",
            settings.integrator, "--view", shown.view, "--device", backend]  # fmt: skip
    if camera_from is not None:
        args += ["--camera-from", str(camera_from)]
    if shown.exposure:
        args += ["--exposure", f"{shown.exposure:g}"]
    if settings.noise_threshold > 0:
        args += ["--noise-threshold", f"{settings.noise_threshold:g}"]
    if settings.time_limit > 0:
        args += ["--time-limit", f"{settings.time_limit:g}"]
    return shlex.join(args + _look_args(shown.post, settings.post))


def reproduce_section(
    script: Path | None, settings: RenderSettings, seed: int, device: str, camera_from: Path | None = None,
    display: Display | None = None,
) -> Section:  # fmt: skip
    command = reproduce_command(script, settings, seed, device, camera_from, display)
    saved = "the camera and lens come from the saved image's metadata"
    note = saved if camera_from is not None else "the script's camera (save the image to keep this one)"
    return Section("reproduce", "Reproduce", (row("Command line", command, note=note),))
