"""The EisenScript compatibility corpus: every unique .es file shipped with Structura."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIRS = (
    ROOT / "src/structura/resources/legacy/examples",
    ROOT / "src/structura/resources/examples/community",
)


@dataclass(frozen=True)
class CorpusScript:
    id: str  # stable id: short content hash + readable stem
    path: Path
    sha1: str
    is_javascript: bool

    @property
    def rel(self) -> str:
        return self.path.relative_to(ROOT).as_posix()


def _slug(stem: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in stem).strip("_").lower()[:40]


def collect() -> list[CorpusScript]:
    seen: dict[str, CorpusScript] = {}
    for base in CORPUS_DIRS:
        for path in sorted(base.rglob("*.es")):
            data = path.read_bytes()
            sha1 = hashlib.sha1(data).hexdigest()
            if sha1 in seen:
                continue
            text = data.decode("utf-8", errors="replace").lstrip()
            seen[sha1] = CorpusScript(
                f"{sha1[:8]}_{_slug(path.stem)}", path, sha1, text.lower().startswith("#javascript")
            )
    return sorted(seen.values(), key=lambda s: s.id)
