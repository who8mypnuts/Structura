"""Turn Python annotation AST nodes into SKL types."""

from __future__ import annotations

import ast

from ..types import NAMED, Buffer, Scalar, SklType, Struct
from .errors import SklError


def annotation_type(node: ast.expr | None, structs: dict[str, Struct], where: str = "") -> SklType:
    if node is None:
        raise SklError("missing type annotation", node, where)
    if isinstance(node, ast.Constant) and node.value is None:
        return NAMED["None"]
    if isinstance(node, ast.Constant) and isinstance(node.value, str):  # string annotations
        return annotation_type(ast.parse(node.value, mode="eval").body, structs, where)
    if isinstance(node, ast.Name):
        if node.id in NAMED:
            return NAMED[node.id]
        if node.id in structs:
            return structs[node.id]
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id in ("Buf", "BufRW"):
        elem = annotation_type(node.slice, structs, where)
        if not isinstance(elem, Scalar) or elem.name not in ("f32", "u32"):
            raise SklError("buffers hold f32 or u32 only (flat buffer ABI)", node, where)
        return Buffer(elem, node.value.id == "BufRW")
    raise SklError(f"unsupported type annotation: {ast.unparse(node)}", node, where)
