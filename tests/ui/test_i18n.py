"""Translations (docs/14 §8): commands, menus and docks follow the installed language."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot

from structura.services.settings import SettingsService
from structura.ui.app_window import MainWindow
from structura.ui.i18n import I18N, available, install

sys.path.insert(0, str(Path(__file__).parents[2] / "tools"))
import update_translations


@pytest.fixture
def pseudo() -> Iterator[None]:
    assert install("pseudo") == "pseudo"
    yield
    install("en")


def test_the_pseudo_locale_translates_menus_commands_and_docks(qtbot: QtBot, tmp_path: Path, pseudo: None) -> None:
    window = MainWindow(SettingsService(tmp_path / "s.ini"))
    qtbot.addWidget(window)
    try:
        menus = [a.text() for a in window.menuBar().actions()]
        assert menus[0].startswith("&[") and all("[" in m for m in menus)
        assert window.registry.action("build.run").text().startswith("[Bûîld")
        assert window.docks["Console"].windowTitle().startswith("[")
    finally:
        window.runner.shutdown()


def test_catalogues_are_up_to_date_and_listed() -> None:
    tool = Path(__file__).parents[2] / "tools" / "update_translations.py"
    check = subprocess.run([sys.executable, str(tool), "--check"], capture_output=True, text=True, check=False)
    assert check.returncode == 0, check.stderr  # a separate process: the tool builds a window of its own
    assert len(update_translations.read_ts(I18N / "structura_pseudo.ts")) > 150
    assert (I18N / "structura_pseudo.qm").exists() and {"pseudo", "de"} <= set(available())


def test_german_is_complete(qtbot: QtBot, tmp_path: Path) -> None:
    catalogue = update_translations.read_ts(I18N / "structura_de.ts")
    assert catalogue and all(catalogue.values())  # every string translated
    assert install("de") == "de"
    try:
        window = MainWindow(SettingsService(tmp_path / "s.ini"))
        qtbot.addWidget(window)
        assert next(a.text() for a in window.menuBar().actions()) == "&Datei"
        window.runner.shutdown()
    finally:
        install("en")
