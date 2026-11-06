"""VS Code and base16 theme import (docs/13 §7)."""

from __future__ import annotations

import json
from pathlib import Path

from structura.themes.derive import resolve_theme
from structura.themes.importers import from_base16, from_vscode, import_theme
from structura.themes.loader import load_file

VSCODE = {
    "name": "Test Dark",
    "type": "dark",
    "colors": {"editor.background": "#101820", "editor.foreground": "#e0e0e0", "focusBorder": "#ff9900"},
    "tokenColors": [
        {"scope": "comment", "settings": {"foreground": "#6a737d", "fontStyle": "italic"}},
        {"scope": ["keyword", "keyword.operator"], "settings": {"foreground": "#ff79c6"}},
        {"scope": "keyword.operator", "settings": {"foreground": "#8be9fd"}},
        {"scope": "constant.numeric", "settings": {"foreground": "#bd93f9"}},
    ],
}
BASE16 = (
    'scheme: "Ocean Test"\nauthor: "someone"\nbase00: "2b303b"\nbase05: "c0c5ce"\nbase0D: "8fa1b3"\nbase08: "bf616a"\n'
)


def test_vscode_roles_and_longest_scope_prefix_wins() -> None:
    doc = from_vscode("// comment\n" + json.dumps(VSCODE), "test-dark")
    assert doc["roles"]["ui.bg"] == "#101820" and doc["roles"]["ui.accent"] == "#FF9900"
    assert doc["syntax"]["syntax.operator"]["color"] == "#8BE9FD"  # 'keyword.operator' beats 'keyword'
    assert doc["syntax"]["syntax.comment"]["italic"]
    theme = resolve_theme(doc)
    assert theme.meta.kind == "dark" and theme["syntax.number"]


def test_base16_and_file_round_trip(tmp_path: Path) -> None:
    doc = from_base16(BASE16, "ocean")
    assert doc["meta"]["name"] == "Ocean Test" and doc["palette"]["base00"] == "#2B303B"
    source = tmp_path / "ocean.yaml"
    source.write_text(BASE16)
    theme = load_file(import_theme(source, tmp_path / "themes"))
    assert theme["ui.bg"] == "#2B303B" and theme.meta.kind == "dark"
