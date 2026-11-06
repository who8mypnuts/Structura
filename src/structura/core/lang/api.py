"""Front-end API: EisenScript text → RuleProgram (docs/06 §1)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path

from .compile.program import RuleProgram, compile_rule_set
from .diagnostics import Diagnostic
from .legacy.gui_params import apply_gui_parameters
from .legacy.parser import parse_legacy
from .legacy.preprocessor import GuiParameter, LegacyPreprocessor
from .resolve import build_rule_set
from .v2.front import after_preprocessing, front, timeline_names


@dataclass(frozen=True)
class CompiledScript:
    program: RuleProgram
    parameters: tuple[GuiParameter, ...]
    diagnostics: tuple[Diagnostic, ...]
    preprocessed: str


def compile_script(
    text: str,
    seed: int = 0,
    params: Mapping[str, float] | None = None,
    script_dir: Path | None = None,
    frame: int = 0,
    fps: float = 24.0,
) -> CompiledScript:
    """Preprocess, parse (v1, strict), resolve and compile. Raises ParseError / BuildError.

    ``frame`` and ``fps`` bind the v2 animation variables 'frame', 'time' and 'fps'.
    """
    fr = front(text)
    pre = LegacyPreprocessor().process(fr.text, seed)
    names = timeline_names(frame, fps)
    source = after_preprocessing(apply_gui_parameters(pre.text, pre.parameters, params), fr, names)
    program = compile_rule_set(build_rule_set(parse_legacy(source)), script_dir)
    program = replace(program, declarations=fr.declarations)
    return CompiledScript(program, tuple(pre.parameters), (*fr.diagnostics, *pre.diagnostics), source)
