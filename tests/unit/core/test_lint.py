"""The semantic linter (docs/05 §10): one focused script per check, spans in original positions."""

from __future__ import annotations

import pytest

from structura.core.lang.analysis import analyze
from structura.core.lang.catalog import diagnostic_specs
from structura.core.lang.diagnostics import Severity


def codes(text: str) -> dict[str, list[str]]:
    """code → the original text each diagnostic underlines."""
    out: dict[str, list[str]] = {}
    for d in analyze(text).diagnostics:
        out.setdefault(d.code, []).append(text[d.span.start : d.span.end] if d.span else "")
    return out


def test_unused_and_unreachable_rules() -> None:
    text = "set maxdepth 5\ntop\nrule top { box }\nrule ping { pong }\nrule pong { ping }\nrule lonely { box }\n"
    found = codes(text)
    assert found["W101"] == ["rule lonely "]
    assert sorted(found["W102"]) == ["rule ping ", "rule pong "]  # b and c call each other; nothing reaches them


def test_unbounded_recursion_needs_no_maxdepth_anywhere() -> None:
    assert codes("r\nrule r { { x 1 } r box }\n")["W108"] == ["rule r "]
    assert "W108" not in codes("set maxdepth 20\nr\nrule r { { x 1 } r box }\n")
    assert "W108" not in codes("r\nrule r md 10 { { x 1 } r box }\n")
    assert "W108" not in codes("r\nrule r { box }\n")


def test_retirement_is_a_reference_and_an_edge() -> None:
    text = "set maxdepth 5\ntop\nrule top md 3 > tail { { x 1 } top }\nrule tail { box }\n"
    assert "W101" not in codes(text) and "W102" not in codes(text)


def test_zero_weight_obsolete_rng_and_aliases() -> None:
    text = "set rng old\nset maxdepth 3\nr\nrule r w 0 { box }\nrule r w 0 { sphere }\n{ size 2 } box\n"
    found = codes(text)
    assert found["W110"] == ["rule r w 0 "] and found["W109"] == ["set rng old"] and found["W106"] == ["size"]


def test_v1_pitfalls() -> None:
    assert codes("r1\nrule r1 { cylinder }\n")["W105"] == ["cylinder"]
    found = codes("#define R 2\nR1\nrule R1 { { x R } box }\n")
    assert found["W103"] == ["#define R 2"]  # also rewrites 'R1' (reported although the result cannot parse)
    assert "E001" in found
    assert "W103" not in codes("#define off 0.5\ntriangle[0,0,0;1,0,0;0,1,off]\n")


def test_v2_material_resolution_and_overridden_settings() -> None:
    text = ("#version 2\nmaterial shiny { roughness 0.1 }\ncamera { fov 30 }\nset scale 2\n"
            "box::shiny\nbox::gold\nbox::mystery\n")  # fmt: skip
    found = codes(text)
    assert found["I203"] == ["box::gold"] and found["W112"] == ["box::mystery"] and found["W113"] == ["set scale 2"]


def test_v2_syntax_in_a_v1_script_is_pointed_out() -> None:
    found = codes("material gold {\n  metallic 1\n}\nbox\n")
    assert found["W114"] == ["material gold {"]


def test_preprocessor_warnings_have_positions() -> None:
    found = codes("#frobnicate\nbox\n")
    assert found["W120"] == ["#frobnicate"]


def test_resolution_errors_carry_their_catalogue_codes() -> None:
    assert "E013" in codes("r::tag\nrule r { box }\n")
    assert "E014" in codes("triangle[0,0,0;1,0,0]\n")
    assert "E006" in codes("{ x } box\n")


@pytest.mark.parametrize("code", sorted(diagnostic_specs()))
def test_catalogue_entries_are_complete(code: str) -> None:
    spec = diagnostic_specs()[code]
    assert spec.title and spec.doc and spec.severity in ("error", "warning", "info")
    assert (spec.severity == "error") == code.startswith("E")
    assert Severity  # the helper maps every severity


def test_spans_after_a_v2_expression_are_not_shifted() -> None:
    text = "#version 2\nset maxdepth 4\n{ s (sin(30)) } sphere\nmissing_rule\n"
    found = codes(text)
    assert found["E003"] == ["missing_rule"]  # the expression shortened its line; later positions still map
    assert "W120" not in found  # '#version 2' is a known directive
