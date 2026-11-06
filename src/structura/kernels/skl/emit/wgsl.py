"""WGSL emitter (wgpu). Buffers become module-scope storage bindings and scalar kernel parameters a uniform
struct ``params`` (binding order: buffers in parameter order, then the uniform block)."""

from __future__ import annotations

from .. import ir
from ..types import BOOL, F32, I32, U32, Buffer, LocalArray, Scalar, SklType, Struct, Vector
from .clike import CLikeEmitter, float_literal

PRELUDE = """\
fn sk_min3(v: vec3<f32>) -> f32 { return min(v.x, min(v.y, v.z)); }
fn sk_max3(v: vec3<f32>) -> f32 { return max(v.x, max(v.y, v.z)); }
"""


class WGSLEmitter(CLikeEmitter):
    target = "wgsl"
    buffers_are_globals = True
    params_immutable = True

    def type_name(self, t: SklType) -> str:
        if isinstance(t, Vector):
            return f"vec{t.size}<{t.elem.name}>"
        if isinstance(t, Struct):
            return t.name
        return {F32: "f32", I32: "i32", U32: "u32", BOOL: "bool"}[t]  # type: ignore[index]

    def literal(self, c: ir.Const) -> str:
        if c.type == F32:
            return float_literal(float(c.value)) + "f"
        if c.type == I32:
            return f"{int(c.value)}i"
        return super().literal(c)

    def declare(self, name: str, t: SklType) -> str:
        if isinstance(t, LocalArray):
            return f"var {name}: array<{self.type_name(t.elem)}, {t.size}>;"
        return f"var {name}: {self.type_name(t)};"

    def shift_rhs(self, rhs: str, t: SklType) -> str:
        return rhs if t == U32 else f"u32({rhs})"

    def scalar_param(self, name: str) -> str:
        return f"params.{name}"

    def function_header(self, f: ir.Function) -> str:
        params = ", ".join(f"{n}: {self.type_name(t)}" for n, t in self.params(f, skip_buffers=True))
        ret = "" if f.ret.name == "void" else f" -> {self.type_name(f.ret)}"
        return f"fn {f.name}({params}){ret}"

    def kernel_header(self, f: ir.Function) -> list[str]:
        x, y, z = f.workgroup
        return [
            f"@compute @workgroup_size({x}, {y}, {z})",
            f"fn {f.name}(@builtin(global_invocation_id) {f.params[0][0]}: vec3<u32>) {{",
        ]

    def struct_definition(self, s: Struct) -> list[str]:
        return [f"struct {s.name} {{", *(f"    {n}: {self.type_name(t)}," for n, t in s.fields), "}", ""]

    def globals_section(self) -> list[str]:
        kernels = [f for f in self.module.functions.values() if f.is_kernel]
        if not kernels:
            return []
        if len(kernels) > 1:
            raise TypeError("a WGSL module holds exactly one kernel")
        k = kernels[0]
        out, binding = [], 0
        for name, t in k.params[1:]:
            if isinstance(t, Buffer):
                access = "read_write" if t.writable else "read"
                out.append(f"@group(0) @binding({binding}) var<storage, {access}> {name}: array<{t.elem.name}>;")
                binding += 1
        scalars = [(n, t) for n, t in k.params[1:] if isinstance(t, Scalar)]
        if scalars:
            out += [
                "struct Params {",
                *(f"    {n}: {self.type_name(t)}," for n, t in scalars),
                "}",
                f"@group(0) @binding({binding}) var<uniform> params: Params;",
            ]
        return [*out, ""]

    def prelude(self) -> str:
        return PRELUDE
