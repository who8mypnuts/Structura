"""Session snapshots (docs/12 §2.1, docs/07 §8): the open tabs with their unsaved text, cursor, seed and
folds. One format serves two purposes:

- the **session**, saved on quit and restored on the next start ("hot exit": unsaved edits survive);
- the **recovery** snapshot, written periodically while editing and deleted on a clean exit. A snapshot
  that is still there at start-up means the previous run crashed, so recovery is offered.

Pure data and JSON; files are written atomically (temporary file, then rename)."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

FORMAT = "structura-session"
VERSION = 1


@dataclass(frozen=True)
class TabState:
    path: str | None = None  # None: an untitled script
    text: str | None = None  # unsaved text; None = read the file at ``path``
    cursor: int = 0
    seed: int = 0
    folded: tuple[int, ...] = ()
    encoding: str = "utf-8"
    newline: str = "\n"
    project: str | None = None  # the tab's .structura file

    @property
    def unsaved(self) -> bool:
        return self.text is not None


@dataclass(frozen=True)
class SessionState:
    tabs: tuple[TabState, ...] = ()
    current: int = 0
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def unsaved_count(self) -> int:
        return sum(t.unsaved for t in self.tabs)

    def to_json(self) -> str:
        tabs = [asdict(t) | {"folded": list(t.folded)} for t in self.tabs]
        return json.dumps({"format": FORMAT, "version": VERSION, "current": self.current, "tabs": tabs,
                           "extra": self.extra}, indent=1)  # fmt: skip

    @classmethod
    def from_json(cls, text: str) -> SessionState:
        """Tolerant: unknown keys are ignored and malformed tabs skipped."""
        data = json.loads(text)
        if not isinstance(data, dict) or data.get("format") != FORMAT:
            raise ValueError("not a Structura session")
        names = set(TabState.__dataclass_fields__)
        tabs = []
        for raw in data.get("tabs", []):
            if isinstance(raw, dict):
                values = {k: v for k, v in raw.items() if k in names}
                values["folded"] = tuple(int(n) for n in values.get("folded", ()))
                tabs.append(TabState(**values))
        current = int(data.get("current", 0))
        return cls(tuple(tabs), max(0, min(current, len(tabs) - 1)), dict(data.get("extra", {})))


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
