"""Variation Explorer (docs/14 §5.3): a grid of seed variations with thumbnails; click one to adopt it.

Each cell is one compute-lane Job: build with that seed (capped at render.thumbnail.MAX_OBJECTS), then a
small 'preview' render on the CPU backend. Cells arrive as they finish; a new exploration cancels the old
one (latest-wins keys)."""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from PySide6.QtCore import QSize, Qt, Signal, Slot
from PySide6.QtGui import QAction, QIcon, QImage, QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ...core.build.api import build_capped
from ...core.lang.api import compile_script
from ...core.lang.compile.program import RuleProgram
from ...core.lang.legacy.preprocessor import GuiParameter
from ...render.thumbnail import MAX_OBJECTS, thumbnail_rgb
from ...services.jobs import FunctionJob, JobContext, JobRunner, Lane
from ..i18n import tr

GRID = 3
THUMB = QSize(150, 112)  # rendered size; shown smaller when the dock is narrow
MIN_THUMB_WIDTH = 64
CELL_PADDING = 12  # tool-button frame around the icon


@dataclass(frozen=True)
class Variation:
    cell: int
    seed: int
    rgb: np.ndarray  # uint8[H, W, 3]
    objects: int
    round: int = 0  # the exploration it belongs to (older ones are ignored)
    params: dict[str, float] | None = None  # parameter variations: the values of this cell


def variation_job(source: RuleProgram | str, cell: int, seed: int, round_: int = 0,
                  params: dict[str, float] | None = None) -> Callable[[JobContext], Variation]:  # fmt: skip
    """``source``: a compiled program (seed variations) or the script text (parameter variations)."""

    def run(ctx: JobContext) -> Variation:
        program = compile_script(source, seed, params).program if isinstance(source, str) else source
        scene = build_capped(program, seed, MAX_OBJECTS)
        ctx.check_cancelled()
        rgb = thumbnail_rgb(scene, (THUMB.width(), THUMB.height()))
        return Variation(cell, seed, rgb, len(scene), round_, params)

    return run


def jitter(
    parameters: list[GuiParameter], base: dict[str, float], spread: float, rng: random.Random
) -> dict[str, float]:
    """``base`` moved by up to ``spread`` of each slider's range, kept inside it (integers stay integers)."""
    out = {}
    for p in parameters:
        value = base.get(p.name, p.default) + rng.uniform(-1.0, 1.0) * spread * (p.maximum - p.minimum)
        value = min(p.maximum, max(p.minimum, value))
        out[p.name] = float(round(value)) if p.kind == "int" else value
    return out


