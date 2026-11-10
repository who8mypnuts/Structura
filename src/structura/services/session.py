"""Session snapshots (docs/12 §2.1, docs/07 §8): the open tabs with their unsaved text, cursor, seed and
folds. One format serves two purposes:

- the **session**, saved on quit and restored on the next start ("hot exit": unsaved edits survive);
- the **recovery** snapshot, written a few seconds after every edit (and periodically) and deleted on a clean
  exit. Whether the previous run crashed is told by its *running lock* (CrashGuard): a lock left behind by a
  process that no longer exists. Then the recovery snapshot — every open tab, with the unsaved text, the
  parameters, render overrides, camera, saved views and timeline — is offered.

Pure data and JSON; files are written atomically (temporary file, then rename)."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import psutil

FORMAT = "structura-session"
VERSION = 2  # 2: parameters, render overrides, camera, saved views and timeline per tab


@dataclass(frozen=True)
class TabState:
    """One tab of a session or recovery snapshot.

    Attributes:
        path: The script file; None for an untitled script.
        text: Unsaved text; None reads the file at ``path``.
        cursor: The cursor position.
        seed: The build seed.
        folded: Folded block lines.
        encoding: The file's text encoding.
        newline: The file's line ending.
        project: The tab's .structura file, if any.
        params: Parameter values.
        render_overrides: Render Settings changes over the script's values.
        camera: The viewport camera (core.project.model.camera_to_dict).
        bookmarks: Saved views: name → camera dict.
        timeline: The animation (core.animation.timeline.to_dict).
    """

    path: str | None = None
    text: str | None = None
    cursor: int = 0
    seed: int = 0
    folded: tuple[int, ...] = ()
    encoding: str = "utf-8"
    newline: str = "\n"
    project: str | None = None
    params: dict[str, float] = field(default_factory=dict)
    render_overrides: dict[str, Any] = field(default_factory=dict)
    camera: dict[str, Any] | None = None
    bookmarks: dict[str, Any] = field(default_factory=dict)
    timeline: dict[str, Any] | None = None

    @property
    def unsaved(self) -> bool:
        """Whether the tab has text that is not on disk."""
        return self.text is not None


@dataclass(frozen=True)
class SessionState:
    """The open tabs of a window, as saved on quit (the session) or after edits (recovery).

    Attributes:
        tabs: The tabs, in order.
        current: The index of the current tab.
        extra: Window-level state (layout, panels …).
    """

    tabs: tuple[TabState, ...] = ()
    current: int = 0
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def unsaved_count(self) -> int:
        return sum(t.unsaved for t in self.tabs)

    @property
    def empty(self) -> bool:
        return not self.tabs

    def to_json(self) -> str:
        """Returns the snapshot as JSON (format FORMAT, version VERSION)."""
        tabs = [asdict(t) | {"folded": list(t.folded)} for t in self.tabs]
        return json.dumps({"format": FORMAT, "version": VERSION, "current": self.current, "tabs": tabs,
                           "extra": self.extra}, indent=1)  # fmt: skip

    @classmethod
    def from_json(cls, text: str) -> SessionState:
        """Reads a snapshot; unknown keys are ignored and malformed tabs skipped.

        Args:
            text: The JSON text.

        Returns:
            The snapshot.

        Raises:
            ValueError: The text is not a Structura session (or not JSON).
        """
        data = json.loads(text)
        if not isinstance(data, dict) or data.get("format") != FORMAT:
            raise ValueError("not a Structura session")
        tabs = [tab for raw in data.get("tabs", []) if (tab := _tab(raw)) is not None]
        current = int(data.get("current", 0))
        return cls(tuple(tabs), max(0, min(current, len(tabs) - 1)), dict(data.get("extra", {})))


def _tab(raw: object) -> TabState | None:
    """A tab from its JSON object; None for a malformed one (the other tabs are still restored)."""
    if not isinstance(raw, dict):
        return None
    values = {k: v for k, v in raw.items() if k in TabState.__dataclass_fields__}
    try:
        values["folded"] = tuple(int(n) for n in values.get("folded", ()))
        tab = TabState(**values)
    except (TypeError, ValueError):
        return None
    if not isinstance(tab.path, str | None) or not isinstance(tab.text, str | None):
        return None
    return tab


class SessionStore:
    """A session snapshot in one JSON file."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def save(self, state: SessionState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(state.to_json(), encoding="utf-8")
        os.replace(temporary, self.path)  # atomic: a crash never leaves half a snapshot

    def load(self) -> SessionState | None:
        try:
            return SessionState.from_json(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return None

    def clear(self) -> None:
        self.path.unlink(missing_ok=True)

    def exists(self) -> bool:
        return self.path.exists()


def _is_structura(pid: int) -> bool:
    """Whether a process runs Structura (a crashed run's PID may have been reused by another program)."""
    try:
        command = " ".join(psutil.Process(pid).cmdline()).lower()
    except (psutil.Error, OSError):
        return False
    return "structura" in command


class CrashGuard:
    """A lock file for the running instance (pid inside). A lock whose process is gone means that run did not
    shut down cleanly. A second instance keeps its own lock and recovery file, so instances never mix."""

    def __init__(self, directory: Path) -> None:
        """Prepares the lock and recovery files of this run (nothing is written yet).

        Args:
            directory: Where the lock and the recovery snapshot live (the settings folder).
        """
        self.directory = directory
        self.lock = directory / "running.lock"
        self.recovery = directory / "recovery.json"

    @staticmethod
    def _owner(lock: Path) -> int | None:
        try:
            return int(lock.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return None

    def start(self) -> bool:
        """Takes the lock.

        A second instance gets its own lock and recovery file, so instances never mix.

        Returns:
            True when the previous run crashed: its lock was left behind and its process is gone.
        """
        self.directory.mkdir(parents=True, exist_ok=True)
        crashed = False
        if self.lock.exists():
            owner = self._owner(self.lock)
            if owner is not None and owner != os.getpid() and _is_structura(owner):
                self.lock = self.directory / f"running-{os.getpid()}.lock"  # another instance is running
                self.recovery = self.directory / f"recovery-{os.getpid()}.json"
            else:
                crashed = True
        self.lock.write_text(str(os.getpid()), encoding="utf-8")
        return crashed

    def stop(self) -> None:
        """A clean exit: drop the lock and the recovery snapshot."""
        self.lock.unlink(missing_ok=True)
        self.recovery.unlink(missing_ok=True)
