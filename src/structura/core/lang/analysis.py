"""Editor-facing analysis of a script (docs/12 §5): diagnostics and symbols in *original* text positions.

One call runs the whole v1 front end. A successful analysis carries the compiled program, so a live build
can start without compiling again.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path

from ..errors import StructuraError, UnresolvedRuleError
from .ast import CallAction, Loop, Program, RuleDef
from .compile.program import RuleProgram, compile_rule_set
from .diagnostics import Diagnostic, ParseError, Severity
from .legacy.gui_params import apply_gui_parameters
from .legacy.parser import parse_legacy
from .legacy.preprocessor import GuiParameter, LegacyPreprocessor
from .position_map import PositionMap
from .resolve import build_rule_set
from .source import Span
from .v2.front import after_preprocessing, front


@dataclass(frozen=True)
class RuleSymbol:
    name: str
    span: Span  # the whole definition
    weight: float
    maxdepth: int | None


@dataclass(frozen=True)
class Analysis:
    version: int
    diagnostics: tuple[Diagnostic, ...]
    rules: tuple[RuleSymbol, ...] = ()
    references: Mapping[str, tuple[Span, ...]] = field(default_factory=dict)
    parameters: tuple[GuiParameter, ...] = ()
    program: RuleProgram | None = None
    positions: PositionMap | None = None
    digest: str = ""  # hash of the preprocessed source: equal digests build identical scenes

    @property
    def ok(self) -> bool:
        return self.program is not None and not any(d.severity == Severity.ERROR for d in self.diagnostics)

    def action_span(self, action: int) -> Span | None:
        """Original-text span of a compiled action (SceneIR.source provenance)."""
        if self.program is None or self.positions is None or not 0 <= action < len(self.program.action_spans):
            return None
        return self.positions.span(self.program.action_spans[action])


def _calls(actions: tuple[object, ...]) -> list[CallAction]:
    return [a for a in actions if isinstance(a, CallAction)]


def _symbols(program: Program, pm: PositionMap) -> tuple[tuple[RuleSymbol, ...], dict[str, tuple[Span, ...]]]:
    rules = tuple(RuleSymbol(r.name, pm.span(r.span) or r.span, r.weight, r.maxdepth) for r in program.rules)
    refs: dict[str, list[Span]] = {}
    bodies: list[tuple[object, ...]] = [program.top, *(r.body for r in program.rules)]
    for body in bodies:
        for call in _calls(body):
            span = pm.span(call.span) or call.span
            refs.setdefault(call.target.split("::")[0], []).append(span)
    for rule in program.rules:  # 'rule A maxdepth 3 > B' references B
        if rule.retirement:
            refs.setdefault(rule.retirement, []).append(pm.span(rule.span) or rule.span)
    return rules, {k: tuple(v) for k, v in refs.items()}


def _header(span: Span, text: str) -> Span:
    """The 'rule NAME …' part of a definition, up to its '{' (diagnostics should not underline the body)."""
    brace = text.find("{", span.start, span.end)
    return Span(span.start, brace if brace > span.start else span.end)


def _unused(rules: tuple[RuleSymbol, ...], refs: Mapping[str, tuple[Span, ...]], text: str) -> list[Diagnostic]:
    return [
        Diagnostic("W101", Severity.WARNING, f"rule '{r.name}' is never referenced", _header(r.span, text))
        for r in rules
        if r.name not in refs
    ]


def analyze(
    text: str,
    seed: int = 0,
    params: Mapping[str, float] | None = None,
    script_dir: Path | None = None,
    version: int = 0,
) -> Analysis:
    fr = front(text)
    pre = LegacyPreprocessor().process(fr.text, seed)
    source = apply_gui_parameters(pre.text, pre.parameters, params)
    pm = PositionMap(text, source)
    diagnostics = [
        *fr.diagnostics,
        *(Diagnostic(d.code, d.severity, d.message, pm.span(d.span)) for d in pre.diagnostics),
    ]
    try:
        source = after_preprocessing(source, fr)
        parsed = parse_legacy(source)
    except ParseError as exc:
        error = Diagnostic(exc.code, Severity.ERROR, exc.message, pm.span(exc.span))
        return Analysis(version, (*diagnostics, error), parameters=tuple(pre.parameters))
    rules, refs = _symbols(parsed, pm)
    diagnostics += _unused(rules, refs, text)
    try:
        program = replace(compile_rule_set(build_rule_set(parsed), script_dir), declarations=fr.declarations)
    except (ParseError, StructuraError) as exc:
        span = pm.span(getattr(exc, "span", None))
        if isinstance(exc, UnresolvedRuleError) and exc.name in refs:
            span = refs[exc.name][0]
        error = Diagnostic(getattr(exc, "code", "E009"), Severity.ERROR, exc.message, span)
        return Analysis(version, (*diagnostics, error), rules, refs, tuple(pre.parameters))
    digest = hashlib.sha1(source.encode("utf-8")).hexdigest()
    return Analysis(version, tuple(diagnostics), rules, refs, tuple(pre.parameters), program, pm, digest)


__all__ = ["Analysis", "Loop", "RuleDef", "RuleSymbol", "analyze"]
