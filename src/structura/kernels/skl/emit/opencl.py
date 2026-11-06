"""OpenCL C emitter (pyopencl; pocl in CI)."""

from __future__ import annotations

from .. import ir
from ..types import BOOL, F32, I32, U32, Buffer, LocalArray, SklType, Struct, Vector
from .clike import CLikeEmitter

PRELUDE = """\
#define SK_OVL __attribute__((overloadable))
inline float sk_min3(float3 v) { return fmin(v.x, fmin(v.y, v.z)); }
inline float sk_max3(float3 v) { return fmax(v.x, fmax(v.y, v.z)); }
inline float SK_OVL sk_fract(float x) { return x - floor(x); }
inline float2 SK_OVL sk_fract(float2 x) { return x - floor(x); }
inline float3 SK_OVL sk_fract(float3 x) { return x - floor(x); }
inline float4 SK_OVL sk_fract(float4 x) { return x - floor(x); }
inline uint sk_reverse_bits(uint x) {
    x = ((x >> 1) & 0x55555555u) | ((x & 0x55555555u) << 1);
    x = ((x >> 2) & 0x33333333u) | ((x & 0x33333333u) << 2);
    x = ((x >> 4) & 0x0F0F0F0Fu) | ((x & 0x0F0F0F0Fu) << 4);
    x = ((x >> 8) & 0x00FF00FFu) | ((x & 0x00FF00FFu) << 8);
    return (x >> 16) | (x << 16);
}
"""


class OpenCLEmitter(CLikeEmitter):
    target = "opencl"

    def type_name(self, t: SklType) -> str:
        if isinstance(t, Vector):
            return ("float" if t.elem == F32 else "uint") + str(t.size)
        if isinstance(t, Struct):
            return t.name
        return {F32: "float", I32: "int", U32: "uint", BOOL: "bool"}[t]  # type: ignore[index]

    def construct_vector(self, t: Vector, args: list[str], arg_types: list[SklType]) -> str:
        return f"({self.type_name(t)})({', '.join(args)})"

    def construct_struct(self, t: Struct, args: list[str]) -> str:
        return f"({t.name}){{{', '.join(args)}}}"

    def cast(self, t: SklType, operand: str) -> str:
        return f"(({self.type_name(t)})({operand}))"

    def declare(self, name: str, t: SklType) -> str:
        if isinstance(t, LocalArray):
            return f"{self.type_name(t.elem)} {name}[{t.size}];"
        return f"{self.type_name(t)} {name};"

    def param(self, name: str, t: SklType) -> str:
        if isinstance(t, Buffer):
            return f"__global {'' if t.writable else 'const '}{self.type_name(t.elem)}* restrict {name}"
        return f"{self.type_name(t)} {name}"

    def function_header(self, f: ir.Function) -> str:
        params = ", ".join(self.param(n, t) for n, t in f.params)
        return f"{self.type_name(f.ret) if f.ret.name != 'void' else 'void'} {f.name}({params})"

    def kernel_header(self, f: ir.Function) -> list[str]:
        params = ", ".join(self.param(n, t) for n, t in f.params[1:])
        gid = f.params[0][0]
        return [
            f"__kernel void {f.name}({params}) {{",
            f"    uint3 {gid} = (uint3)(get_global_id(0), get_global_id(1), get_global_id(2));",
        ]

    def struct_definition(self, s: Struct) -> list[str]:
        fields = " ".join(f"{self.type_name(t)} {n};" for n, t in s.fields)
        return [f"typedef struct {{ {fields} }} {s.name};", ""]

    def prelude(self) -> str:
        return PRELUDE
