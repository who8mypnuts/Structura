"""Refactorings (docs/12 §2.2, P2): extract a call's transforms into a new rule, inline a rule, and convert
'{…} R' ↔ '1 * {…} R'. Qt-free; each is a QuickFix (a titled list of edits in original positions), so the
editor offers them in the Ctrl+. menu next to the quick fixes.

They parse the script like the analysis does and map spans back to the edited text. An action is only
rewritten when its mapped text equals the parsed text (no #define substitution on it), so a refactoring never
guesses around a substitution.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .ast import CallAction, Loop, Program, RuleDef, SetAction
from .diagnostics import ParseError
from .fixes import QuickFix, TextEdit
from .legacy.parser import parse_recovering
from .legacy.preprocessor import LegacyPreprocessor
from .position_map import PositionMap
from .source import Span
from .v2.front import after_preprocessing, front

PRIMITIVES = {"box", "sphere", "cylinder", "line", "dot", "grid", "mesh", "triangle", "template"}


@dataclass(frozen=True)
class Parsed:
    text: str  # the edited text
    source: str  # what was parsed
    program: Program
    positions: PositionMap

    def original(self, span: Span) -> Span | None:
        """``span`` in the edited text, when it maps exactly (no substitution changed it)."""
        mapped = self.positions.span(span)
        if mapped is None or self.text[mapped.start : mapped.end] != self.source[span.start : span.end]:
            return None
        return mapped

    def slice(self, span: Span) -> str:
        return self.source[span.start : span.end]

    def definitions(self, name: str) -> list[RuleDef]:
        return [r for r in self.program.rules if r.name.lower() == name.lower()]


def parse(text: str) -> Parsed | None:
    try:
        fr = front(text)
        source = after_preprocessing(LegacyPreprocessor(fr.v2).process(fr.text, 0).text, fr)
    except ParseError:
        return None
    program, _ = parse_recovering(source, fr.v2)
    return Parsed(text, source, program, PositionMap(text, source))


def _calls(parsed: Parsed) -> list[tuple[CallAction, RuleDef | None]]:
    """Every call with the rule it is in (None: top level)."""
    out: list[tuple[CallAction, RuleDef | None]] = [(a, None) for a in parsed.program.top if isinstance(a, CallAction)]
    for rule in parsed.program.rules:
        out += [(a, rule) for a in rule.body if isinstance(a, CallAction)]
    return out


def _call_at(parsed: Parsed, position: int) -> tuple[CallAction, RuleDef | None, Span] | None:
    for call, rule in _calls(parsed):
        span = parsed.original(call.span)
        if span is not None and span.start <= position <= span.end:
            return call, rule, span
    return None


def counted(parsed: Parsed, loop: Loop) -> str:
    """A loop as 'N * { … }' (the form that composes: counted loops may follow each other)."""
    text = parsed.slice(loop.span)
    return f"{loop.count} * {text[text.index('{') :]}"


def _fresh_name(parsed: Parsed, base: str) -> str:
    taken = {r.name.lower() for r in parsed.program.rules} | PRIMITIVES
    name, n = base, 1
    while name.lower() in taken:
        n += 1
        name = f"{base}{n}"
    return name


def extract_rule(parsed: Parsed, call: CallAction, rule: RuleDef | None, span: Span) -> QuickFix | None:
    """'3 * { x 1 } box' → 'newRule' plus 'rule newRule { 3 * { x 1 } box }' after the enclosing rule."""
    if not call.loops:
        return None
    name = _fresh_name(parsed, "newRule")
    anchor = parsed.original(rule.span) if rule is not None else None
    at = anchor.end if anchor is not None else len(parsed.text)
    body = parsed.text[span.start : span.end]
    gap = "\n" if anchor is None and parsed.text.endswith("\n") else "\n\n"
    block = f"{gap}rule {name} {{\n  {body}\n}}" + ("" if anchor is not None else "\n")
    edits = (TextEdit(span.start, span.end, name), TextEdit(at, at, block))
    return QuickFix(f"Extract the transforms into a new rule '{name}'", edits)


def toggle_count(parsed: Parsed, call: CallAction, span: Span) -> QuickFix | None:
    """'{…} R' → '1 * {…} R', and a lone '1 * {…} R' back to '{…} R'."""
    if len(call.loops) != 1 or call.loops[0].count != 1:
        return None
    loop = parsed.original(call.loops[0].span)
    if loop is None:
        return None
    text = parsed.text[loop.start : loop.end]
    brace = text.index("{")
    if brace == 0:
        return QuickFix("Convert to '1 * { … }'", (TextEdit(loop.start, loop.start, "1 * "),))
    return QuickFix("Convert to '{ … }' (drop '1 *')", (TextEdit(loop.start, loop.start + brace, ""),))


def _inlinable(parsed: Parsed, name: str) -> RuleDef | None:
    """The single, plain definition of ``name`` (no weight, maxdepth, set lines or recursion)."""
    found = parsed.definitions(name)
    if len(found) != 1:
        return None
    rule = found[0]
    plain = rule.weight == 1.0 and rule.maxdepth is None and rule.body
    if not plain or any(isinstance(a, SetAction) for a in rule.body):
        return None
    if any(isinstance(a, CallAction) and a.target.lower() == name.lower() for a in rule.body):
        return None
    return rule


def _target(parsed: Parsed, action: CallAction) -> str:
    """The call's rule name as written (the parser lowercases names)."""
    return parsed.source[action.span.end - len(action.target) : action.span.end]


