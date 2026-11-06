"""Expression typing: Python AST → typed SKL IR (docs/11 §3.2–3.3).

Integer literals are 'soft': they take the integer type of the other operand (i32 by default) and are
accepted where f32 is expected. Float literals are f32. Any other mixing needs an explicit cast.
"""

from __future__ import annotations

import ast
from collections.abc import Callable
from typing import Any

from .. import ir
from ..builtins import BUILTINS, BuiltinTypeError
from ..types import (
    BOOL,
    COMPONENTS,
    F32,
    I32,
    NAMED,
    U32,
    Buffer,
    LocalArray,
    Scalar,
    SklType,
    Struct,
    Vector,
    elem_of,
    is_numeric,
)
from .errors import SklError

ARITH = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.FloorDiv: "//", ast.Mod: "%"}
BITS = {ast.LShift: "<<", ast.RShift: ">>", ast.BitAnd: "&", ast.BitOr: "|", ast.BitXor: "^"}
COMPARE = {ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">="}
SOFT_INT = Scalar("i32")  # marker object identity is not used; softness is tracked on Const nodes


def _soft(e: ir.Expr) -> bool:
    return isinstance(e, ir.Const) and isinstance(e.value, int) and not isinstance(e.value, bool)


def _retype(e: ir.Expr, t: SklType) -> ir.Expr:
    """Give a soft integer literal a concrete type (f32 literals keep their numeric value)."""
    if _soft(e) and isinstance(t, Scalar) and is_numeric(t):
        return ir.Const(t, float(e.value) if t == F32 else e.value)  # type: ignore[attr-defined]
    return e


