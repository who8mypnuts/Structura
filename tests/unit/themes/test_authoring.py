"""Theme authoring (docs/13 §8): drafts, TOML round trips, contrast fixes, user themes."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from structura.themes import authoring, loader
from structura.themes.authoring import ThemeDraft
from structura.themes.derive import role_groups, role_names
from structura.themes.writer import to_toml


@pytest.fixture
def user_themes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(loader, "user_dir", lambda: tmp_path)
    monkeypatch.setattr(authoring, "user_dir", lambda: tmp_path)
    return tmp_path


@pytest.mark.parametrize("theme_id", ["nord", "dracula", "solarized-light"])
def test_builtin_documents_round_trip_through_the_writer(theme_id: str) -> None:
    draft = ThemeDraft.from_id(theme_id)
    assert tomllib.loads(to_toml(draft.data)) == draft.data


def test_start_from_accent_gives_a_complete_theme_that_passes_contrast() -> None:
    theme = ThemeDraft.from_accent("Teal Night", "#2BB5A0", dark=True).theme()
    assert set(theme.colors) == set(role_names()) and theme.meta.id == "teal-night" and theme.meta.dark
    assert ThemeDraft.from_accent("Paper", "#C2410C", dark=False).theme().meta.kind == "light"


def test_overrides_resets_and_contrast_fixes() -> None:
    draft = ThemeDraft.from_accent("Test", "#2BB5A0", dark=True)
    assert draft.override("syntax.comment") is None
    draft.set_role("syntax.comment", "#20232A")  # nearly the background colour
    assert draft.contrast_fixes() and "syntax.comment" in draft.contrast_fixes()
    assert draft.fix_contrast() == 1 and draft.contrast_fixes() == {}
    draft.set_flag("syntax.keyword", "bold", True)
    assert draft.theme().style("syntax.keyword").bold
    draft.reset_role("syntax.comment")
    assert draft.override("syntax.comment") is None


def test_builtins_are_read_only_and_duplicates_get_a_free_id(user_themes: Path) -> None:
    nord = ThemeDraft.from_id("nord")
    assert nord.read_only
    with pytest.raises(PermissionError):
        nord.save()
    copy = nord.duplicate("Nord")  # 'nord' is taken
    assert copy.id == "nord-2" and not copy.read_only
    path = copy.save()
    assert path.parent == user_themes and "nord-2" in loader.theme_ids()
    assert loader.load_theme("nord-2").meta.name == "Nord"
    assert authoring.delete_user_theme("nord-2") and "nord-2" not in loader.theme_ids()


def test_role_groups_cover_every_role() -> None:
    grouped = [role for roles in role_groups().values() for role in roles]
    assert sorted(grouped) == sorted(role_names()) and "syntax" in role_groups()
