"""Structura — a modern studio for grammar-based 3D structures (successor of Structure Synth)."""

import os
import sys

__version__ = "0.1.0.dev0"

if getattr(sys, "frozen", False):  # an installed app bundle: its own files are read-only
    import platformdirs

    # Numba caches compiled kernels next to their sources by default; bundles keep them per user instead.
    os.environ.setdefault("NUMBA_CACHE_DIR", os.path.join(platformdirs.user_cache_dir("structura"), "numba"))
