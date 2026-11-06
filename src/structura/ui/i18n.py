"""Internationalisation (docs/14 §8): Qt translators for Structura's strings and Qt's own.

User-visible strings go through ``tr(text, context)``. Commands, menus and dock titles are translated where
they are shown (registry, menus, docks), so the tables that define them stay in English and the catalogue
extractor (tools/update_translations.py) finds every string in one place. Translations live in
resources/i18n/structura_<language>.qm; 'pseudo' is a generated accented locale for layout testing.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QCoreApplication, QLibraryInfo, QLocale, QTranslator

I18N = Path(__file__).resolve().parents[1] / "resources" / "i18n"
LANGUAGES = {"system": "System language", "en": "English", "de": "Deutsch", "pseudo": "Pseudo-locale (layout testing)"}
_installed: list[QTranslator] = []


def tr(text: str, context: str = "Structura") -> str:
    return QCoreApplication.translate(context, text)


def available() -> dict[str, str]:
    """Language code → name, for the languages that have a compiled catalogue (plus system and English)."""
    found = {p.stem.removeprefix("structura_"): p.stem for p in I18N.glob("structura_*.qm")}
    return {k: v for k, v in LANGUAGES.items() if k in ("system", "en") or k in found} | {
        k: QLocale(k).nativeLanguageName() or k for k in found if k not in LANGUAGES
    }


def install(language: str = "system") -> str:
    """Install the translators for ``language`` (replacing earlier ones); returns the code used."""
    app = QCoreApplication.instance()
    for translator in _installed:
        QCoreApplication.removeTranslator(translator)
    _installed.clear()
    code = QLocale.system().name().split("_")[0] if language == "system" else language
    if app is None or code == "en":
        return code
    ours = QTranslator(app)
    if ours.load(str(I18N / f"structura_{code}.qm")):
        QCoreApplication.installTranslator(ours)
        _installed.append(ours)
    qt = QTranslator(app)
    if qt.load(QLocale(code), "qtbase", "_", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
        QCoreApplication.installTranslator(qt)
        _installed.append(qt)
    return code
