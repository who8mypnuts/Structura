"""The welcome page (docs/14 §5.1)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QPushButton, QToolButton

from structura.ui.app_window import MainWindow


def test_welcome_page_shows_while_no_script_is_open(window: MainWindow, tmp_path: Path) -> None:
    assert window.editor_area.currentWidget() is window.welcome
    script = tmp_path / "spiral.es"
    script.write_text("box\n")
    window.docs.recent.add(script)
    window.welcome.new_script.emit()
    assert window.editor_area.currentWidget() is window.tabs and window.tabs.count() == 1
    window.tabs.close_tab(0)
    assert window.editor_area.currentWidget() is window.welcome
    recent = [b for b in window.welcome.findChildren(QPushButton) if b.accessibleName() == "spiral.es"]
    assert recent  # refreshed when shown again
    recent[0].click()
    assert window.tabs.current() is not None and window.tabs.current().path == script
    window.tabs.close_tab(0)
    themes = [b for b in window.welcome.findChildren(QToolButton) if b.accessibleName() == "Nord Light"]
    themes[0].click()
    assert window.themes.theme.meta.id == "nord-light" and window.settings.value("appearance/theme") == "nord-light"


def test_welcome_reports_the_render_device(window: MainWindow) -> None:
    window.welcome._device_found(("CUDA NVIDIA GeForce GTX 1660", True))
    assert "GTX 1660" in window.welcome.device.text() and "✓" in window.welcome.device.text()
    window.welcome._device_found(("CPU", False))
    assert "cores" in window.welcome.device.text()
