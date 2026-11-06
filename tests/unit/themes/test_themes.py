"""Theme engine: derivation, contrast enforcement, the 40 built-ins and the stylesheet (docs/13)."""

from __future__ import annotations

import pytest

from structura.core.color.oklab import contrast
from structura.themes.derive import catalogue, resolve_theme, role_names
from structura.themes.expr import ThemeError, split_alpha
from structura.themes.loader import builtin_ids, load_theme
from structura.themes.qss import css_color, render_qss

MINIMAL = {
    "meta": {"id": "t", "name": "T", "kind": "dark"},
    "palette": {"ink": "#E0E0E0"},
    "roles": {"ui.bg": "#202020", "ui.fg": "ink", "ui.accent": "#3399FF"},
}


def test_forty_builtins_six_nord_both_kinds() -> None:
    ids = builtin_ids()
    assert len(ids) == 40
    assert sum(i.startswith("nord") for i in ids) == 6
    kinds = [load_theme(i).meta.kind for i in ids]
    assert kinds.count("dark") == 22 and kinds.count("light") == 18


@pytest.mark.parametrize("theme_id", builtin_ids())
def test_builtin_themes_are_complete_and_pass_contrast(theme_id: str) -> None:
    theme = load_theme(theme_id)
    assert set(theme.colors) == set(role_names())
    for fg, bg, minimum in catalogue()[1]:
        (f, fa), (b, ba) = split_alpha(theme[fg]), split_alpha(theme[bg])
        if fa == 1 and ba == 1:
            assert contrast(f, b) >= minimum - 1e-6, f"{fg} on {bg}"
    assert theme.meta.pair in builtin_ids()


def test_minimal_theme_derives_every_role() -> None:
    theme = resolve_theme(MINIMAL)
    assert theme["ui.fg"] == "#E0E0E0"
    assert theme["editor.bg"] == "#202020"  # follows ui.bg
    assert split_alpha(theme["ui.hover"])[1] == pytest.approx(0.12, abs=0.01)
    assert theme.style("syntax.comment").color == theme["syntax.comment"]


def test_missing_required_roles_and_cycles_are_errors() -> None:
    with pytest.raises(ThemeError, match=r"ui\.accent"):
        resolve_theme({**MINIMAL, "roles": {"ui.bg": "#000000", "ui.fg": "#FFFFFF"}})
    cyclic = {**MINIMAL, "roles": {**MINIMAL["roles"], "ui.bg.alt": "ui.border", "ui.border": "ui.bg.alt"}}
    with pytest.raises(ThemeError, match="cycle"):
        resolve_theme(cyclic)


def test_low_contrast_author_colours_are_fixed_and_reported() -> None:
    data = {**MINIMAL, "syntax": {"syntax.comment": "#303030"}}
    theme = resolve_theme(data)
    assert contrast(theme["syntax.comment"], theme["editor.bg"]) >= 3.0
    assert any(a.startswith("syntax.comment") for a in theme.adjustments)


def test_stylesheet_renders_with_rgba_for_translucent_roles() -> None:
    qss = render_qss(load_theme("nord"))
    assert "QTabBar::tab:selected" in qss and "rgba(" in qss and "{{" not in qss
    assert css_color("#11223380") == "rgba(17, 34, 51, 128)"
