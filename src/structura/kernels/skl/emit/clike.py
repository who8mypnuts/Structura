"""Shared emitter for the C-like targets (CUDA, OpenCL, WGSL, GLSL). Targets override small syntax hooks.

Declarations are hoisted to the top of each function (SKL variables have one type per function). Buffer
parameters are either passed as pointers (CUDA/OpenCL) or bound as module globals (WGSL/GLSL,
``buffers_are_globals``); in the latter case scalar kernel parameters live in a uniform block.
"""

from __future__ import annotations

from .. import ir
from ..builtins import BUILTINS
from ..types import BOOL, F32, I32, U32, Buffer, LocalArray, Scalar, SklType, Struct, Vector

PRECEDENCE_OPS = {"and": "&&", "or": "||", "//": "/"}


def float_literal(value: float) -> str:
    text = repr(float(value))
    if "e" in text or "E" in text:
        mantissa, exponent = text.lower().split("e")
        mantissa = mantissa if "." in mantissa else mantissa + ".0"
        return f"{mantissa}e{exponent}"
    return text if "." in text else text + ".0"


class CLikeEmitter:
    target = "c"
    buffers_are_globals = False
    params_immutable = False  # WGSL: parameters that are assigned get a local copy

    def __init__(self, module: ir.Module) -> None:
        self.module = module
        self.lines: list[str] = []
        self.indent = 0
        self.kernel: ir.Function | None = None

    # -- hooks (override per target) ------------------------------------------------------------------
    def type_name(self, t: SklType) -> str:
        raise NotImplementedError

    def literal(self, c: ir.Const) -> str:
        if c.type == BOOL:
            return "true" if c.value else "false"
        if c.type == F32:
            return float_literal(float(c.value)) + "f"
        return f"{int(c.value)}u" if c.type == U32 else str(int(c.value))

    def construct_vector(self, t: Vector, args: list[str], arg_types: list[SklType]) -> str:
        return f"{self.type_name(t)}({', '.join(args)})"

    def construct_struct(self, t: Struct, args: list[str]) -> str:
        return f"{t.name}({', '.join(args)})"

    def cast(self, t: SklType, operand: str) -> str:
        return f"{self.type_name(t)}({operand})"

    def declare(self, name: str, t: SklType) -> str:
        return f"{self.type_name(t)} {name};"

    def function_header(self, f: ir.Function) -> str:
        raise NotImplementedError

    def kernel_header(self, f: ir.Function) -> list[str]:
        raise NotImplementedError

    def struct_definition(self, s: Struct) -> list[str]:
        raise NotImplementedError

    def prelude(self) -> str:
        return ""

    def shift_rhs(self, rhs: str, t: SklType) -> str:
        return rhs

    def scalar_param(self, name: str) -> str:
        return name

    # -- driving ----------------------------------------------------------------------------------------
    def emit(self) -> str:
        out = [self.prelude()]
        for struct in self.module.structs.values():
            out.extend(self.struct_definition(struct))
        out.extend(self.globals_section())
        for name in self.module.order:
            out.extend(self.function(self.module.functions[name]))
        return "\n".join(out) + "\n"

    def globals_section(self) -> list[str]:
        return []

    def function(self, f: ir.Function) -> list[str]:
        self.lines, self.indent, self.kernel = [], 1, f if f.is_kernel else None
        mutated = assigned_params(f) if self.params_immutable and not f.is_kernel else set()
        signature_f = rename_params(f, mutated)
        header = self.kernel_header(f) if f.is_kernel else [self.function_header(signature_f) + " {"]
        for name in sorted(mutated):
            self.line(self.declare(name, dict(f.params)[name]))
            self.line(f"{name} = {PARAM_PREFIX}{name};")
        for name, t in sorted(self.hoisted(f).items()):
            self.line(self.declare(name, t))
        self.block(f.body)
        return [*header, *self.lines, "}", ""]

    def hoisted(self, f: ir.Function) -> dict[str, SklType]:
        found: dict[str, SklType] = {}

        def walk(stmts: tuple[ir.Stmt, ...]) -> None:
            for s in stmts:
                if isinstance(s, ir.Declare):
                    found[s.name] = s.type
                elif isinstance(s, ir.For):
                    found[s.var] = s.var_type
                    walk(s.body)
                elif isinstance(s, ir.If):
                    walk(s.body)
                    walk(s.orelse)
                elif isinstance(s, ir.While):
                    walk(s.body)

        walk(f.body)
        return found

    def line(self, text: str) -> None:
        self.lines.append("    " * self.indent + text)

    def block(self, stmts: tuple[ir.Stmt, ...]) -> None:
        for stmt in stmts:
            self.statement(stmt)

    def nested(self, head: str, body: tuple[ir.Stmt, ...]) -> None:
        self.line(head + " {")
        self.indent += 1
        self.block(body)
        self.indent -= 1
        self.line("}")

    def statement(self, s: ir.Stmt) -> None:  # noqa: C901 - a flat dispatch over statement kinds
        if isinstance(s, ir.Declare):
            if s.value is not None:
                self.line(f"{s.name} = {self.expr(s.value)};")
        elif isinstance(s, ir.Assign):
            self.line(f"{s.name} = {self.expr(s.value)};")
        elif isinstance(s, ir.Store):
            self.line(f"{self.expr(s.target)}[{self.expr(s.index)}] = {self.expr(s.value)};")
        elif isinstance(s, ir.If):
            self.nested(f"if ({self.expr(s.cond)})", s.body)
            if s.orelse:
                self.nested("else", s.orelse)
        elif isinstance(s, ir.For):
            negative = isinstance(s.step, ir.Const) and int(s.step.value) < 0
            cond = f"{s.var} {'>' if negative else '<'} {self.expr(s.stop)}"
            self.nested(
                f"for ({s.var} = {self.expr(s.start)}; {cond}; {s.var} = {s.var} + {self.expr(s.step)})", s.body
            )
        elif isinstance(s, ir.While):
            self.nested(f"while ({self.expr(s.cond)})", s.body)
        elif isinstance(s, ir.Break):
            self.line("break;")
        elif isinstance(s, ir.Continue):
            self.line("continue;")
        elif isinstance(s, ir.Return):
            self.line("return;" if s.value is None else f"return {self.expr(s.value)};")
        elif isinstance(s, ir.ExprStmt):
            self.line(self.expr(s.expr) + ";")

    # -- expressions -------------------------------------------------------------------------------------
    def expr(self, e: ir.Expr) -> str:  # noqa: C901, PLR0911 - a flat dispatch over node kinds
        if isinstance(e, ir.Const):
            return self.literal(e)
        if isinstance(e, ir.Var):
            return self.var(e)
        if isinstance(e, ir.Unary):
            op = "!" if e.op == "not" else e.op
            return f"({op}{self.expr(e.operand)})"
        if isinstance(e, ir.Binary):
            return self.binary(e)
        if isinstance(e, ir.Call):
            return f"{e.func}({', '.join(self.call_args(e))})"
        if isinstance(e, ir.Builtin):
            return self.builtin(e)
        if isinstance(e, ir.Construct):
            return self.construct(e)
        if isinstance(e, ir.Cast):
            return self.cast(e.type, self.expr(e.operand))
        if isinstance(e, ir.Component):
            return f"{self.expr(e.base)}.{'xyzw'[e.index]}"
        if isinstance(e, ir.FieldGet):
            return f"{self.expr(e.base)}.{e.field}"
        if isinstance(e, ir.Index):
            return f"{self.expr(e.base)}[{self.expr(e.index)}]"
        if isinstance(e, ir.Select):
            template = BUILTINS["select"].spelling(self.target, e.type)
            return template.format(self.expr(e.cond), self.expr(e.if_true), self.expr(e.if_false))
        raise TypeError(f"cannot emit {e!r}")

    def var(self, e: ir.Var) -> str:
        k = self.kernel
        is_kernel_scalar = k is not None and isinstance(e.type, Scalar) and e.name in dict(k.params)
        if is_kernel_scalar and self.buffers_are_globals and k is not None and e.name != k.params[0][0]:
            return self.scalar_param(e.name)
        return e.name

    def binary(self, e: ir.Binary) -> str:
        op = PRECEDENCE_OPS.get(e.op, e.op)
        right = self.expr(e.right)
        if e.op in ("<<", ">>"):
            right = self.shift_rhs(right, e.right.type)
        return f"({self.expr(e.left)} {op} {right})"

    def call_args(self, e: ir.Call) -> list[str]:
        callee = self.module.functions[e.func]
        args = []
        for (pname, ptype), arg in zip(callee.params, e.args, strict=True):
            if self.buffers_are_globals and isinstance(ptype, Buffer):
                if not (isinstance(arg, ir.Var) and arg.name == pname):
                    raise TypeError(f"{self.target}: buffer '{pname}' must be passed under its own name")
                continue
            args.append(self.expr(arg))
        return args

    def builtin(self, e: ir.Builtin) -> str:
        template = BUILTINS[e.name].spelling(self.target, e.args[0].type if e.args else F32)
        return template.format(*(self.expr(a) for a in e.args))

    def construct(self, e: ir.Construct) -> str:
        args = [self.expr(a) for a in e.args]
        if isinstance(e.type, Struct):
            return self.construct_struct(e.type, args)
        assert isinstance(e.type, Vector)
        return self.construct_vector(e.type, args, [a.type for a in e.args])

    def params(self, f: ir.Function, skip_buffers: bool) -> list[tuple[str, SklType]]:
        return [(n, t) for n, t in f.params if not (skip_buffers and isinstance(t, Buffer))]


PARAM_PREFIX = "p_"


def assigned_params(f: ir.Function) -> set[str]:
    names = {n for n, _ in f.params}
    found: set[str] = set()

    def walk(stmts: tuple[ir.Stmt, ...]) -> None:
        for s in stmts:
            if isinstance(s, ir.Assign) and s.name in names:
                found.add(s.name)
            for child in (getattr(s, "body", ()), getattr(s, "orelse", ())):
                walk(child)

    walk(f.body)
    return found


def rename_params(f: ir.Function, names: set[str]) -> ir.Function:
    if not names:
        return f
    params = tuple((PARAM_PREFIX + n if n in names else n, t) for n, t in f.params)
    return ir.Function(f.name, params, f.ret, f.body, f.is_kernel, f.workgroup, f.exact, f.calls, f.source)


def local_array_decl(name: str, t: LocalArray, elem: str, style: str) -> str:
    if style == "wgsl":
        return f"var {name}: array<{elem}, {t.size}>;"
    return f"{elem} {name}[{t.size}];"


__all__ = ["I32", "CLikeEmitter", "float_literal", "local_array_decl"]
