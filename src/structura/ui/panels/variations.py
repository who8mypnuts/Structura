"""Variation Explorer (docs/14 §5.3): a grid of seed variations with thumbnails; click one to adopt it.

Each cell is one compute-lane Job: build with that seed, then a small 'preview' render on the CPU
backend. Cells arrive as they finish; a new exploration cancels the old one (latest-wins keys)."""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from PySide6.QtCore import QSize, Qt, Signal, Slot
from PySide6.QtGui import QIcon, QImage, QPixmap, QResizeEvent
from PySide6.QtWidgets import QGridLayout, QPushButton, QSizePolicy, QToolButton, QVBoxLayout, QWidget

from ...compute.cpu import CpuBackend
from ...core.build.api import build_scene
from ...core.lang.compile.program import RuleProgram
from ...render.api import render
from ...render.output import to_display
from ...render.settings import RenderSettings
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


def variation_job(program: RuleProgram, cell: int, seed: int) -> Callable[[JobContext], Variation]:
    def run(ctx: JobContext) -> Variation:
        scene = build_scene(program, seed).scene
        ctx.check_cancelled()
        settings = RenderSettings(width=THUMB.width(), height=THUMB.height(), samples=2, samples_per_pass=2,
                                  integrator="preview", frame=True)  # fmt: skip
        image = render(scene, settings, CpuBackend()).image if len(scene) else np.zeros((1, 1, 3), np.float32)
        return Variation(cell, seed, to_display(image, 0.0, "soft"), len(scene))

    return run


class VariationExplorer(QWidget):
    adopt = Signal(int)  # seed

    def __init__(self, runner: JobRunner, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.runner = runner
        self.reroll = QPushButton(tr("New variations"))
        self.cells: list[QToolButton] = []
        grid = QGridLayout()
        for i in range(GRID * GRID):
            button = QToolButton()
            button.setIconSize(THUMB)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            button.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)  # long labels elide
            button.clicked.connect(lambda _c=False, i=i: self._adopt(i))
            button.setAccessibleName(tr("Variation {n}").format(n=i + 1))
            grid.addWidget(button, i // GRID, i % GRID)
            self.cells.append(button)
        self.grid = grid
        layout = self.column = QVBoxLayout(self)
        layout.addWidget(self.reroll)
        layout.addLayout(grid)
        layout.addStretch(1)
        self.seeds = [0] * (GRID * GRID)
        self.program: RuleProgram | None = None
        self.reroll.clicked.connect(lambda: self.explore(self.program) if self.program else None)

    def explore(self, program: RuleProgram | None, seeds: list[int] | None = None) -> None:
        if program is None:
            return
        self.program = program
        self.seeds = seeds or [random.randint(0, 32767) for _ in self.cells]
        for cell, (button, seed) in enumerate(zip(self.cells, self.seeds, strict=True)):
            button.setIcon(QIcon())
            button.setText(f"seed {seed} …")
            job = FunctionJob(
                f"variation {cell}", Lane.COMPUTE, variation_job(program, cell, seed), key=f"variation:{cell}"
            )
            self.runner.submit(job).finished.connect(self._show)

    @Slot(object)
    def _show(self, result: object) -> None:
        if not isinstance(result, Variation) or self.seeds[result.cell] != result.seed:
            return  # a newer exploration replaced this cell
        rgb = np.ascontiguousarray(result.rgb)
        h, w, _ = rgb.shape
        image = QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()
        button = self.cells[result.cell]
        button.setIcon(QIcon(QPixmap.fromImage(image)))
        button.setText(f"seed {result.seed} · {result.objects:,}")
        button.setToolTip(f"Seed {result.seed}: {result.objects:,} objects. Click to use this seed.")

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
        self.adopt.emit(self.seeds[cell])
