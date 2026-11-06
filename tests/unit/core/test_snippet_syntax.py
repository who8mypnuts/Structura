"""Snippet tab stops (docs/12 §2.3)."""

from __future__ import annotations

from structura.core.lang.analysis import analyze
from structura.core.lang.catalog import snippets
from structura.core.lang.snippet_syntax import Stop, expand, plain


def test_expand_fills_defaults_and_orders_stops() -> None:
    text, stops = expand("rule ${1:r} { { x ${2:1} } ${1:r} }$0")
    assert text == "rule r { { x 1 } r }"
    assert stops == (Stop(1, 5, 6), Stop(1, 17, 18), Stop(2, 13, 14), Stop(0, 20, 20))


def test_bare_stops_mirror_the_first_default() -> None:
    assert expand("${1:name} $1") == ("name name", (Stop(1, 0, 4), Stop(1, 5, 9)))


def test_every_pattern_snippet_is_valid_eisenscript_once_expanded() -> None:
    for s in snippets():
        if s.group == "Patterns":
            body = plain(s.text)
            call = body.split()[1] if body.startswith("rule") else ""
            script = f"set maxdepth 20\n{call}\n{body}\n"
            assert not [d for d in analyze(script).diagnostics if d.severity.name == "ERROR"], script
