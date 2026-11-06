"""Build Stats panel: counts by primitive kind and the builder's termination reasons (docs/14 §3)."""

from __future__ import annotations

import numpy as np
from PySide6.QtWidgets import QFormLayout, QLabel, QWidget

from ...core.scene.ir import PrimitiveKind
from ...services.build import BuildOutcome


class BuildStatsPanel(QWidget):
    FIELDS = ("Objects", "By kind", "Generations", "Rule applications", "Culled (max/min size)", "Time", "Seed")

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QFormLayout(self)
        self.labels = {name: QLabel("—") for name in self.FIELDS}
        for name, label in self.labels.items():
            label.setWordWrap(True)
            layout.addRow(name, label)

    def show_outcome(self, outcome: BuildOutcome) -> None:
        stats, scene = outcome.stats, outcome.scene
        kinds, counts = np.unique(scene.kind, return_counts=True)
        by_kind = ", ".join(
            f"{PrimitiveKind(int(k)).name.lower()} {int(c):,}" for k, c in zip(kinds, counts, strict=True)
        )
        capped = " (maxobjects reached)" if stats.objects >= stats.max_objects else ""
        values = {
            "Objects": f"{stats.objects:,}{capped}",
            "By kind": by_kind or "—",
            "Generations": f"{stats.generations:,} (max {stats.max_generations:,})",
            "Rule applications": f"{stats.applications:,}",
            "Culled (max/min size)": f"{stats.max_size_culled:,} / {stats.min_size_culled:,}",
            "Time": f"{stats.seconds * 1000:.0f} ms",
            "Seed": str(outcome.seed),
        }
        for name, text in values.items():
            self.labels[name].setText(text)
