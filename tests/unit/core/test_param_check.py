"""E015 (docs/05 §9.2): typed #param defaults and uses."""

from __future__ import annotations

from structura.core.lang.analysis import analyze

HEAD = "#version 2\n"


def _e015(text: str) -> list[str]:
    full = HEAD + text
    return [full[d.span.start : d.span.end] for d in analyze(full).diagnostics if d.code == "E015"]


def test_defaults_must_fit_their_type_and_range() -> None:
    assert _e015("#param n int = 2.5 range 1..9\nbox\n") == ["2.5"]
    assert _e015("#param k float = 20 range 0..10\nbox\n") == ["20"]
    assert _e015("#param c color = 12\nbox\n") == ["12"]
    assert _e015("#param s enum = zig of a|b\nbox\n") == ["zig"]
    assert _e015("#param k float = 5 range 0..10\n#param c color = #f80\n{ x k color c } box\n") == []


def test_uses_must_fit_their_operator() -> None:
    assert _e015("#param c color = #f80\n{ x c } box\n") == ["c"]
    assert _e015("#param k float = 1 range 0..2\n{ color k } box\n") == ["k"]
    assert _e015("#param k float = 1 range 0..2\n3 * { x k } box\n") == []


def test_colour_switch_and_choice_parameters_substitute() -> None:
    from structura.core.lang.api import compile_script  # noqa: PLC0415

    text = (HEAD + "#param tint color = #f80\n#param caps bool = true\n#param style enum = tree of spiral|tree\n"
            "{ color tint x (caps * 2) } style\nrule tree { box }\nrule spiral { sphere }\n")  # fmt: skip
    kinds = [(p.kind, p.default) for p in analyze(text).parameters]
    assert kinds == [("color", float(0xFF8800)), ("bool", 1.0), ("enum", 1.0)]
    assert not [d for d in analyze(text).diagnostics if d.code in ("W101", "W102")]  # choices count as used
    source = compile_script(text, params={"style": 0.0, "tint": float(0x00FF00), "caps": 0.0}).preprocessed
    assert "{ color #00ff00 x 0 } spiral" in source
