"""Strict EisenScript v1 parser (grammar: docs/05-eisenscript-language.md §3).

Accepts and rejects exactly what Structure Synth 1.5 does, with two documented, output-neutral extensions
inside transformation lists (docs/01 D2/D3): 'size' means 's' and 'v' means 'brightness'.
"""

from __future__ import annotations

from ...color import parse_color
from ..ast import Action, CallAction, Loop, Program, RuleDef, SetAction, TransformOp
from ..catalog import operators
from ..diagnostics import ParseError
from ..source import Span
from .tokenizer import Kind, Token, tokenize

_OPS = {spec.name: spec for spec in operators()}
_PARSER_ALIASES = {"v": "brightness", "size": "s"}
_V2_OPS = {name for name, spec in _OPS.items() if spec.v2}
_ACTION_START = (Kind.LBRACE, Kind.USER, Kind.NUMBER)


class LegacyParser:
    def __init__(self, tokens: list[Token], v2: bool = False) -> None:
        self.tokens = tokens
        self.pos = 0
        self.depth_first = False
        self.v2 = v2  # '#version 2': also the v2 operators ('mat'), which v1 tokenizes as rule names

    # -- token helpers ------------------------------------------------------------------------------------
    @property
    def tok(self) -> Token:
        return self.tokens[self.pos]

    def advance(self) -> Token:
        token = self.tokens[self.pos]
        self.pos = min(self.pos + 1, len(self.tokens) - 1)
        return token

    def expect(self, kind: Kind, message: str) -> Token:
        if self.tok.kind is not kind:
            raise ParseError(f"{message} Found: {self.tok.text}", self.tok.span)
        return self.advance()

    def expect_number(self, message: str, integer: bool = False, code: str = "E001") -> float:
        token = self.tok
        if token.kind is not Kind.NUMBER or (integer and not token.is_integer):
            raise ParseError(f"{message} Found: {token.text}", token.span, code)
        self.advance()
        return token.value

    # -- grammar ------------------------------------------------------------------------------------------
    def program(self) -> Program:
        top: list[Action] = []
        rules: list[RuleDef] = []
        while self.tok.kind in (Kind.RULE, Kind.SET, *_ACTION_START):
            if self.tok.kind is Kind.RULE:
                rules.append(self.rule())
            else:
                top.append(self.statement())
        self.expect(Kind.END, "Unexpected symbol found. At this scope only RULE and SET statements are allowed.")
        return Program(tuple(top), tuple(rules), self.depth_first)

    def statement(self) -> Action:
        return self.set_action() if self.tok.kind is Kind.SET else self.action()

    def rule(self) -> RuleDef:
        start = self.advance().span.start
        name = self.expect(Kind.USER, "After rule identifier a rule name is expected.").text
        weight, maxdepth, retire = 1.0, None, None
        while self.tok.kind is Kind.OPERATOR:
            weight, maxdepth, retire = self.modifier(weight, maxdepth, retire)
        self.expect(Kind.LBRACE, "After rule name a left bracket is expected.")
        body: list[Action] = []
        while self.tok.kind in (Kind.SET, *_ACTION_START):
            body.append(self.statement())
        end = self.expect(Kind.RBRACE, "A rule definition must end with a right bracket.").span.end
        return RuleDef(name, tuple(body), Span(start, end), weight, maxdepth, retire)

    def modifier(self, weight: float, maxdepth: int | None, retire: str | None) -> tuple[float, int | None, str | None]:
        name = self.advance().text
        if name == "weight":
            return self.expect_number("Rule modifier 'weight' expected numerical argument."), maxdepth, retire
        if name == "maxdepth":
            depth = int(self.expect_number("Rule modifier 'maxdepth' expected integer argument.", True, "E008"))
            if self.tok.kind is Kind.GT:
                self.advance()
                retire = self.expect(Kind.USER, "After maxdepth retirement operator a rule name is expected.").text
            return weight, depth, retire
        raise ParseError(f"In rule modifier list: expected maxdepth or weight. Found: {name}", self.tok.span)

    def set_action(self) -> SetAction:
        start = self.advance().span.start
        key_token = self.tok
        if key_token.kind is Kind.OPERATOR and key_token.text == "maxdepth":
            self.advance()
        else:
            self.expect(Kind.USER, "Expected a valid setting name.")
        value_token = self.advance()  # any symbol is accepted as the value
        if key_token.text == "recursion" and value_token.text == "depth":
            self.depth_first = True
        return SetAction(key_token.text, value_token.text, Span(start, value_token.span.end))

    def action(self) -> CallAction:
        start = self.tok.span.start
        if self.tok.kind is Kind.USER:
            target = self.advance()
            return CallAction((), target.text, Span(start, target.span.end))
        loops: list[Loop] = []
        if self.tok.kind is Kind.LBRACE:
            loops.append(self.transform_list(1, start))
        else:
            while self.tok.kind is Kind.NUMBER:
                loops.append(self.counted_loop())
        target = self.expect(Kind.USER, "Expected a rule name after the transformation list.")
        return CallAction(tuple(loops), target.text, Span(start, target.span.end))

    def counted_loop(self) -> Loop:
        start = self.tok.span.start
        count = int(self.expect_number("Expected an integer count in the transformation loop.", True, "E007"))
        self.expect(Kind.STAR, "Expected a '*' after the transformation count.")
        return self.transform_list(count, start)

    def transform_list(self, count: int, start: int) -> Loop:
        self.expect(Kind.LBRACE, "Transformation List: Expected a left bracket.")
        ops: list[TransformOp] = []
        while self.tok.kind is Kind.OPERATOR or (self.tok.kind is Kind.USER and self._user_operator(self.tok.text)):
            ops.append(self.transform())
        end = self.expect(Kind.RBRACE, "Transformation List: Expected a right bracket or an operator.").span.end
        return Loop(count, tuple(ops), Span(start, end))

    def _user_operator(self, word: str) -> bool:
        return word in _PARSER_ALIASES or (self.v2 and word in _V2_OPS)

    def transform(self) -> TransformOp:
        token = self.advance()
        name = _PARSER_ALIASES.get(token.text, token.text)
        spec = _OPS.get(name)
        if spec is None:
            raise ParseError(f"Unknown transformation type: {token.text}", token.span)
        args = self.transform_args(name, spec.args, spec.arity)
        return TransformOp(name, args, Span(token.span.start, self.tokens[self.pos - 1].span.end))

    def transform_args(self, name: str, kinds: tuple[str, ...], arity: tuple[int, ...]) -> tuple[float | str, ...]:
        args: list[float | str] = []
        for index, kind in enumerate(kinds):
            if index in arity and self.tok.kind is not Kind.NUMBER and kind != "color":
                break  # optional trailing arguments ('s x' vs 's x y z')
            if kind == "material":
                args.append(self.expect(Kind.USER, f"Transformation '{name}': expected a material name.").text)
                continue
            args.append(
                self.color_arg(name)
                if kind.startswith("color")
                else self.expect_number(f"Transformation '{name}': expected numerical parameter.", code="E006")
            )
        return tuple(args)

    def color_arg(self, name: str) -> str:
        token = self.advance()
        if not (token.text == "random" and name == "color") and parse_color(token.text) is None:
            raise ParseError(
                f"Transformation '{name}': Expected a valid color. Found: {token.text}", token.span, "E005"
            )
        return token.text


