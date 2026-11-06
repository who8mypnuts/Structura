"""The v2 front passes, run before the v1 preprocessor (docs/05 §9)."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...scene.declarations import SceneDeclarations
from ..diagnostics import Diagnostic
from ..source import detect_dialect
from .blocks import extract_blocks
from .expressions import params_to_defines, substitute_expressions


@dataclass(frozen=True)
class Front:
    text: str  # what the v1 preprocessor sees
    declarations: SceneDeclarations | None = None
    diagnostics: tuple[Diagnostic, ...] = field(default=())

    @property
    def v2(self) -> bool:
        return self.declarations is not None


def front(text: str) -> Front:
    """v1 scripts pass through unchanged; v2 scripts lose their blocks and gain #define sliders for #param."""
    if detect_dialect(text) != 2:
        return Front(text)
    extracted = extract_blocks(text)
    return Front(params_to_defines(extracted.text), extracted.declarations, tuple(extracted.diagnostics))


def timeline_names(frame: int = 0, fps: float = 24.0) -> dict[str, float]:
    """The animation variables of v2 expressions (docs/16 §2)."""
    return {"frame": float(frame), "time": frame / fps, "fps": float(fps)}


def after_preprocessing(source: str, fr: Front, names: dict[str, float] | None = None) -> str:
    """v2: evaluate '( expr )' once the defines and parameters have been substituted."""
    return substitute_expressions(source, names or timeline_names()) if fr.v2 else source
