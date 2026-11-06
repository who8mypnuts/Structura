"""CUDA C++ emitter (compiled at runtime with NVRTC)."""

from __future__ import annotations

from .. import ir
from ..types import BOOL, F32, I32, U32, Buffer, LocalArray, SklType, Struct, Vector
from .clike import CLikeEmitter
from .cuda_prelude import cuda_prelude


class CudaEmitter(CLikeEmitter):
    target = "cuda"

    def type_name(self, t: SklType) -> str:
        if isinstance(t, Vector):
            return ("float" if t.elem == F32 else "uint") + str(t.size)
        if isinstance(t, Struct):
            return t.name
        return {F32: "float", I32: "int", U32: "unsigned int", BOOL: "bool"}[t]  # type: ignore[index]

    def construct_vector(self, t: Vector, args: list[str], arg_types: list[SklType]) -> str:
        if len(args) == 1 and not isinstance(arg_types[0], Vector):
            return f"sk_splat{t.size}({args[0]})" if t.elem == F32 else f"make_uint{t.size}({', '.join(args * t.size)})"
        if len(args) == 2 and isinstance(arg_types[0], Vector):
            return f"sk_cat({args[0]}, {args[1]})"
        prefix = "float" if t.elem == F32 else "uint"
        return f"make_{prefix}{t.size}({', '.join(args)})"

    def construct_struct(self, t: Struct, args: list[str]) -> str:
        return f"{t.name}{{{', '.join(args)}}}"

    def cast(self, t: SklType, operand: str) -> str:
        return f"(({self.type_name(t)})({operand}))"

    def declare(self, name: str, t: SklType) -> str:
        if isinstance(t, LocalArray):
            return f"{self.type_name(t.elem)} {name}[{t.size}];"
        return f"{self.type_name(t)} {name};"

    def param(self, name: str, t: SklType) -> str:
        if isinstance(t, Buffer):
            const = "" if t.writable else "const "
            return f"{const}{self.type_name(t.elem)}* __restrict__ {name}"
        return f"{self.type_name(t)} {name}"

    def function_header(self, f: ir.Function) -> str:
        params = ", ".join(self.param(n, t) for n, t in f.params)
        ret = "void" if f.ret.name == "void" else self.type_name(f.ret)
        return f"__device__ {ret} {f.name}({params})"

    def kernel_header(self, f: ir.Function) -> list[str]:
        params = ", ".join(self.param(n, t) for n, t in f.params[1:])
        gid = f.params[0][0]
        return [
            f'extern "C" __global__ void {f.name}({params}) {{',
            f"    uint3 {gid} = make_uint3(blockIdx.x * blockDim.x + threadIdx.x, "
            "blockIdx.y * blockDim.y + threadIdx.y, blockIdx.z * blockDim.z + threadIdx.z);",
        ]

    def struct_definition(self, s: Struct) -> list[str]:
        return [f"struct {s.name} {{ {' '.join(f'{self.type_name(t)} {n};' for n, t in s.fields)} }};", ""]

    def prelude(self) -> str:
        return cuda_prelude()