def parse_legacy(text: str, v2: bool = False) -> Program:
    """Tokenize and parse preprocessed text (v1 grammar, plus the v2 operators when ``v2``). Raises ParseError
    on the first error (1.5 behaviour)."""
    return LegacyParser(tokenize(text), v2).program()


MAX_ERRORS = 50


class RecoveringParser(LegacyParser):
    """The editor's parser (docs/12 §2.2): after an error it notes it and resumes at the next 'rule', so the
    Problems panel lists every broken rule at once and the rules that do parse stay known (outline,
    completion, go to definition). The first error is always the one the strict parser reports. Only
    analysis uses it; builds still go through the strict parser (1.5 behaviour)."""

    def __init__(self, tokens: list[Token], v2: bool = False) -> None:
        super().__init__(tokens, v2)
        self.errors: list[ParseError] = []

    def program(self) -> Program:
        top: list[Action] = []
        rules: list[RuleDef] = []
        while self.tok.kind is not Kind.END and len(self.errors) < MAX_ERRORS:
            start = self.pos
            try:
                if self.tok.kind is Kind.RULE:
                    rules.append(self.rule())
                elif self.tok.kind in (Kind.SET, *_ACTION_START):
                    top.append(self.statement())
                else:
                    self.expect(Kind.END, "Unexpected symbol found. At this scope only RULE and SET statements are "
                                          "allowed.")  # fmt: skip
            except ParseError as exc:
                self.errors.append(exc)
                self._resume(start)
        return Program(tuple(top), tuple(rules), self.depth_first)

    def _resume(self, start: int) -> None:
        """Skip to the next 'rule' keyword (rules never nest, so it always starts a top-level rule)."""
        self.pos = start
        self.advance()
        while self.tok.kind not in (Kind.RULE, Kind.END):
            self.advance()


def parse_recovering(text: str, v2: bool = False) -> tuple[Program, list[ParseError]]:
    """Parses as much as possible, collecting every syntax error (up to MAX_ERRORS).

    Args:
        text: The script after preprocessing.
        v2: Whether it is an EisenScript v2 script.

    Returns:
        (the program made of what parsed, the errors). A symbol the tokenizer rejects ('85mm' in a v1 script)
        is the one error: nothing can be parsed around it.
    """
    try:
        tokens = tokenize(text)
    except ParseError as exc:
        return Program((), (), False), [exc]
    parser = RecoveringParser(tokens, v2)
    return parser.program(), parser.errors
