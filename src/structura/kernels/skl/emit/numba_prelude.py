"""Helpers for SKL code emitted to Numba: float32 tuple vectors, builtins and C integer semantics.

Everything here is generated from templates (one definition per operation, DRY) and compiled with Numba.
Vectors are tuples of float32; all float helpers return float32 so SKL's numerical contract holds.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from llvmlite import ir as llvm_ir
from numba import njit, types
from numba.extending import intrinsic

F32 = np.float32
COMP = "xyzw"
MATH1 = ("sqrt", "sin", "cos", "tan", "asin", "acos", "atan", "exp", "log", "floor", "ceil", "trunc")


@intrinsic
def _bitcast_f2u(typingctx: Any, x: Any) -> Any:
    def codegen(context: Any, builder: Any, sig: Any, args: Any) -> Any:
        return builder.bitcast(args[0], llvm_ir.IntType(32))

    return types.uint32(types.float32), codegen


@intrinsic
def _bitcast_u2f(typingctx: Any, x: Any) -> Any:
    def codegen(context: Any, builder: Any, sig: Any, args: Any) -> Any:
        return builder.bitcast(args[0], llvm_ir.FloatType())

    return types.float32(types.uint32), codegen


def _tuple(parts: list[str]) -> str:
    return "(" + ", ".join(parts) + ("," if len(parts) == 1 else "") + ")"


def _vector_source(n: int) -> list[str]:
    c = range(n)
    out = [
        f"def v{n}_splat(s): return {_tuple(['s'] * n)}",
        f"def v{n}_neg(a): return {_tuple([f'-a[{i}]' for i in c])}",
    ]
    for name, op in (("add", "+"), ("sub", "-"), ("mul", "*"), ("div", "/")):
        out += [
            f"def v{n}_{name}_vv(a, b): return {_tuple([f'a[{i}] {op} b[{i}]' for i in c])}",
            f"def v{n}_{name}_vs(a, s): return {_tuple([f'a[{i}] {op} s' for i in c])}",
            f"def v{n}_{name}_sv(s, a): return {_tuple([f's {op} a[{i}]' for i in c])}",
        ]
    out += [f"def sk_{fn}_v{n}(a): return {_tuple([f'sk_{fn}(a[{i}])' for i in c])}" for fn in (*MATH1, "abs", "fract")]
    out += [
        f"def sk_min_v{n}(a, b): return {_tuple([f'sk_min(a[{i}], b[{i}])' for i in c])}",
        f"def sk_max_v{n}(a, b): return {_tuple([f'sk_max(a[{i}], b[{i}])' for i in c])}",
        f"def sk_clamp_v{n}(x, lo, hi): return {_tuple([f'sk_clamp(x[{i}], lo[{i}], hi[{i}])' for i in c])}",
        f"def sk_mix_v{n}(a, b, t): return {_tuple([f'a[{i}] + (b[{i}] - a[{i}]) * t[{i}]' for i in c])}",
        f"def sk_mix_v{n}s(a, b, t): return {_tuple([f'a[{i}] + (b[{i}] - a[{i}]) * t' for i in c])}",
        f"def sk_dot_v{n}(a, b): return {' + '.join(f'a[{i}] * b[{i}]' for i in c)}",
        f"def sk_length_v{n}(a): return F32(math.sqrt(sk_dot_v{n}(a, a)))",
        f"def sk_normalize_v{n}(a): return v{n}_mul_vs(a, F32(1.0) / sk_length_v{n}(a))",
    ]
    return out


SCALAR_SOURCE = [
    *(f"def sk_{fn}(x): return F32(math.{fn}(x))" for fn in MATH1),
    "def sk_abs(x): return -x if x < 0 else x",
    "def sk_min(a, b): return a if a < b else b",
    "def sk_max(a, b): return a if a > b else b",
    "def sk_clamp(x, lo, hi): return sk_min(sk_max(x, lo), hi)",
    "def sk_fract(x): return x - F32(math.floor(x))",
    "def sk_mix(a, b, t): return a + (b - a) * t",
    "def sk_atan2(y, x): return F32(math.atan2(y, x))",
    "def sk_pow(x, y): return F32(math.pow(x, y))",
    "def sk_fmod(x, y): return F32(math.fmod(x, y))",
    "def sk_min3(v): return sk_min(v[0], sk_min(v[1], v[2]))",
    "def sk_max3(v): return sk_max(v[0], sk_max(v[1], v[2]))",
    "def sk_cross_v3(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])",
    "def sk_bitcast_u32(x): return _bitcast_f2u(x)",
    "def sk_bitcast_f32(x): return _bitcast_u2f(np.uint32(x))",
    "def sk_idiv(a, b): return np.int32(abs(a) // abs(b) * (1 if (a < 0) == (b < 0) else -1))",
    "def sk_imod(a, b): return np.int32(a - sk_idiv(a, b) * b)",
]
BITS_SOURCE = """
def sk_reverse_bits(x):
    x = np.uint32(((x >> np.uint32(1)) & np.uint32(0x55555555)) | ((x & np.uint32(0x55555555)) << np.uint32(1)))
    x = np.uint32(((x >> np.uint32(2)) & np.uint32(0x33333333)) | ((x & np.uint32(0x33333333)) << np.uint32(2)))
    x = np.uint32(((x >> np.uint32(4)) & np.uint32(0x0F0F0F0F)) | ((x & np.uint32(0x0F0F0F0F)) << np.uint32(4)))
    x = np.uint32(((x >> np.uint32(8)) & np.uint32(0x00FF00FF)) | ((x & np.uint32(0x00FF00FF)) << np.uint32(8)))
    return np.uint32((x >> np.uint32(16)) | (x << np.uint32(16)))

def sk_count_ones(x):
    x = np.uint32(x - ((x >> np.uint32(1)) & np.uint32(0x55555555)))
    x = np.uint32((x & np.uint32(0x33333333)) + ((x >> np.uint32(2)) & np.uint32(0x33333333)))
    x = np.uint32((x + (x >> np.uint32(4))) & np.uint32(0x0F0F0F0F))
    return np.uint32((x * np.uint32(0x01010101)) >> np.uint32(24))
"""


def _build() -> dict[str, Any]:
    namespace: dict[str, Any] = {
        "np": np,
        "math": math,
        "F32": F32,
        "_bitcast_f2u": _bitcast_f2u,
        "_bitcast_u2f": _bitcast_u2f,
    }
    source = [*SCALAR_SOURCE, *(line for n in (2, 3, 4) for line in _vector_source(n))]
    exec("\n".join(source) + "\n" + BITS_SOURCE, namespace)
    helpers = {
        name: njit(nogil=True)(fn)
        for name, fn in namespace.items()
        if name.startswith(("sk_", "v2_", "v3_", "v4_")) and callable(fn)
    }
    namespace.update(helpers)  # helpers call each other through this namespace: point them at the jitted versions
    return helpers


HELPERS: dict[str, Any] = _build()
