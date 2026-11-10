"""The exporter protocol and registry (docs/15 §1). Exporters are leaves: they import only core."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..core.params import ParamSpec
from ..core.scene.ir import SceneIR
from .scene_model import ExportSceneModel

Progress = Callable[[float, str], None]


@dataclass(frozen=True)
class ExportReport:
    path: Path
    files: tuple[Path, ...] = ()
    counts: dict[str, int] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()


@dataclass
class ExportJob:
    scene: SceneIR
    model: ExportSceneModel
    options: dict[str, Any]
    progress: Progress = field(default=lambda _f, _t: None)
    cancelled: Callable[[], bool] = field(default=lambda: False)

    def check(self) -> None:
        if self.cancelled():
            raise InterruptedError("export cancelled")


class Exporter(ABC):
    """A file format Structura writes; registered instances are listed by EXPORTERS.

    Attributes:
        name: The format's id (`structura export --format NAME`, presets).
        title: The name the export dialog shows.
        extensions: File suffixes, the first being the default.
        params: The options of the export sheet and `--option KEY=VALUE`.
        preferred: Whether it is the default exporter for its extensions.
    """

    name: str = ""
    title: str = ""
    extensions: tuple[str, ...] = ()
    params: tuple[ParamSpec, ...] = ()
    preferred: bool = True  # (the 1.5 OBJ layout is opt-in)

    @abstractmethod
    def write(self, job: ExportJob, path: Path) -> ExportReport:
        """Writes a scene.

        Args:
            job: The scene, its export model, the options, and progress/cancellation callbacks.
            path: The file to write (exporters may write more files beside it).

        Returns:
            What was written: the files, counts and warnings.
        """


EXPORTERS: dict[str, Exporter] = {}


def register(exporter: Exporter) -> Exporter:
    EXPORTERS[exporter.name] = exporter
    return exporter


def exporter_for(path: Path) -> Exporter | None:
    suffix = path.suffix.lower()
    candidates = sorted((e for e in EXPORTERS.values() if suffix in e.extensions), key=lambda e: not e.preferred)
    return candidates[0] if candidates else None
