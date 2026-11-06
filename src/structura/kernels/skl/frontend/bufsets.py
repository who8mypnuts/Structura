"""Buffer-set desugaring (see ``skl.bufset``): a pure AST rewrite applied before type checking."""

from __future__ import annotations

import ast
import copy
from typing import Any

from .errors import SklError


def bufset_fields(cls: type, source_ast: ast.ClassDef) -> list[ast.arg]:
    fields = []
    for stmt in source_ast.body:
        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            fields.append(ast.arg(arg=stmt.target.id, annotation=copy.deepcopy(stmt.annotation)))
    if not fields:
        raise SklError(f"bufset {cls.__name__} declares no buffers")
    return fields


class _Rewriter(ast.NodeTransformer):
    def __init__(self, groups: dict[str, list[ast.arg]], where: str) -> None:
        self.groups, self.where = groups, where

    def visit_Attribute(self, node: ast.Attribute) -> Any:
        if isinstance(node.value, ast.Name) and node.value.id in self.groups:
            names = [a.arg for a in self.groups[node.value.id]]
            if node.attr not in names:
                raise SklError(f"'{node.value.id}' has no buffer '{node.attr}'", node, self.where)
            return ast.copy_location(ast.Name(id=node.attr, ctx=node.ctx), node)
        return self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> Any:
        args: list[ast.expr] = []
        for arg in node.args:
            if isinstance(arg, ast.Name) and arg.id in self.groups:
                args.extend(ast.copy_location(ast.Name(id=a.arg, ctx=ast.Load()), arg) for a in self.groups[arg.id])
            else:
                args.append(arg)
        node.args = args
        return self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> Any:
        if node.id in self.groups:
            raise SklError(f"buffer set '{node.id}' can only be passed to calls or accessed with '.'", node, self.where)
        return node


def expand_bufsets(node: ast.FunctionDef, globals_: dict[str, Any], fields_of: Any, where: str) -> ast.FunctionDef:
    """Return ``node`` with every bufset-typed parameter expanded (``fields_of(cls)`` → list of ast.arg)."""
    groups: dict[str, list[ast.arg]] = {}
    params: list[ast.arg] = []
    for arg in node.args.args:
        cls = globals_.get(arg.annotation.id) if isinstance(arg.annotation, ast.Name) else None
        if getattr(getattr(cls, "__skl__", None), "kind", None) != "bufset":
            params.append(arg)
            continue
        groups[arg.arg] = fields_of(cls)
        params.extend(copy.deepcopy(groups[arg.arg]))
    if not groups:
        return node
    names = [a.arg for a in params]
    if len(names) != len(set(names)):
        raise SklError("buffer names collide after expanding buffer sets", node, where)
    rewritten = _Rewriter(groups, where).visit(copy.deepcopy(node))
    rewritten.args.args = params
    return ast.fix_missing_locations(rewritten)  # type: ignore[no-any-return]
