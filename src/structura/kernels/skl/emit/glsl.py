"""GLSL emitter: shared function libraries for the preview engine (GLSL 330/410), and compute kernels
(#version 430) used for testing on Mesa llvmpipe. Buffers are SSBOs, scalar kernel parameters uniforms."""

from __future__ import annotations

from .. import ir
from ..types import BOOL, F32, I32, U32, Buffer, LocalArray, Scalar, SklType, Struct, Vector
from .clike import CLikeEmitter, float_literal

PRELUDE = """\
float sk_min3(vec3 v) { return min(v.x, min(v.y, v.z)); }
float sk_max3(vec3 v) { return max(v.x, max(v.y, v.z)); }
"""


class GLSLEmitter(CLikeEmitter):
    target = "glsl"
    buffers_are_globals = True

    def type_name(self, t: SklType) -> str:
        if isinstance(t, Vector):
            return ("vec" if t.elem == F32 else "uvec") + str(t.size)
        if isinstance(t, Struct):
            return t.name
        return {F32: "float", I32: "int", U32: "uint", BOOL: "bool"}[t]  # type: ignore[index]

    def literal(self, c: ir.Const) -> str:
        return float_literal(float(c.value)) if c.type == F32 else super().literal(c)

    def declare(self, name: str, t: SklType) -> str:
        if isinstance(t, LocalArray):
            return f"{self.type_name(t.elem)} {name}[{t.size}];"
        return f"{self.type_name(t)} {name};"

    def function_header(self, f: ir.Function) -> str:
        params = ", ".join(f"{self.type_name(t)} {n}" for n, t in self.params(f, skip_buffers=True))
        return f"{'void' if f.ret.name == 'void' else self.type_name(f.ret)} {f.name}({params})"

    def kernel_header(self, f: ir.Function) -> list[str]:
        return ["void main() {", f"    uvec3 {f.params[0][0]} = gl_GlobalInvocationID;"]

    def struct_definition(self, s: Struct) -> list[str]:
        return [f"struct {s.name} {{", *(f"    {self.type_name(t)} {n};" for n, t in s.fields), "};", ""]

    def globals_section(self) -> list[str]:
        kernels = [f for f in self.module.functions.values() if f.is_kernel]
        if not kernels:
            return []
        k = kernels[0]
        x, y, z = k.workgroup
        out = [f"layout(local_size_x = {x}, local_size_y = {y}, local_size_z = {z}) in;"]
        binding = 0
        for name, t in k.params[1:]:
            if isinstance(t, Buffer):
                qualifier = "" if t.writable else "readonly "
                out.append(
                    f"layout(std430, binding = {binding}) {qualifier}buffer B_{name} {{ {self.type_name(t.elem)} "
                    f"{name}[]; }};"
                )
                binding += 1
            elif isinstance(t, Scalar):
                out.append(f"uniform {self.type_name(t)} {name};")
        return [*out, ""]

    def emit(self) -> str:
        has_kernel = any(f.is_kernel for f in self.module.functions.values())
        body = super().emit()
        return ("#version 430\n" + body) if has_kernel else body

    def prelude(self) -> str:
        return PRELUDE
