"""Guard: no source or test file may be git-ignored (a bare `build/` pattern once hid `core/build`)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_no_source_file_is_git_ignored() -> None:
    git = shutil.which("git")
    inside = git and subprocess.run([git, "rev-parse", "--is-inside-work-tree"], cwd=ROOT, capture_output=True,
                                    check=False).returncode == 0  # fmt: skip
    if not git or not inside:
        pytest.skip("not a git checkout")
    files = [str(p.relative_to(ROOT)) for d in ("src", "tests") for p in (ROOT / d).rglob("*")
             if p.is_file() and "__pycache__" not in p.parts]  # fmt: skip
    result = subprocess.run([git, "check-ignore", "--no-index", "--stdin"], cwd=ROOT, input="\n".join(files),
                            capture_output=True, text=True, check=False)  # fmt: skip
    assert result.stdout.split() == [], f"git-ignored source files: {result.stdout.split()[:10]}"
