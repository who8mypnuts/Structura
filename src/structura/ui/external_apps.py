"""Other applications Structura hands files to (docs/15 §4.3, PLAN Q4): Blender runs an exported script, MeshLab
opens an exported mesh or project. One finder for all of them: the executable set in Preferences ▸ Paths, else
the program on the PATH, else the usual install folders."""

from __future__ import annotations

import glob
import os
import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExternalApp:
    name: str
    key: str  # the settings key of its path (Preferences ▸ Paths)
    command: str  # the program name on the PATH
    installed: Callable[[], list[str]]  # usual install locations, the most likely first
    arguments: Callable[[Path], list[str]]  # how it opens a file
    opens: tuple[str, ...]  # the file suffixes it is offered for


def _program_files(*pattern: str) -> list[str]:
    roots = [os.environ.get(v, "") for v in ("ProgramFiles", "ProgramFiles(x86)")]
    return sorted((p for r in roots if r for p in glob.glob(os.path.join(r, *pattern))), reverse=True)  # newest first


def _blender_installed() -> list[str]:
    if sys.platform == "win32":
        return _program_files("Blender Foundation", "Blender*", "blender.exe")
    if sys.platform == "darwin":
        return ["/Applications/Blender.app/Contents/MacOS/Blender"]
    return ["/snap/bin/blender", "/usr/bin/blender", "/usr/local/bin/blender"]


def _meshlab_installed() -> list[str]:
    if sys.platform == "win32":
        return _program_files("VCG", "MeshLab*", "meshlab.exe")
    if sys.platform == "darwin":
        return sorted(glob.glob("/Applications/MeshLab*.app/Contents/MacOS/MeshLab"), reverse=True)
    return ["/snap/bin/meshlab", "/usr/bin/meshlab", "/usr/local/bin/meshlab",
            *glob.glob(os.path.expanduser("~/Applications/MeshLab*.AppImage"))]  # fmt: skip


BLENDER = ExternalApp("Blender", "paths/blender", "blender", _blender_installed, lambda f: ["--python", str(f)],
                      (".py",))  # fmt: skip
MESHLAB = ExternalApp("MeshLab", "paths/meshlab", "meshlab", _meshlab_installed, lambda f: [str(f)],
                      (".ply", ".stl", ".obj", ".3mf", ".x3d", ".wrl", ".glb", ".gltf", ".mlp"))  # fmt: skip


def find_app(app: ExternalApp, configured: str = "") -> str | None:
    """The executable of ``app`` to use, or None when there is none."""
    if configured:
        return configured if Path(configured).is_file() else None
    on_path = shutil.which(app.command)
    if on_path:
        return on_path
    return next((p for p in app.installed() if Path(p).is_file()), None)


def find_blender(configured: str = "") -> str | None:
    return find_app(BLENDER, configured)
