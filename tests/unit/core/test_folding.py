"""Fold ranges (docs/12 §2.1): brace blocks and comment runs, computed with the highlighting lexer."""

from __future__ import annotations

from structura.core.lang.folding import FoldRange, fold_ranges

SCRIPT = """// title
// author
set maxdepth 20
rule tree {
  { y 1 } tree
  rule_inner_like_text { }
}
/* notes {
   not a brace }
*/
material gold {
  metallic 1
}
rule short { box
} tree
"""


def test_blocks_and_comment_runs() -> None:
    assert fold_ranges(SCRIPT) == (
        FoldRange(0, 1, "comment"),
        FoldRange(3, 6, "block"),
        FoldRange(7, 9, "comment"),
        FoldRange(10, 12, "block"),
    )


def test_braces_in_comments_do_not_fold_and_code_after_a_closer_stays_visible() -> None:
    ranges = fold_ranges(SCRIPT)
    assert all(r.start != 13 for r in ranges)  # 'rule short { box' / '} tree': the closer line carries code
    text = "rule a {\n  box\n  box\n} a\n"
    assert fold_ranges(text) == (FoldRange(0, 2, "block"),)


def test_nested_blocks_are_ordered_outer_first() -> None:
    text = "rule a {\n  {\n    x 1\n  } a\n  box\n}\n"
    assert fold_ranges(text) == (FoldRange(0, 5, "block"), FoldRange(1, 2, "block"))


def test_a_single_comment_line_does_not_fold() -> None:
    assert fold_ranges("// one\nbox\n") == ()
