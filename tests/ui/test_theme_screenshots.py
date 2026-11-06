"""Screenshot test of every built-in theme (docs/13 §10): a reference widget with the editor (every syntax
role), the Problems panel and common controls, compared with a committed baseline within a tolerance.

Regenerate the baselines after an intended change of the style sheet or the reference:
    STRUCTURA_UPDATE_THEME_SHOTS=1 pytest tests/ui/test_theme_screenshots.py
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest
from PIL import Image
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from pytestqt.qtbot import QtBot

from structura.core.lang.analysis import analyze
from structura.themes.loader import builtin_ids, load_theme
from structura.themes.qss import Fonts
from structura.ui.dialogs.theme_editor import SAMPLE
from structura.ui.editor.code_editor import CodeEditor
from structura.ui.fonts import register_fonts
from structura.ui.panels.problems import ProblemsPanel
from structura.ui.theming import apply_theme

BASELINES = Path(__file__).resolve().parents[1] / "golden" / "themes"
SIZE = (560, 360)
MEAN_TOLERANCE = 2.0  # mean absolute difference per channel (0–255)
OUTLIER_LEVEL, OUTLIER_FRACTION = 48, 0.01  # at most 1% of pixels may differ strongly (glyph anti-aliasing)


def reference(theme_id: str) -> QWidget:
    theme = load_theme(theme_id)
    app = QApplication.instance()
    assert isinstance(app, QApplication)
    apply_theme(app, theme, Fonts(ui_size=10, code_size=10))
    root = QWidget()
    editor = CodeEditor(theme)
    editor.setPlainText(SAMPLE)
    analysis = analyze(SAMPLE)
    editor.highlighter.set_analysis(analysis)
    editor.set_diagnostics(list(analysis.diagnostics))
    problems = ProblemsPanel()
    problems.show_diagnostics(SAMPLE, list(analysis.diagnostics))
    controls = QHBoxLayout()
    for widget in (QPushButton("Build"), QLineEdit("seed 42"), QCheckBox("Live"), QComboBox()):
        controls.addWidget(widget)
    layout = QVBoxLayout(root)
    layout.addLayout(controls)
    layout.addWidget(editor, 3)
    layout.addWidget(problems, 1)
    root.resize(*SIZE)
    return root


def _grab(widget: QWidget) -> np.ndarray:
    image = widget.grab().toImage().convertToFormat(widget.grab().toImage().Format.Format_RGB888)
    buffer = np.frombuffer(image.constBits(), np.uint8, image.sizeInBytes())
    return (
        buffer.reshape(image.height(), image.bytesPerLine())[:, : image.width() * 3]
        .reshape(image.height(), image.width(), 3)
        .copy()
    )


@pytest.mark.parametrize("theme_id", builtin_ids())
def test_theme_matches_its_baseline(qtbot: QtBot, theme_id: str) -> None:
    register_fonts()
    widget = reference(theme_id)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.wait(50)
    shot = _grab(widget)
    baseline = BASELINES / f"{theme_id}.png"
    if os.environ.get("STRUCTURA_UPDATE_THEME_SHOTS") or not baseline.exists():
        BASELINES.mkdir(parents=True, exist_ok=True)
        Image.fromarray(shot).save(baseline, optimize=True)
        if not os.environ.get("STRUCTURA_UPDATE_THEME_SHOTS"):
            pytest.fail(f"no baseline for {theme_id}: wrote {baseline.name}; review and commit it")
        return
    expected = np.asarray(Image.open(baseline).convert("RGB"))
    assert expected.shape == shot.shape, f"size changed: {expected.shape} → {shot.shape}"
    diff = np.abs(expected.astype(int) - shot.astype(int))
    outliers = float((diff.max(axis=2) > OUTLIER_LEVEL).mean())
    assert diff.mean() < MEAN_TOLERANCE and outliers < OUTLIER_FRACTION, (
        f"{theme_id}: mean diff {diff.mean():.2f}, {100 * outliers:.2f}% strong differences"
    )
