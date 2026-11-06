"""Quick fixes (docs/12 §2.2): each offered fix removes its diagnostic."""

from __future__ import annotations

import pytest

from structura.core.lang.analysis import analyze
from structura.core.lang.fixes import apply_edits, quick_fixes

CASES = [
    ("E003", "set maxdepth 5\ntop\nrule top { { x 1 } missing }\n", "Create rule 'missing'"),
    ("W101", "set maxdepth 5\ntop\nrule top { box }\nrule lonely {\n  { x 1 } box\n}\n", "Remove unused rule 'lonely'"),
    ("W106", "{ size 2 } box\n", "Replace 'size' with 's'"),
    ("W108", "// spiral\nr\nrule r { { x 1 } r box }\n", "Add 'set maxdepth 100'"),
    ("W109", "set rng old\nbox\n", "Remove 'set rng old'"),
    ("W114", "material gold {\n  metallic 1\n}\nbox::gold\n", "Add '#version 2' (EisenScript v2)"),
]


@pytest.mark.parametrize(("code", "text", "title"), CASES, ids=[c[0] for c in CASES])
def test_fix_is_offered_and_removes_the_diagnostic(code: str, text: str, title: str) -> None:
    diagnostics = [d for d in analyze(text).diagnostics if d.code == code]
    assert diagnostics, f"{code} not reported"
    fixes = quick_fixes(text, diagnostics)
    assert [f.title for f in fixes] == [title]
    fixed = apply_edits(text, fixes[0].edits)
    assert code not in {d.code for d in analyze(fixed).diagnostics}, fixed


def test_fixes_keep_the_rest_of_the_script() -> None:
    text = "// title\n#define w 2\nr\nrule r { { x w } r box }\n"
    fixed = apply_edits(text, quick_fixes(text, [d for d in analyze(text).diagnostics if d.code == "W108"])[0].edits)
    assert fixed == "// title\n#define w 2\nset maxdepth 100\nr\nrule r { { x w } r box }\n"


def test_codes_without_a_fix_offer_nothing() -> None:
    text = "set maxdepth 5\ntop\nrule top { ping }\nrule ping { pong }\nrule pong { ping }\n"
    assert quick_fixes(text, list(analyze(text).diagnostics)) == []
