"""Theme importers (docs/13 §7): VS Code colour themes (JSON) and base16/base24 schemes (YAML) → the
Structura theme document, which derive.resolve_theme completes and contrast-checks."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import tomli_w

VSCODE_UI = {  # VS Code 'colors' key → Structura role
    "editor.background": "ui.bg",
    "editor.foreground": "ui.fg",
    "focusBorder": "ui.accent",
    "button.background": "ui.accent",
    "sideBar.background": "ui.bg.alt",
    "editorWidget.background": "ui.bg.raised",
    "input.background": "ui.bg.sunken",
    "panel.border": "ui.border",
    "editorLineNumber.foreground": "editor.line.number",
    "editorLineNumber.activeForeground": "editor.line.number.active",
    "editor.lineHighlightBackground": "editor.line.current",
    "editor.selectionBackground": "editor.selection",
    "editorCursor.foreground": "editor.cursor",
    "errorForeground": "status.error",
    "editorWarning.foreground": "status.warning",
    "statusBar.background": "statusbar.bg",
    "statusBar.foreground": "statusbar.fg",
}
SCOPES = {  # TextMate scope prefix → syntax role (longest prefix wins)
    "comment": "syntax.comment",
    "keyword": "syntax.keyword",
    "keyword.operator": "syntax.operator",
    "storage": "syntax.keyword",
    "constant.numeric": "syntax.number",
    "constant": "syntax.color",
    "string": "syntax.string",
    "entity.name.function": "syntax.rule.def",
    "entity.name": "syntax.rule.ref",
    "support.function": "syntax.primitive",
    "entity.name.tag": "syntax.tag",
    "variable.parameter": "syntax.param",
    "meta.preprocessor": "syntax.preprocessor",
    "invalid": "syntax.rule.undefined",
    "storage.modifier": "syntax.modifier",
}
BASE16 = {"ui.bg": "base00", "ui.bg.alt": "base01", "ui.bg.raised": "base02", "ui.fg": "base05",
          "ui.accent": "base0D", "status.error": "base08", "status.warning": "base0A",
          "status.success": "base0B"}  # fmt: skip
BASE16_SYNTAX = {"syntax.comment": "base03", "syntax.keyword": "base0E", "syntax.operator": "base05",
                 "syntax.number": "base09", "syntax.color": "base09", "syntax.primitive": "base0C",
                 "syntax.rule.def": "base0D", "syntax.rule.ref": "base0D", "syntax.tag": "base0A",
                 "syntax.string": "base0B", "syntax.preprocessor": "base0F", "syntax.modifier": "base0E"}  # fmt: skip


def _hex(value: str) -> str:
    v = value.strip().lstrip("#")
    return "#" + v[:8].upper() if re.fullmatch(r"[0-9a-fA-F]{6}([0-9a-fA-F]{2})?", v[:8]) else ""


def _luminance_kind(hex_color: str) -> str:
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
    return "light" if 0.2126 * r + 0.7152 * g + 0.0722 * b > 140 else "dark"


def _token_roles(token_colors: list[dict[str, Any]]) -> dict[str, Any]:
    syntax: dict[str, Any] = {}
    ranked: dict[str, int] = {}
    for rule in token_colors:
        scopes = rule.get("scope", [])
        scopes = [s.strip() for s in (scopes.split(",") if isinstance(scopes, str) else scopes)]
        settings = rule.get("settings", {})
        color = _hex(str(settings.get("foreground", "")))
        if not color:
            continue
        style = str(settings.get("fontStyle", ""))
        for scope in scopes:
            for prefix, role in SCOPES.items():
                if scope.startswith(prefix) and len(prefix) >= ranked.get(role, -1):  # later rules win ties
                    ranked[role] = len(prefix)
                    syntax[role] = {"color": color, "bold": "bold" in style, "italic": "italic" in style}
    return syntax


def from_vscode(text: str, theme_id: str) -> dict[str, Any]:
    data = json.loads(re.sub(r"^\s*//.*$", "", text, flags=re.MULTILINE))  # VS Code allows comments
    colors = data.get("colors", {})
    roles = {role: _hex(str(colors[key])) for key, role in VSCODE_UI.items() if _hex(str(colors.get(key, "")))}
    roles.setdefault("ui.bg", "#1E1E1E")
    roles.setdefault("ui.fg", "#D4D4D4")
    roles.setdefault("ui.accent", "#007ACC")
    kind = str(data.get("type", _luminance_kind(roles["ui.bg"])))
    meta = {"id": theme_id, "name": str(data.get("name", theme_id)), "kind": "light" if "light" in kind else "dark"}
    return {"meta": meta, "roles": roles, "syntax": _token_roles(data.get("tokenColors", []))}


BASE16_LINE = re.compile(r'^\s*([\w-]+)\s*:\s*"?([^"\n#]*#?[0-9A-Fa-f]{6}|[^"\n]+?)"?\s*$', re.MULTILINE)


def from_base16(text: str, theme_id: str) -> dict[str, Any]:
    pairs: dict[str, str] = dict(BASE16_LINE.findall(text))
    palette = {k: _hex(v) for k, v in pairs.items() if k.startswith("base") and _hex(v)}
    name = str(pairs.get("scheme", pairs.get("name", theme_id))).strip()
    meta = {"id": theme_id, "name": name, "kind": _luminance_kind(palette.get("base00", "#000000")),
            "author": pairs.get("author", "").strip()}  # fmt: skip
    roles = {role: key for role, key in BASE16.items() if key in palette}
    syntax = {role: key for role, key in BASE16_SYNTAX.items() if key in palette}
    return {"meta": meta, "palette": palette, "roles": roles, "syntax": syntax}


def import_theme(path: Path, target_dir: Path) -> Path:
    """Convert a VS Code (.json) or base16 (.yaml/.yml) theme into a Structura TOML theme in target_dir."""
    theme_id = re.sub(r"[^a-z0-9-]+", "-", path.stem.lower()).strip("-") or "imported"
    text = path.read_text(encoding="utf-8")
    document = from_vscode(text, theme_id) if path.suffix.lower() == ".json" else from_base16(text, theme_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    out = target_dir / f"{theme_id}.toml"
    out.write_text(f"# Imported from {path.name}\n" + tomli_w.dumps(document), encoding="utf-8")
    return out
