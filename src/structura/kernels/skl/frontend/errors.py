"""SKL compile errors carry the Python source location of the offending construct."""

from __future__ import annotations

import ast


class SklError(Exception):
    def __init__(self, message: str, node: ast.AST | None = None, where: str = "") -> None:
        line = getattr(node, "lineno", None)
        location = f"{where}:{line}: " if where and line else (f"{where}: " if where else "")
        super().__init__(location + message)
