"""Generate the CUDA C++ prelude: float2/3/4 operators and overloaded sk_* maths (DRY: from templates)."""

from __future__ import annotations

COMP = "xyzw"
MATH1 = {
    "sqrt": "sqrtf",
    "sin": "sinf",
    "cos": "cosf",
    "tan": "tanf",
    "asin": "asinf",
    "acos": "acosf",
    "atan": "atanf",
    "exp": "expf",
    "log": "logf",
    "floor": "floorf",
    "ceil": "ceilf",
    "trunc": "truncf",
    "abs": "fabsf",
}


def _vec(n: int) -> str:
    return f"float{n}"


def _make(n: int, parts: list[str]) -> str:
    return f"make_float{n}({', '.join(parts)})"


def _ops(n: int) -> list[str]:
    v, c = _vec(n), COMP[:n]
    out = [f"SKD {v} operator-({v} a) {{ return {_make(n, [f'-a.{k}' for k in c])}; }}"]
    for op in "+-*/":
        out += [
            f"SKD {v} operator{op}({v} a, {v} b) {{ return {_make(n, [f'a.{k} {op} b.{k}' for k in c])}; }}",
            f"SKD {v} operator{op}({v} a, float s) {{ return {_make(n, [f'a.{k} {op} s' for k in c])}; }}",
            f"SKD {v} operator{op}(float s, {v} a) {{ return {_make(n, [f's {op} a.{k}' for k in c])}; }}",
        ]
    return out


def _vector_math(n: int) -> list[str]:
    v, c = _vec(n), COMP[:n]
    out = [
        f"SKD {v} sk_{name}({v} a) {{ return {_make(n, [f'{fn}(a.{k})' for k in c])}; }}" for name, fn in MATH1.items()
    ]
    out += [
        f"SKD {v} sk_min({v} a, {v} b) {{ return {_make(n, [f'fminf(a.{k}, b.{k})' for k in c])}; }}",
        f"SKD {v} sk_max({v} a, {v} b) {{ return {_make(n, [f'fmaxf(a.{k}, b.{k})' for k in c])}; }}",
        f"SKD {v} sk_clamp({v} x, {v} lo, {v} hi) {{ return sk_min(sk_max(x, lo), hi); }}",
        f"SKD {v} sk_fract({v} a) {{ return a - sk_floor(a); }}",
        f"SKD {v} sk_mix({v} a, {v} b, float t) {{ return a + (b - a) * t; }}",
        f"SKD {v} sk_mix({v} a, {v} b, {v} t) {{ return a + (b - a) * t; }}",
        f"SKD float sk_dot({v} a, {v} b) {{ return {' + '.join(f'a.{k} * b.{k}' for k in c)}; }}",
        f"SKD float sk_length({v} a) {{ return sqrtf(sk_dot(a, a)); }}",
        f"SKD {v} sk_normalize({v} a) {{ return a * (1.0f / sk_length(a)); }}",
        f"SKD {v} sk_splat{n}(float s) {{ return {_make(n, ['s'] * n)}; }}",
    ]
    return out


def _scalar_math() -> list[str]:
    out = [f"SKD float sk_{name}(float a) {{ return {fn}(a); }}" for name, fn in MATH1.items()]
    out += [
        "SKD float sk_min(float a, float b) { return fminf(a, b); }",
        "SKD float sk_max(float a, float b) { return fmaxf(a, b); }",
        "SKD float sk_clamp(float x, float lo, float hi) { return fminf(fmaxf(x, lo), hi); }",
        "SKD float sk_fract(float a) { return a - floorf(a); }",
        "SKD float sk_mix(float a, float b, float t) { return a + (b - a) * t; }",
    ]
    for t in ("int", "unsigned int"):
        out += [
            f"SKD {t} sk_min({t} a, {t} b) {{ return a < b ? a : b; }}",
            f"SKD {t} sk_max({t} a, {t} b) {{ return a > b ? a : b; }}",
            f"SKD {t} sk_clamp({t} x, {t} lo, {t} hi) {{ return sk_min(sk_max(x, lo), hi); }}",
        ]
    out.append("SKD int sk_abs(int a) { return a < 0 ? -a : a; }")
    return out


def cuda_prelude() -> str:
    lines = ["#define SKD __device__ __forceinline__"]
    for n in (2, 3, 4):
        lines += _ops(n)
    lines += _scalar_math()
    for n in (2, 3, 4):
        lines += _vector_math(n)
    lines += [
        "SKD float3 sk_cross(float3 a, float3 b) { return make_float3(a.y * b.z - a.z * b.y, "
        "a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x); }",
        "SKD float sk_min3(float3 v) { return fminf(v.x, fminf(v.y, v.z)); }",
        "SKD float sk_max3(float3 v) { return fmaxf(v.x, fmaxf(v.y, v.z)); }",
        "SKD float4 sk_cat(float3 v, float w) { return make_float4(v.x, v.y, v.z, w); }",
        "SKD float3 sk_cat(float2 v, float w) { return make_float3(v.x, v.y, w); }",
    ]
    return "\n".join(lines) + "\n"
