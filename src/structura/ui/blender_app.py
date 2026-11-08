"""'Open in Blender' (docs/15 §4.3, a convenience): find a Blender executable — the one set in Preferences ▸
Paths, else 'blender' on the PATH, else the usual install folders — and run an exported script in it."""

from __future__ import annotations

import glob
import os
import shutil
import sys
from pathlib import Path

KEY = "paths/blender"


def _installed() -> list[str]:
    if sys.platform == "win32":
        roots = [os.environ.get(v, "") for v in ("ProgramFiles", "ProgramFiles(x86)")]
        found = [p for r in roots if r for p in glob.glob(os.path.join(r, "Blender Foundation", "Blender*",
                                                                         "blender.exe"))]  # fmt: skip
        return sorted(found, reverse=True)  # the newest version first
    if sys.platform == "darwin":
        return ["/Applications/Blender.app/Contents/MacOS/Blender"]
    return ["/snap/bin/blender", "/usr/bin/blender", "/usr/local/bin/blender"]


def find_blender(configured: str = "") -> str | None:
    """The Blender executable to use, or None when there is none."""
    if configured:
        return configured if Path(configured).is_file() else None
    on_path = shutil.which("blender")
    if on_path:
        return on_path
    return next((p for p in _installed() if Path(p).is_file()), None)
