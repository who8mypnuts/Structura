"""Backup copies on save (PLAN Q6): before a script is overwritten, the version on disk is copied to the
backups folder as '<stem>-<YYYYmmdd-HHMMSS><suffix>'. The newest KEEP copies of each file name are kept, so an
edit saved by mistake can be undone past the editor's undo history (File ▸ Recover ▸ Open Backups Folder)."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

KEEP = 20


def backups_of(folder: Path, original: Path) -> list[Path]:
    """The backups of ``original`` (by its file name), newest first."""
    pattern = f"{original.stem}-????????-??????{original.suffix}"
    return sorted(folder.glob(pattern), reverse=True) if folder.is_dir() else []


def back_up(path: Path, folder: Path, now: datetime | None = None) -> Path | None:
    """Copy the file at ``path`` (if there is one) into ``folder``; returns the copy."""
    if not path.is_file():
        return None
    folder.mkdir(parents=True, exist_ok=True)
    stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    target = folder / f"{path.stem}-{stamp}{path.suffix}"
    shutil.copy2(path, target)
    for old in backups_of(folder, path)[KEEP:]:
        old.unlink(missing_ok=True)
    return target
