"""Find in Files search (docs/12 §2.1)."""

from __future__ import annotations

import re

import pytest

from structura.core.text_search import pattern, search

TEXTS = {"a.es": "rule tree {\n  box\n  boxes\n}\n", "b.es": "Box\n"}


def test_plain_search_is_case_insensitive_by_default() -> None:
    found = search(TEXTS, pattern("box"))
    assert [(m.source, m.line, m.column) for m in found] == [("a.es", 1, 2), ("a.es", 2, 2), ("b.es", 0, 0)]
    assert TEXTS["a.es"][found[1].offset : found[1].offset + 3] == "box"


def test_whole_word_case_and_regex() -> None:
    assert len(search(TEXTS, pattern("box", whole_word=True))) == 2
    assert len(search(TEXTS, pattern("Box", case=True))) == 1
    assert [m.text for m in search(TEXTS, pattern(r"^rule \w+", regex=True))] == ["rule tree {"]
    with pytest.raises(re.error):
        pattern("(", regex=True)
