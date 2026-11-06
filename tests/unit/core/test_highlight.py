"""Editor line lexer (docs/12 §1): roles per token, block comments across lines."""

from __future__ import annotations

from structura.core.lang.analysis import analyze
from structura.core.lang.assist import complete, hover
from structura.core.lang.highlight import IN_BLOCK_COMMENT, lex_line


def roles(line: str, state: int = 0) -> list[tuple[str, str]]:
    tokens, _ = lex_line(line, state)
    return [(line[s : s + n], r) for s, n, r in tokens]


def test_statement_roles() -> None:
    assert roles("rule R1 md 10 > R2 {") == [
        ("rule", "keyword"), ("R1", "rule.def"), ("md", "modifier"), ("10", "number"),
        (">", "operator"), ("R2", "rule.ref"), ("{", "brace"),
    ]  # fmt: skip
    assert roles("{ x 1 color #f80 blend red 0.5 } box::shiny") == [
        ("{", "brace"), ("x", "operator"), ("1", "number"), ("color", "operator"), ("#f80", "color"),
        ("blend", "operator"), ("red", "color"), ("0.5", "number"), ("}", "brace"), ("box::shiny", "tag"),
    ]  # fmt: skip
    assert roles("set maxdepth 20")[1:] == [("maxdepth", "set.key"), ("20", "set.value")]
    assert roles("triangle[0,0,0;1,0,0;0,1,0]") == [("triangle", "primitive"), ("[0,0,0;1,0,0;0,1,0]", "bracket.arg")]


def test_comments_and_preprocessor() -> None:
    assert roles("#define N 10") == [("#define N 10", "preprocessor")]
    assert roles("# a note") == [("# a note", "comment")]
    assert roles("box // tail") == [("box", "primitive"), ("// tail", "comment")]
    tokens, state = lex_line("box /* open")
    assert state == IN_BLOCK_COMMENT and tokens[-1][2] == "comment"
    assert roles("still */ sphere", IN_BLOCK_COMMENT) == [("still */", "comment"), ("sphere", "primitive")]
    assert lex_line("inside", IN_BLOCK_COMMENT)[1] == IN_BLOCK_COMMENT


def test_completion_contexts() -> None:
    text = "rule R w 2 { box }\nrule R w 1 { sphere }\nR\n"
    analysis = analyze(text)

    def labels(probe: str) -> list[str]:
        return [i.label for i in complete(probe, len(probe), analysis).items]

    assert labels("set ma") == ["maxdepth", "maxobjects", "maxsize"]
    assert "raytracer::samples" in labels("set raytracer::s")
    assert labels("{ color re") == ["red"] and "rotate" not in labels("{ r")
    assert labels("{ r")[:3] == ["rx", "ry", "rz"]
    assert labels("rule Q ") == ["weight", "maxdepth"]
    assert labels("3 * { x 1 } ")[:2] == ["rule", "set"] and "r" in labels("3 * { x 1 } ")
    assert labels("#inc") == [] and labels("#jav") == ["javascript"]  # no #include in EisenScript
    assert "66.7%" in (hover(text, 6, analysis) or "")
    assert "Rotate" in (hover("{ rz 5 }", 3) or "")


def test_defines_and_functions_are_not_undefined_rules() -> None:
    text = "#version 2\n#define angle 20 (float:0-90)\n#define step 2\n{ rz angle x step s (sin(30)) } box\n"
    defined, _, defines = analyze(text).semantic_symbols()
    assert defined is not None and {"angle", "step"} <= defines
    line = "{ rz angle x step s (sin(30)) } box"
    roles = {line[s : s + n]: r for s, n, r in lex_line(line)[0]}
    assert roles["sin"] == "function"
