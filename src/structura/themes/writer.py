"""Write a theme document back to TOML (docs/13 §3). Themes only hold strings, booleans and one level of
inline tables ({ color = "#…", bold = true }), so a small writer is enough and avoids another dependency."""

from __future__ import annotations

from typing import Any

TABLES = ("meta", "palette", "roles", "syntax", "viewport")


def _value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, dict):
        return "{ " + ", ".join(f"{k} = {_value(v)}" for k, v in value.items()) + " }"
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def _key(key: str) -> str:
    return key if key.replace("_", "").isalnum() else f'"{key}"'


def to_toml(data: dict[str, Any], header: str = "") -> str:
    lines = [f"# {header}"] if header else []
    for table in (*TABLES, *(t for t in data if t not in TABLES)):
        entries = data.get(table)
        if not entries:
            continue
        lines += ["", f"[{table}]"] if lines else [f"[{table}]"]
        lines += [f"{_key(k)} = {_value(v)}" for k, v in entries.items()]
    return "\n".join(lines) + "\n"