class VariationExplorer(QWidget):
    adopt = Signal(int)  # seed
    adopt_params = Signal(object)  # dict[str, float]: a parameter variation

    def __init__(self, runner: JobRunner, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.runner = runner
        self.reroll = QPushButton(tr("New variations"))
        self.mode = QComboBox()
        self.mode.setAccessibleName(tr("Vary"))
        self.mode.addItem(tr("Seeds"), "seeds")
        self.mode.addItem(tr("Parameters"), "params")
        self.mode.setToolTip(tr("Vary the seed, or the #define sliders around their current values"))
        self.cells: list[QToolButton] = []
        grid = QGridLayout()
        for i in range(GRID * GRID):
            grid.addWidget(self._cell(i), i // GRID, i % GRID)
        self.grid = grid
        top = QHBoxLayout()
        top.addWidget(self.mode)
        top.addWidget(self.reroll, 1)
        layout = self.column = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addLayout(grid)
        layout.addStretch(1)
        self.seeds = [0] * (GRID * GRID)
        self.cell_params: list[dict[str, float] | None] = [None] * (GRID * GRID)
        self.round = 0
        self._spread = 0.25
        self.program: RuleProgram | None = None
        self.script: tuple[str, int, list[GuiParameter], dict[str, float]] | None = None  # text, seed, sliders, base
        self.reroll.clicked.connect(self._again)

    def _cell(self, i: int) -> QToolButton:
        button = QToolButton()
        button.setIconSize(THUMB)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        button.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)  # long labels elide
        button.clicked.connect(lambda _c=False, i=i: self._adopt(i))
        button.setAccessibleName(tr("Variation {n}").format(n=i + 1))
        button.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
        expand = QAction(tr("Expand Around This"), button)
        expand.triggered.connect(lambda _c=False, i=i: self.expand(i))
        button.addAction(expand)
        self.cells.append(button)
        return button

    def _again(self) -> None:
        if self.mode.currentData() == "params" and self.script is not None:
            self.explore_params(*self.script)
        elif self.program is not None:
            self.explore(self.program)

    def _start(self, cell: int, job: Callable[[JobContext], Variation], label: str) -> None:
        button = self.cells[cell]
        button.setIcon(QIcon())
        button.setText(label)
        self.runner.submit(
            FunctionJob(f"variation {cell}", Lane.COMPUTE, job, key=f"variation:{cell}")
        ).finished.connect(self._show)

    def explore(self, program: RuleProgram | None, seeds: list[int] | None = None) -> None:
        if program is None:
            return
        self.program, self.round = program, self.round + 1
        self.seeds = seeds or [random.randint(0, 32767) for _ in self.cells]
        self.cell_params = [None] * len(self.cells)
        for cell, seed in enumerate(self.seeds):
            self._start(cell, variation_job(program, cell, seed, self.round), f"seed {seed} …")

    def explore_params(self, text: str, seed: int, parameters: list[GuiParameter], base: dict[str, float],
                       spread: float = 0.25) -> None:  # fmt: skip
        """Nine variations of the sliders around ``base`` (the first cell is ``base`` itself)."""
        self.script, self.round = (text, seed, parameters, base), self.round + 1
        rng = random.Random(self.round)
        self.seeds = [seed] * len(self.cells)
        self.cell_params = [dict(base), *(jitter(parameters, base, spread, rng) for _ in self.cells[1:])]
        for cell, params in enumerate(self.cell_params):
            self._start(cell, variation_job(text, cell, seed, self.round, params), tr("variation …"))
        self._spread = spread

    def expand(self, cell: int) -> None:
        """Explore closer around one cell: its parameters with half the spread."""
        params = self.cell_params[cell]
        if self.script is not None and params is not None:
            text, seed, parameters, _ = self.script
            self.explore_params(text, seed, parameters, params, self._spread / 2)

    @Slot(object)
    def _show(self, result: object) -> None:
        if not isinstance(result, Variation) or result.round != self.round:
            return  # a newer exploration replaced this cell
        rgb = np.ascontiguousarray(result.rgb)
        h, w, _ = rgb.shape
        image = QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()
        button = self.cells[result.cell]
        button.setIcon(QIcon(QPixmap.fromImage(image)))
        if result.params is None:
            button.setText(f"seed {result.seed} · {result.objects:,}")
            button.setToolTip(f"Seed {result.seed}: {result.objects:,} objects. Click to use this seed.")
        else:
            values = ", ".join(f"{k} {v:.3g}" for k, v in result.params.items())
            button.setText(f"{result.objects:,}")
            button.setToolTip(f"{values}\nClick to use these values; right-click ▸ Expand Around This.")

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._fit_thumbnails()

    def _fit_thumbnails(self) -> None:
        """Scale the thumbnails to the dock width (between MIN_THUMB_WIDTH and the rendered size)."""
        margins = self.column.contentsMargins()
        spare = self.width() - margins.left() - margins.right() - (GRID - 1) * self.grid.horizontalSpacing()
        width = max(MIN_THUMB_WIDTH, min(THUMB.width(), spare // GRID - CELL_PADDING))
        size = QSize(width, width * THUMB.height() // THUMB.width())
        for button in self.cells:
            button.setIconSize(size)

    def _adopt(self, cell: int) -> None:
        params = self.cell_params[cell]
        if params is not None:
            self.adopt_params.emit(params)
        else:
            self.adopt.emit(self.seeds[cell])
