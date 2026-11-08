"""Build Stats panel (docs/14 §3): counts by primitive kind, why the build stopped (1.5's termination
reasons), timings, and a histogram of objects per generation."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter, QPaintEvent
from PySide6.QtWidgets import QFormLayout, QHBoxLayout, QLabel, QWidget

from ...core.build.driver import BuildStats
from ...services.build import BuildOutcome
from ..i18n import tr

MAX_BARS = 120


def termination(stats: BuildStats) -> str:
    """Why the build stopped, in Structure Synth's terms."""
    reasons = []
    if stats.objects >= stats.max_objects:
        reasons.append(tr("the object limit ('set maxobjects') was reached"))
    if stats.generations >= stats.max_generations:
        reasons.append(tr("the generation limit ('set maxdepth') was reached"))
    if stats.max_size_culled or stats.min_size_culled:
        reasons.append(tr("branches were culled by 'set maxsize' / 'set minsize'"))
    return "; ".join(reasons) or tr("every rule terminated on its own")


def generation_histogram(generation: np.ndarray, bars: int = MAX_BARS) -> np.ndarray:
    """Objects per generation, merged into at most ``bars`` bins."""
    counts = np.bincount(generation) if generation.size else np.zeros(1, np.int64)
    if counts.size <= bars:
        return counts
    edges = np.linspace(0, counts.size, bars + 1).astype(np.int64)
    return np.add.reduceat(counts, edges[:-1])


class GenerationChart(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.counts = np.zeros(0, np.int64)
        self.setMinimumHeight(60)
        self.setToolTip(tr("Objects per generation (left: the first generation)"))

    def set_counts(self, counts: np.ndarray) -> None:
        self.counts = counts
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        if not self.counts.size or self.counts.max() <= 0:
            return
        painter = QPainter(self)
        colour = self.palette().highlight().color()
        width = self.width() / len(self.counts)
        top = float(self.counts.max())
        for i, count in enumerate(self.counts):
            height = (self.height() - 2) * float(count) / top
            painter.fillRect(QRectF(i * width, self.height() - height, max(1.0, width - 1), height), colour)
        painter.end()


class BuildStatsPanel(QWidget):
    FIELDS = ("Objects", "By kind", "Generations", "Stopped because", "Rule applications", "Culled (max/min size)",
              "Time", "Phases", "Seed")  # fmt: skip

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        form = QFormLayout()
        self.labels = {name: QLabel("—") for name in self.FIELDS}
        for name, label in self.labels.items():
            label.setWordWrap(True)
            form.addRow(name, label)
        self.chart = GenerationChart()
        layout = QHBoxLayout(self)
        layout.addLayout(form, 3)
        layout.addWidget(self.chart, 2, Qt.AlignmentFlag.AlignBottom)

    def show_phases(self, analysis: float, build: float, preview: float) -> None:
        """Per-phase timings: analysing (and compiling), building, preparing the viewport scene."""
        text = f"analysis {analysis * 1000:.0f} ms · build {build * 1000:.0f} ms · viewport {preview * 1000:.0f} ms"
        self.labels["Phases"].setText(text)

    def show_outcome(self, outcome: BuildOutcome) -> None:
        stats, scene = outcome.stats, outcome.scene
        by_kind = ", ".join(f"{kind} {count:,}" for kind, count in scene.kind_counts().items())
        rate = stats.objects / stats.seconds if stats.seconds > 0 else 0.0
        values = {
            "Objects": f"{stats.objects:,}",
            "By kind": by_kind or "—",
            "Generations": f"{stats.generations:,} (max {stats.max_generations:,})",
            "Stopped because": termination(stats),
            "Rule applications": f"{stats.applications:,}",
            "Culled (max/min size)": f"{stats.max_size_culled:,} / {stats.min_size_culled:,}",
            "Time": f"{stats.seconds * 1000:.0f} ms ({rate:,.0f} objects/s)",
            "Seed": str(outcome.seed),
        }
        for name, text in values.items():
            self.labels[name].setText(text)
        self.chart.set_counts(generation_histogram(np.asarray(scene.generation)))
