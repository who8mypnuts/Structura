"""SKL front end: collect tagged objects, type-check, and produce a closed IR module in dependency order."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .. import ir
from .collect import Collector
from .errors import SklError
from .statements import FunctionBuilder, signature

__all__ = ["SklError", "compile_module"]


def _dependency_order(functions: dict[str, ir.Function]) -> list[str]:
    order: list[str] = []
    state: dict[str, int] = {}

    def visit(name: str, path: tuple[str, ...]) -> None:
        if state.get(name) == 2:
            return
        if state.get(name) == 1:
            raise SklError("recursion is not allowed in SKL: " + " -> ".join((*path, name)))
        state[name] = 1
        for callee in sorted(functions[name].calls):
            visit(callee, (*path, name))
        state[name] = 2
        order.append(name)

    for name in sorted(functions):
        visit(name, ())
    return order


def compile_module(entries: Iterable[Any]) -> ir.Module:
    """Compile the SKL functions/kernels reachable from ``entries`` (decorated Python objects)."""
    collector = Collector()
    for entry in entries:
        collector.add(entry)
    structs = collector.structs
    signatures = {name: signature(src, structs) for name, src in collector.functions.items()}
    functions = {name: FunctionBuilder(src, signatures, structs).build() for name, src in collector.functions.items()}
    return ir.Module(functions, dict(structs), _dependency_order(functions))
