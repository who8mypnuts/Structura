"""Extract Structura's user-visible strings into Qt Linguist catalogues and compile them (docs/14 §8).

    python tools/update_translations.py            # update resources/i18n/*.ts, regenerate 'pseudo', compile .qm
    python tools/update_translations.py --check    # fail if a catalogue is missing strings (CI)

Sources: every registered command's title, tip, menu and submenu (from an offscreen window), the dock titles,
and every literal ``tr("…", "Context")`` call under src/structura/ui. Existing translations in .ts files are
kept; translators edit them with Qt Linguist (pyside6-linguist). The 'pseudo' locale is generated: accented,
bracketed and ~30 % longer, to find clipped layouts and untranslated strings.
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "src" / "structura" / "ui"
I18N = ROOT / "src" / "structura" / "resources" / "i18n"
LRELEASE = Path(sys.executable).with_name("pyside6-lrelease")
ACCENTS = str.maketrans("aceinouyACEINOUY", "àçéîñöûýÀÇÉÎÑÖÛÝ")
Catalogue = dict[tuple[str, str], str]  # (context, source) → translation


def _constant(node: ast.AST | None) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _commands() -> set[tuple[str, str]]:
    """Every registered command's title and tip, menu and submenu, read from a live (offscreen) window, so
    commands made in loops (edits, view toggles, exporters, snippets) are included."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("STRUCTURA_PREVIEW", "off")
    from PySide6.QtWidgets import QApplication  # noqa: PLC0415

    from structura.services.settings import SettingsService  # noqa: PLC0415
    from structura.ui.app_window import MainWindow  # noqa: PLC0415

    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory() as tmp:
        window = MainWindow(SettingsService(Path(tmp) / "settings.ini"))
        found = set()
        for c in window.registry.commands():
            found |= {("Menus", c.category)} | {("Menus", m) for m in (c.menu, c.submenu) if m}
            if c.id.startswith("insert."):  # snippet titles are EisenScript code, not prose
                continue
            found.add(("Commands", c.title))
            found |= {("Commands", c.tip)} if c.tip else set()
        window.runner.shutdown()
        window.deleteLater()
    del app
    return found


def _tr_calls() -> set[tuple[str, str]]:
    found = set()
    for path in UI.rglob("*.py"):
        for call in (n for n in ast.walk(ast.parse(path.read_text(encoding="utf-8"))) if isinstance(n, ast.Call)):
            if getattr(call.func, "id", "") == "tr" and call.args and (text := _constant(call.args[0])):
                context = _constant(call.args[1]) if len(call.args) > 1 else "Structura"
                found.add((context or "Structura", text))
    return found


def _fixed() -> set[tuple[str, str]]:
    window = (UI / "app_window.py").read_text(encoding="utf-8")
    menus = re.search(r"MENU_ORDER = \(([^)]*)\)", (UI / "menus.py").read_text(encoding="utf-8"))
    names = re.findall(r'"([^"]+)"', menus.group(1)) if menus else []
    return ({("Panels", t) for t in re.findall(r'\("([^"]+)", self\.\w+\)', window)}
            | {("Menus", m) for m in [*names, "Open Recent", "Timeline"]})  # fmt: skip


def strings() -> set[tuple[str, str]]:
    return _commands() | _tr_calls() | _fixed()


def pseudo(text: str) -> str:
    """Accented, bracketed and padded; '{placeholders}' stay intact for str.format."""
    padding = "~" * max(1, len(text) * 3 // 10)
    parts = re.split(r"(\{[^}]*\})", text)
    accented = "".join(p if p.startswith("{") else p.translate(ACCENTS) for p in parts)
    return f"[{accented} {padding}]"


def read_ts(path: Path) -> Catalogue:
    if not path.exists():
        return {}
    out = {}
    for context in ET.parse(path).getroot().iter("context"):
        name = context.findtext("name") or ""
        for message in context.iter("message"):
            out[(name, message.findtext("source") or "")] = message.findtext("translation") or ""
    return out


def write_ts(path: Path, language: str, catalogue: Catalogue) -> None:
    root = ET.Element("TS", version="2.1", language=language)
    for context in sorted({c for c, _ in catalogue}):
        node = ET.SubElement(root, "context")
        ET.SubElement(node, "name").text = context
        for (ctx, source), translation in sorted(catalogue.items()):
            if ctx == context:
                message = ET.SubElement(node, "message")
                ET.SubElement(message, "source").text = source
                item = ET.SubElement(message, "translation")
                item.text = translation
                if not translation:
                    item.set("type", "unfinished")
    ET.indent(root)
    path.write_text('<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE TS>\n' + ET.tostring(root, "unicode") + "\n",
                    encoding="utf-8")  # fmt: skip


def update(check: bool) -> int:
    wanted = strings()
    stale = []
    for path in [*sorted(I18N.glob("structura_*.ts")), I18N / "structura_pseudo.ts"]:
        language = path.stem.removeprefix("structura_")
        old = read_ts(path)
        new = {key: (pseudo(key[1]) if language == "pseudo" else old.get(key, "")) for key in wanted}
        if check and set(new) != set(old):
            stale.append(path.name)
            continue
        write_ts(path, language, new)
        subprocess.run([str(LRELEASE), "-silent", str(path), "-qm", str(path.with_suffix(".qm"))], check=True)
    for name in stale:
        print(f"stale: {name} (run python tools/update_translations.py)", file=sys.stderr)
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(update("--check" in sys.argv))
