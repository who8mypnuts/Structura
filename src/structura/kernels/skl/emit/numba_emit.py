"""Numba emitter: SKL IR → Python source compiled with @njit (the CPU backend, docs/11 §2).

Vectors and structs become tuples; u32/i32 results are wrapped to 32 bits; local arrays become per-worker
scratch arrays passed as hidden trailing parameters (allocated once per chunk by the kernel dispatcher).
"""

from __future__ import annotations

from .. import ir
from ..builtins import BUILTINS
from ..types import BOOL, F32, I32, U32, LocalArray, SklType, Struct, Vector
from .clike import float_literal

WRAP = {U32: "np.uint32", I32: "np.int32"}
VEC_OPS = {"+": "add", "-": "sub", "*": "mul", "/": "div"}
NO_VECTOR_SUFFIX = {"min3", "max3", "select", "bitcast_u32", "bitcast_f32", "reverse_bits", "count_ones"}


def dtype_name(t: SklType) -> str:
    return {F32: "np.float32", U32: "np.uint32", I32: "np.int32", BOOL: "np.bool_"}[t]  # type: ignore[index]


class NumbaEmitter:
    def __init__(self, module: ir.Module) -> None:
        self.module = module
        self.scratch: dict[str, list[tuple[str, LocalArray]]] = {}
        self.lines: list[str] = []
        self.indent = 0
        self.fn: ir.Function | None = None

    # -- scratch (local arrays) -----------------------------------------------------------------------
    def _own_arrays(self, f: ir.Function) -> list[tuple[str, LocalArray]]:
        found: list[tuple[str, LocalArray]] = []

        def walk(stmts: tuple[ir.Stmt, ...]) -> None:
            for s in stmts:
                if isinstance(s, ir.Declare) and isinstance(s.type, LocalArray):
                    found.append((f"{f.name}__{s.name}", s.type))
                for child in (getattr(s, "body", ()), getattr(s, "orelse", ())):
                    walk(child)

        walk(f.body)
        return found

    def _compute_scratch(self) -> None:
        for name in self.module.order:
            f = self.module.functions[name]
            needed = dict(self._own_arrays(f))
            for callee in f.calls:
                needed.update(dict(self.scratch[callee]))
            self.scratch[name] = sorted(needed.items())

    # -- driving ----------------------------------------------------------------------------------------
    def emit(self) -> str:
        self._compute_scratch()
        out = [
            "import math",
            "import numpy as np",
            "from numba import njit, prange",
            "from structura.kernels.skl.emit.numba_prelude import HELPERS",
            "globals().update(HELPERS)",
            "",
        ]
        for name in self.module.order:
            out.extend(self.function(self.module.functions[name]))
            if self.module.functions[name].is_kernel:
                out.extend(self.dispatcher(self.module.functions[name]))
        return "\n".join(out) + "\n"

    def function(self, f: ir.Function) -> list[str]:
        self.fn, self.lines, self.indent = f, [], 1
        params = [n for n, _ in f.params] + [n for n, _ in self.scratch[f.name]]
        fastmath = "False" if f.exact else "True"
        self.block(f.body)
        return [
            f"@njit(nogil=True, cache=True, fastmath={fastmath})",
            f"def {f.name}({', '.join(params)}):",
            *(self.lines or ["    pass"]),
            "",
        ]

    def dispatcher(self, f: ir.Function) -> list[str]:
        params = [n for n, _ in f.params[1:]]
        scratch = self.scratch[f.name]
        alloc = [f"            {n} = np.empty({t.size}, {dtype_name(t.elem)})" for n, t in scratch]
        call = ", ".join(["(np.uint32(x), np.uint32(y), np.uint32(z))", *params, *(n for n, _ in scratch)])
        return [
            "@njit(nogil=True, cache=True, parallel=True)",
            f"def dispatch_{f.name}(gx, gy, gz{''.join(', ' + p for p in params)}):",
            "    total = gx * gy * gz",
            "    chunks = (total + 255) // 256",
            "    for c in prange(chunks):",
            *(line.replace("            ", "        ", 1) for line in alloc),
            "        for idx in range(c * 256, min(total, (c + 1) * 256)):",
            "            x = idx % gx",
            "            y = (idx // gx) % gy",
            "            z = idx // (gx * gy)",
            f"            {f.name}({call})",
            "",
        ]

    def line(self, text: str) -> None:
        self.lines.append("    " * self.indent + text)

    def block(self, stmts: tuple[ir.Stmt, ...]) -> None:
        before = len(self.lines)
        for s in stmts:
            self.statement(s)
        if len(self.lines) == before:
            self.line("pass")

    def nested(self, head: str, body: tuple[ir.Stmt, ...]) -> None:
        self.line(head)
        self.indent += 1
        self.block(body)
        self.indent -= 1

    def statement(self, s: ir.Stmt) -> None:  # noqa: C901 - flat dispatch over statement kinds
        if isinstance(s, ir.Declare):
            if s.value is not None:
                self.line(f"{s.name} = {self.expr(s.value)}")
        elif isinstance(s, ir.Assign):
            self.line(f"{s.name} = {self.expr(s.value)}")
        elif isinstance(s, ir.Store):
            self.line(f"{self.expr(s.target)}[{self.expr(s.index)}] = {self.expr(s.value)}")
        elif isinstance(s, ir.If):
            self.nested(f"if {self.expr(s.cond)}:", s.body)
            if s.orelse:
                self.nested("else:", s.orelse)
        elif isinstance(s, ir.For):
            loop = f"_r_{s.var}"
            self.line(f"for {loop} in range({self.expr(s.start)}, {self.expr(s.stop)}, {self.expr(s.step)}):")
            self.indent += 1
            self.line(f"{s.var} = {WRAP[s.var_type]}({loop})")  # type: ignore[index]
            self.block(s.body)
            self.indent -= 1
        elif isinstance(s, ir.While):
            self.nested(f"while {self.expr(s.cond)}:", s.body)
        elif isinstance(s, ir.Break):
            self.line("break")
        elif isinstance(s, ir.Continue):
            self.line("continue")
        elif isinstance(s, ir.Return):
            self.line("return" if s.value is None else f"return {self.expr(s.value)}")
        elif isinstance(s, ir.ExprStmt):
            self.line(self.expr(s.expr))

    # -- expressions ----------------------------------------------------------------------------------------
    def expr(self, e: ir.Expr) -> str:  # noqa: C901, PLR0911 - flat dispatch over node kinds
        if isinstance(e, ir.Const):
            return self.literal(e)
        if isinstance(e, ir.Var):
            return self.var(e)
        if isinstance(e, ir.Unary):
            return self.unary(e)
        if isinstance(e, ir.Binary):
            return self.binary(e)
        if isinstance(e, ir.Call):
            scratch = [n for n, _ in self.scratch[e.func]]
            return f"{e.func}({', '.join([*(self.expr(a) for a in e.args), *scratch])})"
        if isinstance(e, ir.Builtin):
            return self.builtin(e)
        if isinstance(e, ir.Construct):
            return self.construct(e)
        if isinstance(e, ir.Cast):
            return f"{dtype_name(e.type)}({self.expr(e.operand)})"
        if isinstance(e, ir.Component):
            return f"{self.expr(e.base)}[{e.index}]"
        if isinstance(e, ir.FieldGet):
            assert isinstance(e.base.type, Struct)
            return f"{self.expr(e.base)}[{e.base.type.field_index(e.field)}]"
        if isinstance(e, ir.Index):
            return f"{self.expr(e.base)}[{self.expr(e.index)}]"
        if isinstance(e, ir.Select):
            return f"({self.expr(e.if_true)} if {self.expr(e.cond)} else {self.expr(e.if_false)})"
        raise TypeError(f"cannot emit {e!r}")

    def literal(self, c: ir.Const) -> str:
        if c.type == BOOL:
            return "True" if c.value else "False"
        if c.type == F32:
            return f"np.float32({float_literal(float(c.value))})"
        return f"{WRAP[c.type]}({int(c.value)})"  # type: ignore[index]

    def var(self, e: ir.Var) -> str:
        if isinstance(e.type, LocalArray):
            assert self.fn is not None
            return f"{self.fn.name}__{e.name}"
        return e.name

    def unary(self, e: ir.Unary) -> str:
        operand = self.expr(e.operand)
        if e.op == "not":
            return f"(not {operand})"
        if isinstance(e.type, Vector):
            return f"v{e.type.size}_neg({operand})"
        return f"{WRAP[e.type]}({e.op}{operand})" if e.type in WRAP else f"({e.op}{operand})"

    def binary(self, e: ir.Binary) -> str:
        left, right = self.expr(e.left), self.expr(e.right)
        if isinstance(e.type, Vector):
            kind = ("v" if isinstance(e.left.type, Vector) else "s") + (
                "v" if isinstance(e.right.type, Vector) else "s"
            )
            return f"v{e.type.size}_{VEC_OPS[e.op]}_{kind}({left}, {right})"
        if e.op in ("and", "or"):
            return f"({left} {e.op} {right})"
        if e.type == I32 and e.op in ("//", "%"):
            return f"sk_{'idiv' if e.op == '//' else 'imod'}({left}, {right})"
        text = f"({left} {e.op} {right})"
        return f"{WRAP[e.type]}{text}" if e.type in WRAP else text

    def builtin(self, e: ir.Builtin) -> str:
        args = [self.expr(a) for a in e.args]
        if e.name == "select":
            return f"({args[1]} if {args[0]} else {args[2]})"
        name = f"sk_{e.name}"
        first = e.args[0].type
        if isinstance(first, Vector) and e.name not in NO_VECTOR_SUFFIX:
            name += f"_v{first.size}"
            if e.name == "mix" and not isinstance(e.args[2].type, Vector):
                name += "s"
        assert BUILTINS[e.name] is not None
        return f"{name}({', '.join(args)})"

    def construct(self, e: ir.Construct) -> str:
        args = [self.expr(a) for a in e.args]
        if isinstance(e.type, Vector):
            if len(args) == 1 and not isinstance(e.args[0].type, Vector):
                return f"v{e.type.size}_splat({args[0]})"
            if len(args) == 2 and isinstance(e.args[0].type, Vector):
                return f"({args[0]} + ({args[1]},))"
        return "(" + ", ".join(args) + ("," if len(args) == 1 else "") + ")"