def _joined(parsed: Parsed, outer: tuple[Loop, ...], action: CallAction) -> str:
    """``action`` with the caller's loops in front: one loop stays as written, several become counted."""
    loops = [*outer, *action.loops]
    if not loops:
        return _target(parsed, action)
    if len(loops) == 1:
        return f"{parsed.slice(loops[0].span)} {_target(parsed, action)}"
    return " ".join([*(counted(parsed, loop) for loop in loops), _target(parsed, action)])


def _inlined(parsed: Parsed, call: CallAction, rule: RuleDef) -> str:
    if not call.loops:
        return " ".join(parsed.slice(a.span) for a in rule.body)
    return " ".join(_joined(parsed, call.loops, a) for a in rule.body if isinstance(a, CallAction))


def inline_call(parsed: Parsed, call: CallAction, span: Span) -> QuickFix | None:
    rule = _inlinable(parsed, call.target)
    if rule is None:
        return None
    title = f"Inline '{_target(parsed, call)}' here"
    return QuickFix(title, (TextEdit(span.start, span.end, _inlined(parsed, call, rule)),))


def inline_everywhere(parsed: Parsed, name: str) -> QuickFix | None:
    """Inline every call of ``name`` and delete its definition."""
    rule = _inlinable(parsed, name)
    definition = parsed.original(rule.span) if rule is not None else None
    if rule is None or definition is None:
        return None
    edits = []
    for call, owner in _calls(parsed):
        span = parsed.original(call.span)
        if call.target.lower() == name.lower() and owner is not rule:
            if span is None:
                return None
            edits.append(TextEdit(span.start, span.end, _inlined(parsed, call, rule)))
    trailing = re.match(r"[ \t]*\n?", parsed.text[definition.end :])
    end = definition.end + (len(trailing.group(0)) if trailing else 0)
    edits.append(TextEdit(definition.start, end, ""))
    return QuickFix(f"Inline rule '{parsed.text[definition.start:definition.end].split()[1]}' everywhere and remove it",
                    tuple(edits))  # fmt: skip


def _rule_name_at(parsed: Parsed, position: int) -> str | None:
    for rule in parsed.program.rules:
        span = parsed.original(rule.span)
        if span is not None and span.start <= position <= span.start + len("rule ") + len(rule.name) + 1:
            return rule.name
    return None


def refactorings_at(text: str, position: int) -> list[QuickFix]:
    """The refactorings that apply at ``position`` (a call, or a rule definition's header)."""
    parsed = parse(text)
    if parsed is None:
        return []
    found: list[QuickFix | None] = []
    at = _call_at(parsed, position)
    if at is not None:
        call, rule, span = at
        found += [extract_rule(parsed, call, rule, span), toggle_count(parsed, call, span),
                  inline_call(parsed, call, span)]  # fmt: skip
    name = _rule_name_at(parsed, position)
    if name is not None:
        found.append(inline_everywhere(parsed, name))
    return [f for f in found if f is not None]


def rule_alone(text: str, name: str) -> str | None:
    """The script with its top-level calls replaced by one call of ``name`` (the rule built on its own, for
    hover previews); top-level 'set' lines, definitions and v2 blocks stay. None when it cannot be cut."""
    parsed = parse(text)
    if parsed is None or not parsed.definitions(name):
        return None
    spans = [parsed.original(a.span) for a in parsed.program.top if isinstance(a, CallAction)]
    if any(span is None for span in spans):
        return None
    out = text
    for span in sorted((s for s in spans if s is not None), key=lambda s: s.start, reverse=True):
        out = out[: span.start] + out[span.end :]
    return out.rstrip() + f"\n{name}\n"
