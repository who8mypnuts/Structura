"""Typed intermediate representation produced by the SKL front end and consumed by every emitter."""

from __future__ import annotations

from dataclasses import dataclass, field

from .types import SklType, Struct


@dataclass(frozen=True)
class Expr:
    type: SklType


@dataclass(frozen=True)
class Const(Expr):
    value: float | int | bool


@dataclass(frozen=True)
class Var(Expr):
    name: str


@dataclass(frozen=True)
class Unary(Expr):
    op: str  # "-", "not", "~"
    operand: Expr


@dataclass(frozen=True)
class Binary(Expr):
    op: str  # + - * / // % << >> & | ^ == != < <= > >= and or
    left: Expr
    right: Expr


@dataclass(frozen=True)
class Call(Expr):
    func: str
    args: tuple[Expr, ...]


@dataclass(frozen=True)
class Builtin(Expr):
    name: str
    args: tuple[Expr, ...]


@dataclass(frozen=True)
class Construct(Expr):
    """Vector or struct construction. A vector with a single scalar argument is a splat."""

    args: tuple[Expr, ...]


@dataclass(frozen=True)
class Cast(Expr):
    operand: Expr


@dataclass(frozen=True)
class Component(Expr):
    base: Expr
    index: int


@dataclass(frozen=True)
class FieldGet(Expr):
    base: Expr
    field: str


@dataclass(frozen=True)
class Index(Expr):
    base: Expr  # a Var of Buffer or LocalArray type
    index: Expr


@dataclass(frozen=True)
class Select(Expr):
    cond: Expr
    if_true: Expr
    if_false: Expr


@dataclass(frozen=True)
class Stmt:
    pass


@dataclass(frozen=True)
class Declare(Stmt):
    name: str
    type: SklType
    value: Expr | None  # None for local arrays


@dataclass(frozen=True)
class Assign(Stmt):
    name: str
    value: Expr


@dataclass(frozen=True)
class Store(Stmt):
    target: Var
    index: Expr
    value: Expr


@dataclass(frozen=True)
class If(Stmt):
    cond: Expr
    body: tuple[Stmt, ...]
    orelse: tuple[Stmt, ...]


@dataclass(frozen=True)
class For(Stmt):
    var: str
    var_type: SklType
    start: Expr
    stop: Expr
    step: Expr
    body: tuple[Stmt, ...]


@dataclass(frozen=True)
class While(Stmt):
    cond: Expr
    body: tuple[Stmt, ...]


@dataclass(frozen=True)
class Break(Stmt):
    pass


@dataclass(frozen=True)
class Continue(Stmt):
    pass


@dataclass(frozen=True)
class Return(Stmt):
    value: Expr | None


@dataclass(frozen=True)
class ExprStmt(Stmt):
    expr: Expr


@dataclass(frozen=True)
class Function:
    name: str
    params: tuple[tuple[str, SklType], ...]
    ret: SklType
    body: tuple[Stmt, ...]
    is_kernel: bool = False
    workgroup: tuple[int, int, int] = (8, 8, 1)
    exact: bool = False
    calls: frozenset[str] = frozenset()
    source: str = ""


@dataclass
class Module:
    """A closed set of functions (dependency order) plus the struct types they use."""

    functions: dict[str, Function] = field(default_factory=dict)
    structs: dict[str, Struct] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)
