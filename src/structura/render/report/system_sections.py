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
from ..settings import RenderSettings
from .model import Row, Section, row

PACKAGES = ("numpy", "numba", "PySide6", "wgpu", "pyopencl", "cuda-python", "usd-core")


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


def reproduce_command(script: Path | None, settings: RenderSettings, seed: int, device: str) -> str:
    """A `structura render` command line that renders the same image (with the script's camera)."""
    name, backend = str(script) if script else "script.es", device.split(" ", maxsplit=1)[0] or "auto"
    args = ["structura", "render", name, "-o", "render.png", "--seed", str(seed), "--size",
            f"{settings.width}x{settings.height}", "--samples", str(settings.samples), "--integrator",
            settings.integrator, "--view", settings.view, "--device", backend]  # fmt: skip
    if settings.noise_threshold > 0:
        args += ["--noise-threshold", f"{settings.noise_threshold:g}"]
    if settings.time_limit > 0:
        args += ["--time-limit", f"{settings.time_limit:g}"]
    return shlex.join(args)


def reproduce_section(script: Path | None, settings: RenderSettings, seed: int, device: str) -> Section:
    command = reproduce_command(script, settings, seed, device)
    note = "the viewport camera is stored in the image metadata; the command uses the script's camera"
    return Section("reproduce", "Reproduce", (row("Command line", command, note=note),))
