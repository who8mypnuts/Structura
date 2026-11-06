"""Golden compatibility suite: every corpus script × seed must match Structure Synth 1.5 (docs/18 §3)."""

from __future__ import annotations

import json

import pytest

from tests.golden.golden_compare import DATA, compare

_MANIFEST = json.loads((DATA / "manifest.json").read_text()) if (DATA / "manifest.json").exists() else {"scripts": []}
_CASES = [(e["id"], seed) for e in _MANIFEST["scripts"] if not e["javascript"] for seed in _MANIFEST["seeds"]]


@pytest.mark.golden
@pytest.mark.parametrize(("script_id", "seed"), _CASES, ids=[f"{i}-s{s}" for i, s in _CASES])
def test_matches_structure_synth(script_id: str, seed: int) -> None:
    outcome = compare(script_id, seed)
    assert outcome.ok, outcome.message
