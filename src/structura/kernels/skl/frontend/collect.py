"""Collect SKL functions and structs reachable from entry points (following names through __globals__)."""

from __future__ import annotations

import ast
import inspect
import textwrap
from dataclasses import dataclass
from functools import cache
from typing import Any

from ... import skl as api
from ..types import Struct
from .annotations import annotation_type
from .bufsets import bufset_fields, expand_bufsets
from .errors import SklError


@dataclass(frozen=True)
class FunctionSource:
    name: str
    node: ast.FunctionDef
    meta: api.SklMeta
    globals: dict[str, Any]
    where: str


def _source_ast(obj: Any) -> tuple[ast.AST, str]:
    source = textwrap.dedent(inspect.getsource(obj))
    where = f"{inspect.getsourcefile(obj)}"
    return ast.parse(source).body[0], where


def _struct_type(cls: type, structs: dict[str, Struct]) -> Struct:
    node, where = _source_ast(cls)
    assert isinstance(node, ast.ClassDef)
    fields = []
    for stmt in node.body:
        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            fields.append((stmt.target.id, annotation_type(stmt.annotation, structs, where)))
    return Struct(cls.__name__, tuple(fields))


@cache
def _fields_of(cls: type) -> list[ast.arg]:
    node, _ = _source_ast(cls)
    assert isinstance(node, ast.ClassDef)
    return bufset_fields(cls, node)


class Collector:
    def __init__(self) -> None:
        self.functions: dict[str, FunctionSource] = {}
        self.structs: dict[str, Struct] = {}
        self._ids: dict[str, int] = {}

    def add(self, obj: Any) -> None:
        meta = getattr(obj, "__skl__", None)
        if meta is None:
            return
        name = obj.__name__
        if self._ids.get(name, id(obj)) != id(obj):
            raise SklError(f"two different SKL objects are both named '{name}'")
        if name in self._ids:
            return
        self._ids[name] = id(obj)
        if meta.kind == "bufset":
            return
        if meta.kind == "struct":
            self._add_struct_deps(obj)
            self.structs[name] = _struct_type(obj, self.structs)
            return
        node, where = _source_ast(obj)
        if not isinstance(node, ast.FunctionDef):
            raise SklError("SKL functions must be plain 'def' functions", node, where)
        node = expand_bufsets(node, obj.__globals__, _fields_of, where)
        self.functions[name] = FunctionSource(name, node, meta, obj.__globals__, where)
        for ref in {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}:
            if ref in obj.__globals__:
                self.add(obj.__globals__[ref])

    def _add_struct_deps(self, cls: type) -> None:
        module = inspect.getmodule(cls)
        for annotation in getattr(cls, "__annotations__", {}).values():
            target = getattr(module, str(annotation), None)
            if target is not None:
                self.add(target)
