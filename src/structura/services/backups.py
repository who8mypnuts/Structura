"""Backup copies on save (PLAN Q6): before a script is overwritten, the version on disk is copied to the
backups folder as '<stem>-<YYYYmmdd-HHMMSS><suffix>'. The newest KEEP copies of each file name are kept, so an
edit saved by mistake can be undone past the editor's undo history (File ▸ Recover ▸ Open Backups Folder)."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

KEEP = 20


def backups_of(folder: Path, original: Path) -> list[Path]:
    """Returns the backups of a file, newest first.

    Args:
        folder: The backups folder.
        original: The file (its backups are found by its name).
    """
    pattern = f"{original.stem}-????????-??????{original.suffix}"
    return sorted(folder.glob(pattern), reverse=True) if folder.is_dir() else []


def back_up(path: Path, folder: Path, now: datetime | None = None) -> Path | None:
    """Copies a file into the backups folder before it is overwritten; old copies beyond KEEP are deleted.

    Args:
        path: The file (nothing happens when it does not exist).
        folder: The backups folder.
        now: The time stamp to use (tests); default now.

    Returns:
        The copy (the existing one when the file was already backed up within the same second), or None when
        there was no file.
    """
    if not path.is_file():
        return None
    folder.mkdir(parents=True, exist_ok=True)
    stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    target = folder / f"{path.stem}-{stamp}{path.suffix}"
    if target.exists():  # saved twice within a second: that second's backup already holds the older text
        return target
    shutil.copy2(path, target)
    for old in backups_of(folder, path)[KEEP:]:
        old.unlink(missing_ok=True)
    return target