class ExprBuilder:
    def __init__(
        self,
        scope: dict[str, SklType],
        signatures: dict[str, tuple[list[SklType], SklType]],
        structs: dict[str, Struct],
        globals_: dict[str, Any],
        where: str,
    ) -> None:
        self.scope, self.signatures, self.structs = scope, signatures, structs
        self.globals, self.where = globals_, where
        self.calls: set[str] = set()

    def fail(self, message: str, node: ast.AST) -> SklError:
        return SklError(message, node, self.where)

    # ------------------------------------------------------------------------------------------------
    def build(self, node: ast.expr) -> ir.Expr:
        handlers: dict[type, Callable[[Any], ir.Expr]] = {
            ast.Constant: self._constant,
            ast.Name: self._name,
            ast.BinOp: self._binop,
            ast.UnaryOp: self._unary,
            ast.Compare: self._compare,
            ast.BoolOp: self._boolop,
            ast.Call: self._call,
            ast.Attribute: self._attribute,
            ast.Subscript: self._subscript,
            ast.IfExp: self._ifexp,
        }
        handler = handlers.get(type(node))
        if handler is None:
            raise self.fail(f"unsupported expression: {ast.unparse(node)}", node)
        return handler(node)

    def expect(self, node: ast.expr, t: SklType) -> ir.Expr:
        e = _retype(self.build(node), t)
        if e.type != t:
            raise self.fail(f"expected {t}, got {e.type}: {ast.unparse(node)}", node)
        return e

    def _constant(self, node: ast.Constant) -> ir.Expr:
        v = node.value
        if isinstance(v, bool):
            return ir.Const(BOOL, v)
        if isinstance(v, int):
            return ir.Const(I32, v)
        if isinstance(v, float):
            return ir.Const(F32, v)
        raise self.fail(f"unsupported constant {v!r}", node)

    def _name(self, node: ast.Name) -> ir.Expr:
        if node.id in self.scope:
            return ir.Var(self.scope[node.id], node.id)
        value = self.globals.get(node.id)
        if isinstance(value, bool | int | float):
            return self._constant(ast.Constant(value))
        raise self.fail(f"unknown name '{node.id}'", node)

    def _binop(self, node: ast.BinOp) -> ir.Expr:
        left, right = self.build(node.left), self.build(node.right)
        if type(node.op) in BITS:
            return self._int_op(BITS[type(node.op)], left, right, node)
        if type(node.op) not in ARITH:
            raise self.fail("unsupported operator", node)
        return self._arith(ARITH[type(node.op)], left, right, node)

    def _unify(self, left: ir.Expr, right: ir.Expr) -> tuple[ir.Expr, ir.Expr]:
        if _soft(left) and not _soft(right):
            left = _retype(left, elem_of(right.type) or right.type)
        elif _soft(right) and not _soft(left):
            right = _retype(right, elem_of(left.type) or left.type)
        return left, right

    def _arith(self, op: str, left: ir.Expr, right: ir.Expr, node: ast.AST) -> ir.Expr:
        left, right = self._unify(left, right)
        lt, rt = left.type, right.type
        if not (is_numeric(lt) and is_numeric(rt)) or elem_of(lt) != elem_of(rt):
            raise self.fail(f"operands of '{op}' must share a numeric type, got {lt} and {rt}", node)
        result = lt if isinstance(lt, Vector) else rt
        if isinstance(lt, Vector) and isinstance(rt, Vector) and lt != rt:
            raise self.fail(f"vector sizes differ: {lt} {op} {rt}", node)
        elem = elem_of(result)
        if op == "/" and elem != F32:
            raise self.fail("use '//' for integer division", node)
        if op in ("//", "%") and (elem == F32 or isinstance(result, Vector)):
            raise self.fail(f"'{op}' is for scalar integers only (use fmod for floats)", node)
        return ir.Binary(result, op, left, right)

    def _int_op(self, op: str, left: ir.Expr, right: ir.Expr, node: ast.AST) -> ir.Expr:
        left, right = self._unify(left, right)
        if left.type != right.type or left.type not in (I32, U32):
            raise self.fail(f"'{op}' needs matching integer operands, got {left.type} and {right.type}", node)
        return ir.Binary(left.type, op, left, right)

    def _unary(self, node: ast.UnaryOp) -> ir.Expr:
        operand = self.build(node.operand)
        if isinstance(node.op, ast.Not):
            if operand.type != BOOL:
                raise self.fail("'not' needs a bool", node)
            return ir.Unary(BOOL, "not", operand)
        if isinstance(node.op, ast.USub) and is_numeric(operand.type):
            if isinstance(operand, ir.Const) and (_soft(operand) or operand.type == F32):
                return ir.Const(operand.type, -operand.value)
            return ir.Unary(operand.type, "-", operand)
        if isinstance(node.op, ast.Invert) and operand.type in (I32, U32):
            return ir.Unary(operand.type, "~", operand)
        raise self.fail("unsupported unary operator", node)

    def _compare(self, node: ast.Compare) -> ir.Expr:
        if len(node.ops) != 1:
            raise self.fail("chained comparisons are not supported", node)
        left, right = self._unify(self.build(node.left), self.build(node.comparators[0]))
        if left.type != right.type or not isinstance(left.type, Scalar):
            raise self.fail(f"cannot compare {left.type} with {right.type}", node)
        return ir.Binary(BOOL, COMPARE[type(node.ops[0])], left, right)

    def _boolop(self, node: ast.BoolOp) -> ir.Expr:
        op = "and" if isinstance(node.op, ast.And) else "or"
        values = [self.expect(v, BOOL) for v in node.values]
        result = values[0]
        for value in values[1:]:
            result = ir.Binary(BOOL, op, result, value)
        return result

    def _ifexp(self, node: ast.IfExp) -> ir.Expr:
        cond = self.expect(node.test, BOOL)
        a, b = self._unify(self.build(node.body), self.build(node.orelse))
        if a.type != b.type:
            raise self.fail(f"conditional branches differ: {a.type} vs {b.type}", node)
        return ir.Select(a.type, cond, a, b)

    def _attribute(self, node: ast.Attribute) -> ir.Expr:
        base = self.build(node.value)
        if isinstance(base.type, Vector) and len(node.attr) == 1 and node.attr in COMPONENTS[: base.type.size]:
            return ir.Component(base.type.elem, base, COMPONENTS.index(node.attr))
        if isinstance(base.type, Struct) and base.type.field_type(node.attr) is not None:
            return ir.FieldGet(base.type.field_type(node.attr), base, node.attr)  # type: ignore[arg-type]
        raise self.fail(f"{base.type} has no member '{node.attr}'", node)

    def _subscript(self, node: ast.Subscript) -> ir.Expr:
        base = self.build(node.value)
        if not isinstance(base, ir.Var) or not isinstance(base.type, Buffer | LocalArray):
            raise self.fail("only buffers and local arrays can be indexed", node)
        index = self.build(node.slice)
        index = _retype(index, U32 if index.type not in (I32, U32) else index.type)
        if index.type not in (I32, U32):
            raise self.fail("indices must be i32 or u32", node)
        return ir.Index(base.type.elem, base, index)

    # ------------------------------------------------------------------------------------------------
    def _call(self, node: ast.Call) -> ir.Expr:
        if not isinstance(node.func, ast.Name) or node.keywords:
            raise self.fail("calls must be plain 'name(args)'", node)
        name = node.func.id
        if name in ("f32", "i32", "u32"):
            return self._cast(NAMED[name], node)
        if name in NAMED and isinstance(NAMED[name], Vector):
            return self._construct_vector(NAMED[name], node)  # type: ignore[arg-type]
        if name in self.structs:
            return self._construct_struct(self.structs[name], node)
        if name in BUILTINS:
            return self._builtin(name, node)
        if name in self.signatures:
            return self._user_call(name, node)
        raise self.fail(f"unknown function '{name}'", node)

    def _cast(self, t: SklType, node: ast.Call) -> ir.Expr:
        operand = self.build(node.args[0])
        if _soft(operand):
            return _retype(operand, t)
        if not isinstance(operand.type, Scalar):
            raise self.fail(f"cannot cast {operand.type} to {t}", node)
        return ir.Cast(t, operand)

    def _construct_vector(self, t: Vector, node: ast.Call) -> ir.Expr:
        args = [_retype(self.build(a), t.elem) for a in node.args]
        width = sum(a.type.size if isinstance(a.type, Vector) else 1 for a in args)
        if any(elem_of(a.type) != t.elem for a in args) or width not in (1, t.size) or (width == 1 and len(args) != 1):
            raise self.fail(f"cannot build {t} from {[a.type for a in args]}", node)
        return ir.Construct(t, tuple(args))

    def _construct_struct(self, t: Struct, node: ast.Call) -> ir.Expr:
        if len(node.args) != len(t.fields):
            raise self.fail(f"{t.name} takes {len(t.fields)} fields", node)
        args = []
        for arg, (fname, ftype) in zip(node.args, t.fields, strict=True):
            value = _retype(self.build(arg), ftype)
            if value.type != ftype:
                raise self.fail(f"field {t.name}.{fname} expects {ftype}, got {value.type}", node)
            args.append(value)
        return ir.Construct(t, tuple(args))

    def _builtin(self, name: str, node: ast.Call) -> ir.Expr:
        spec = BUILTINS[name]
        args = [self.build(a) for a in node.args]
        if len(args) != spec.arity:
            raise self.fail(f"{name}() takes {spec.arity} arguments", node)
        typed = [a for a in args if not _soft(a)]
        target = typed[-1].type if typed else F32
        args = [_retype(a, elem_of(target) or target) for a in args]
        try:
            result = spec.rule([a.type for a in args])
        except BuiltinTypeError as exc:
            raise self.fail(f"{name}(): {exc}", node) from exc
        return ir.Builtin(result, name, tuple(args))

    def _user_call(self, name: str, node: ast.Call) -> ir.Expr:
        params, ret = self.signatures[name]
        if len(node.args) != len(params):
            raise self.fail(f"{name}() takes {len(params)} arguments", node)
        args = [self.expect(a, p) for a, p in zip(node.args, params, strict=True)]
        self.calls.add(name)
        return ir.Call(ret, name, tuple(args))
