"""Statement lowering and whole-function compilation (docs/11 §3.2).

Every local variable has one type for the whole function (C-like emitters hoist declarations), is created
by its first assignment (or an annotated assignment), and vectors/structs are immutable values.
"""

from __future__ import annotations

import ast
from collections.abc import Callable
from typing import Any

from .. import ir
from ..reserved import RESERVED
from ..types import BOOL, I32, U32, UVEC3, Buffer, LocalArray, Scalar, SklType, Struct
from .annotations import annotation_type
from .collect import FunctionSource
from .errors import SklError
from .expressions import ARITH, BITS, ExprBuilder, _retype

Signatures = dict[str, tuple[list[SklType], SklType]]


class FunctionBuilder:
    def __init__(self, src: FunctionSource, signatures: Signatures, structs: dict[str, Struct]) -> None:
        self.src, self.structs = src, structs
        params, self.ret = signatures[src.name]
        self.param_names = [a.arg for a in src.node.args.args]
        self.scope: dict[str, SklType] = dict(zip(self.param_names, params, strict=True))
        self.exprs = ExprBuilder(self.scope, signatures, structs, src.globals, src.where)

    def fail(self, message: str, node: ast.AST) -> SklError:
        return SklError(message, node, self.src.where)

    def build(self) -> ir.Function:
        body = self.block(self.src.node.body)
        params = tuple(zip(self.param_names, (self.scope[p] for p in self.param_names), strict=True))
        meta = self.src.meta
        return ir.Function(
            self.src.name,
            params,
            self.ret,
            body,
            meta.kind == "kernel",
            meta.workgroup,
            meta.exact,
            frozenset(self.exprs.calls),
            ast.unparse(self.src.node),
        )

    def block(self, nodes: list[ast.stmt]) -> tuple[ir.Stmt, ...]:
        out: list[ir.Stmt] = []
        for node in nodes:
            if (
                isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
            ):
                continue  # docstring
            out.extend(self.statement(node))
        return tuple(out)

    def statement(self, node: ast.stmt) -> list[ir.Stmt]:
        handlers: dict[type, Callable[[Any], list[ir.Stmt]]] = {
            ast.Assign: self._assign,
            ast.AnnAssign: self._ann_assign,
            ast.AugAssign: self._aug_assign,
            ast.If: self._if,
            ast.For: self._for,
            ast.While: self._while,
            ast.Return: self._return,
            ast.Expr: self._expr,
            ast.Break: lambda n: [ir.Break()],
            ast.Continue: lambda n: [ir.Continue()],
            ast.Pass: lambda n: [],
        }
        handler = handlers.get(type(node))
        if handler is None:
            raise self.fail(f"unsupported statement: {ast.unparse(node)}", node)
        return handler(node)

    # -- assignments ----------------------------------------------------------------------------------
    def _bind(self, name: str, value: ir.Expr, node: ast.AST, declared: SklType | None = None) -> list[ir.Stmt]:
        check_name(name, node, self.src.where)
        if name in self.scope:
            target = self.scope[name]
            value = _retype(value, target)
            if value.type != target or isinstance(target, Buffer | LocalArray):
                raise self.fail(f"'{name}' is {target}; cannot assign {value.type}", node)
            return [ir.Assign(name, value)]
        t = declared or value.type
        value = _retype(value, t)
        if value.type != t:
            raise self.fail(f"'{name}: {t}' cannot hold {value.type}", node)
        self.scope[name] = t
        return [ir.Declare(name, t, value)]

    def _local_array(self, name: str, call: ast.Call) -> list[ir.Stmt]:
        elem = annotation_type(call.args[0], self.structs, self.src.where)
        size = call.args[1]
        if not isinstance(elem, Scalar) or not isinstance(size, ast.Constant) or not isinstance(size.value, int):
            raise self.fail("local(type, size) needs a scalar type and an integer constant size", call)
        check_name(name, call, self.src.where)
        self.scope[name] = LocalArray(elem, size.value)
        return [ir.Declare(name, self.scope[name], None)]

    def _assign(self, node: ast.Assign) -> list[ir.Stmt]:
        if len(node.targets) != 1:
            raise self.fail("only single assignments are supported", node)
        target = node.targets[0]
        if isinstance(target, ast.Subscript):
            return self._store(target, self.exprs.build(node.value), node)
        if not isinstance(target, ast.Name):
            raise self.fail("vectors and structs are immutable; assign a whole new value", node)
        value = node.value
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "local":
            return self._local_array(target.id, value)
        return self._bind(target.id, self.exprs.build(value), node)

    def _ann_assign(self, node: ast.AnnAssign) -> list[ir.Stmt]:
        if not isinstance(node.target, ast.Name) or node.value is None:
            raise self.fail("annotated assignments need a name and a value", node)
        declared = annotation_type(node.annotation, self.structs, self.src.where)
        return self._bind(node.target.id, self.exprs.build(node.value), node, declared)

    def _store(self, target: ast.Subscript, value: ir.Expr, node: ast.AST) -> list[ir.Stmt]:
        base = self.exprs.build(target.value)
        if not isinstance(base, ir.Var) or not (
            isinstance(base.type, LocalArray) or (isinstance(base.type, Buffer) and base.type.writable)
        ):
            raise self.fail("can only store into BufRW buffers and local arrays", node)
        index = self.exprs.build(target.slice)
        index = _retype(index, U32 if index.type not in (I32, U32) else index.type)
        value = _retype(value, base.type.elem)
        if value.type != base.type.elem:
            raise self.fail(f"storing {value.type} into {base.type}", node)
        return [ir.Store(base, index, value)]

    def _aug_assign(self, node: ast.AugAssign) -> list[ir.Stmt]:
        op_node = ast.BinOp(left=_load_of(node.target), op=node.op, right=node.value)
        ast.copy_location(op_node, node)
        if type(node.op) not in ARITH and type(node.op) not in BITS:
            raise self.fail("unsupported augmented assignment", node)
        assign = ast.Assign(targets=[node.target], value=op_node)
        return self._assign(ast.copy_location(assign, node))

    # -- control flow ---------------------------------------------------------------------------------
    def _if(self, node: ast.If) -> list[ir.Stmt]:
        cond = self.exprs.expect(node.test, BOOL)
        return [ir.If(cond, self.block(node.body), self.block(node.orelse))]

    def _while(self, node: ast.While) -> list[ir.Stmt]:
        if node.orelse:
            raise self.fail("while/else is not supported", node)
        return [ir.While(self.exprs.expect(node.test, BOOL), self.block(node.body))]

    def _for(self, node: ast.For) -> list[ir.Stmt]:
        it = node.iter
        if not (
            isinstance(it, ast.Call)
            and isinstance(it.func, ast.Name)
            and it.func.id == "range"
            and isinstance(node.target, ast.Name)
            and 1 <= len(it.args) <= 3
            and not node.orelse
        ):
            raise self.fail("only 'for name in range(...)' loops are supported", node)
        args = [self.exprs.build(a) for a in it.args]
        typed = [a.type for a in args if a.type in (I32, U32) and not isinstance(a, ir.Const)]
        var_type = typed[0] if typed else I32
        args = [_retype(a, var_type) for a in args]
        if any(a.type != var_type for a in args):
            raise self.fail("range() arguments must share one integer type", node)
        start, stop, step = (
            (ir.Const(var_type, 0), args[0], ir.Const(var_type, 1))
            if len(args) == 1
            else (args[0], args[1], args[2] if len(args) == 3 else ir.Const(var_type, 1))
        )
        name = node.target.id
        check_name(name, node, self.src.where)
        if self.scope.setdefault(name, var_type) != var_type:
            raise self.fail(f"loop variable '{name}' changes type", node)
        return [ir.For(name, var_type, start, stop, step, self.block(node.body))]

    def _return(self, node: ast.Return) -> list[ir.Stmt]:
        if node.value is None:
            return [ir.Return(None)]
        return [ir.Return(self.exprs.expect(node.value, self.ret))]

    def _expr(self, node: ast.Expr) -> list[ir.Stmt]:
        return [ir.ExprStmt(self.exprs.build(node.value))]


def _load_of(target: ast.expr) -> ast.expr:
    clone = ast.parse(ast.unparse(target), mode="eval").body
    return ast.copy_location(clone, target)


def check_name(name: str, node: ast.AST | None, where: str) -> None:
    if name in RESERVED or name.startswith(("sk_", "p_", "_r_", "gl_")):
        raise SklError(f"'{name}' is reserved in at least one SKL target; choose another name", node, where)


def signature(src: FunctionSource, structs: dict[str, Struct]) -> tuple[list[SklType], SklType]:
    node = src.node
    check_name(src.name, node, src.where)
    for arg in node.args.args:
        check_name(arg.arg, node, src.where)
    params = [annotation_type(a.annotation, structs, src.where) for a in node.args.args]
    ret = (
        annotation_type(node.returns, structs, src.where)
        if node.returns is not None
        else annotation_type(ast.Constant(None), structs, src.where)
    )
    if src.meta.kind == "kernel" and (not params or params[0] != UVEC3):
        raise SklError("kernels take 'gid: uvec3' as their first parameter", node, src.where)
    return params, ret
