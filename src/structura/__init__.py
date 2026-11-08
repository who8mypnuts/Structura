"""Structura — a modern studio for grammar-based 3D structures (successor of Structure Synth)."""

import os
import sys

__version__ = "0.1.0.dev0"

if getattr(sys, "frozen", False):  # an installed app bundle: its own files are read-only
    import platformdirs

    # Numba caches compiled kernels next to their sources by default; bundles keep them per user instead.
    os.environ.setdefault("NUMBA_CACHE_DIR", os.path.join(platformdirs.user_cache_dir("structura"), "numba"))


def __getattr__(name: str) -> object:
    """``import structura as st; st.build(…)``: the Python API (structura.api), imported on first use so that
    ``import structura`` itself stays light."""
    if name in ("Document", "build", "export", "open", "render"):
        import importlib  # noqa: PLC0415 - a dynamic import: modules that read __version__ do not depend on the API

        return getattr(importlib.import_module("structura.api"), name)
    raise AttributeError(f"module 'structura' has no attribute {name!r}")
