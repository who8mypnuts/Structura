"""Session snapshots: JSON round trip, tolerant parsing and atomic storage (docs/12 §2.1)."""

from __future__ import annotations

from pathlib import Path

from structura.services.session import SessionState, SessionStore, TabState


def test_round_trip() -> None:
    state = SessionState(
        (TabState("/a.es", None, 5, 3, (1, 4)), TabState(None, "box\n", 2, 0, (), "cp1252", "\r\n")), 1
    )
    assert SessionState.from_json(state.to_json()) == state
    assert state.unsaved_count == 1


def test_unknown_keys_and_bad_tabs_are_tolerated() -> None:
    text = '{"format": "structura-session", "version": 9, "current": 7, "tabs": [{"path": "/x.es", "future": 1}, 3]}'
    state = SessionState.from_json(text)
    assert state.tabs == (TabState("/x.es"),) and state.current == 0


def test_store_saves_atomically_and_ignores_garbage(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "sub" / "session.json")
    assert store.load() is None
    store.save(SessionState((TabState(None, "box"),)))
    assert store.load() == SessionState((TabState(None, "box"),))
    assert not list((tmp_path / "sub").glob("*.tmp"))
    store.path.write_text("{ not json")
    assert store.load() is None
    store.clear()
    assert not store.exists()
