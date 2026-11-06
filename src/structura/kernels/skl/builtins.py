"""The one builtin table: type rules and per-target spellings (docs/11 §3.3).

Spelling templates use ``{0}``, ``{1}``… for the emitted arguments. A target may key its spelling by the
argument class: ``"<target>:f"`` (float scalar), ``"<target>:v"`` (float vector), ``"<target>:i"`` (int).
Numba spellings refer to helpers generated in ``emit_numba_prelude``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from .types import BOOL, F32, U32, VEC3, Scalar, SklType, Vector

Rule = Callable[[list[SklType]], SklType]


class BuiltinTypeError(TypeError):
    pass


def _same_numeric(args: list[SklType]) -> SklType:
    if any(a != args[0] for a in args) or not isinstance(args[0], Scalar | Vector) or args[0] == BOOL:
        raise BuiltinTypeError(f"arguments must be the same numeric type, got {args}")
    return args[0]


def _float_like(args: list[SklType]) -> SklType:
    t = _same_numeric(args)
    if not (t == F32 or (isinstance(t, Vector) and t.elem == F32)):
        raise BuiltinTypeError(f"expected f32 or a float vector, got {t}")
    return t


def _mix(args: list[SklType]) -> SklType:
    t = _float_like(args[:2])
    if args[2] not in (F32, t):
        raise BuiltinTypeError("mix(a, b, t): t must be f32 or the type of a")
    return t


def _vector_to_f32(args: list[SklType]) -> SklType:
    t = _same_numeric(args)
    if not (isinstance(t, Vector) and t.elem == F32):
        raise BuiltinTypeError(f"expected float vectors, got {args}")
    return F32


def _vec3_only(result: SklType) -> Rule:
    def rule(args: list[SklType]) -> SklType:
        if any(a != VEC3 for a in args):
            raise BuiltinTypeError(f"expected vec3 arguments, got {args}")
        return result

    return rule


def _normalize(args: list[SklType]) -> SklType:
    _vector_to_f32(args)
    return args[0]


def _select(args: list[SklType]) -> SklType:
    if args[0] != BOOL or args[1] != args[2]:
        raise BuiltinTypeError("select(cond: bool, a, b) needs a and b of the same type")
    return args[1]


def _fixed(params: tuple[SklType, ...], result: SklType) -> Rule:
    def rule(args: list[SklType]) -> SklType:
        if tuple(args) != params:
            raise BuiltinTypeError(f"expected {params}, got {tuple(args)}")
        return result

    return rule


@dataclass(frozen=True)
class BuiltinSpec:
    name: str
    arity: int
    rule: Rule
    spell: dict[str, str] = field(default_factory=dict)

    def spelling(self, target: str, arg_type: SklType) -> str:
        cls = "f" if arg_type == F32 else "v" if isinstance(arg_type, Vector) else "i"
        return self.spell.get(f"{target}:{cls}") or self.spell[target]


def _math1(name: str, c: str, wgsl: str = "", glsl: str = "") -> BuiltinSpec:
    return BuiltinSpec(
        name,
        1,
        _float_like,
        {
            "numba": f"sk_{name}({{0}})",
            "cuda": f"sk_{name}({{0}})",
            "opencl": f"{c}({{0}})",
            "wgsl": f"{wgsl or name}({{0}})",
            "glsl": f"{glsl or name}({{0}})",
        },
    )


SPECS: tuple[BuiltinSpec, ...] = (
    BuiltinSpec(
        "abs",
        1,
        _same_numeric,
        {
            "numba": "sk_abs({0})",
            "cuda": "sk_abs({0})",
            "opencl:f": "fabs({0})",
            "opencl:v": "fabs({0})",
            "opencl": "abs({0})",
            "wgsl": "abs({0})",
            "glsl": "abs({0})",
        },
    ),
    BuiltinSpec(
        "min",
        2,
        _same_numeric,
        {
            "numba": "sk_min({0}, {1})",
            "cuda": "sk_min({0}, {1})",
            "opencl:f": "fmin({0}, {1})",
            "opencl:v": "fmin({0}, {1})",
            "opencl": "min({0}, {1})",
            "wgsl": "min({0}, {1})",
            "glsl": "min({0}, {1})",
        },
    ),
    BuiltinSpec(
        "max",
        2,
        _same_numeric,
        {
            "numba": "sk_max({0}, {1})",
            "cuda": "sk_max({0}, {1})",
            "opencl:f": "fmax({0}, {1})",
            "opencl:v": "fmax({0}, {1})",
            "opencl": "max({0}, {1})",
            "wgsl": "max({0}, {1})",
            "glsl": "max({0}, {1})",
        },
    ),
    BuiltinSpec(
        "clamp",
        3,
        _same_numeric,
        dict.fromkeys(("opencl", "wgsl", "glsl"), "clamp({0}, {1}, {2})")
        | {"numba": "sk_clamp({0}, {1}, {2})", "cuda": "sk_clamp({0}, {1}, {2})"},
    ),
    _math1("sqrt", "sqrt"),
    _math1("sin", "sin"),
    _math1("cos", "cos"),
    _math1("tan", "tan"),
    _math1("asin", "asin"),
    _math1("acos", "acos"),
    _math1("atan", "atan"),
    _math1("exp", "exp"),
    _math1("log", "log"),
    _math1("floor", "floor"),
    _math1("ceil", "ceil"),
    _math1("trunc", "trunc"),
    BuiltinSpec(
        "fract",
        1,
        _float_like,
        {
            "numba": "sk_fract({0})",
            "cuda": "sk_fract({0})",
            "opencl": "sk_fract({0})",
            "wgsl": "fract({0})",
            "glsl": "fract({0})",
        },
    ),
    BuiltinSpec(
        "atan2",
        2,
        _fixed((F32, F32), F32),
        {
            "numba": "sk_atan2({0}, {1})",
            "cuda": "atan2f({0}, {1})",
            "opencl": "atan2({0}, {1})",
            "wgsl": "atan2({0}, {1})",
            "glsl": "atan({0}, {1})",
        },
    ),
    BuiltinSpec(
        "pow",
        2,
        _fixed((F32, F32), F32),
        {
            "numba": "sk_pow({0}, {1})",
            "cuda": "powf({0}, {1})",
            "opencl": "pow({0}, {1})",
            "wgsl": "pow({0}, {1})",
            "glsl": "pow({0}, {1})",
        },
    ),
    BuiltinSpec(
        "fmod",
        2,
        _fixed((F32, F32), F32),
        {
            "numba": "sk_fmod({0}, {1})",
            "cuda": "fmodf({0}, {1})",
            "opencl": "fmod({0}, {1})",
            "wgsl": "({0} - {1} * trunc({0} / {1}))",
            "glsl": "({0} - {1} * trunc({0} / {1}))",
        },
    ),
    BuiltinSpec(
        "mix",
        3,
        _mix,
        {
            "numba": "sk_mix({0}, {1}, {2})",
            "cuda": "sk_mix({0}, {1}, {2})",
            "opencl": "mix({0}, {1}, {2})",
            "wgsl": "mix({0}, {1}, {2})",
            "glsl": "mix({0}, {1}, {2})",
        },
    ),
    BuiltinSpec(
        "dot",
        2,
        _vector_to_f32,
        dict.fromkeys(("opencl", "wgsl", "glsl"), "dot({0}, {1})")
        | {"numba": "sk_dot({0}, {1})", "cuda": "sk_dot({0}, {1})"},
    ),
    BuiltinSpec(
        "cross",
        2,
        _vec3_only(VEC3),
        dict.fromkeys(("opencl", "wgsl", "glsl"), "cross({0}, {1})")
        | {"numba": "sk_cross({0}, {1})", "cuda": "sk_cross({0}, {1})"},
    ),
    BuiltinSpec(
        "length",
        1,
        _vector_to_f32,
        dict.fromkeys(("opencl", "wgsl", "glsl"), "length({0})")
        | {"numba": "sk_length({0})", "cuda": "sk_length({0})"},
    ),
    BuiltinSpec(
        "normalize",
        1,
        _normalize,
        dict.fromkeys(("opencl", "wgsl", "glsl"), "normalize({0})")
        | {"numba": "sk_normalize({0})", "cuda": "sk_normalize({0})"},
    ),
    BuiltinSpec("min3", 1, _vec3_only(F32), dict.fromkeys(("numba", "cuda", "opencl", "wgsl", "glsl"), "sk_min3({0})")),
    BuiltinSpec("max3", 1, _vec3_only(F32), dict.fromkeys(("numba", "cuda", "opencl", "wgsl", "glsl"), "sk_max3({0})")),
    BuiltinSpec(
        "select",
        3,
        _select,
        {
            "numba": "({1} if {0} else {2})",
            "cuda": "({0} ? {1} : {2})",
            "opencl": "({0} ? {1} : {2})",
            "wgsl": "select({2}, {1}, {0})",
            "glsl": "({0} ? {1} : {2})",
        },
    ),
    BuiltinSpec(
        "bitcast_u32",
        1,
        _fixed((F32,), U32),
        {
            "numba": "sk_bitcast_u32({0})",
            "cuda": "__float_as_uint({0})",
            "opencl": "as_uint({0})",
            "wgsl": "bitcast<u32>({0})",
            "glsl": "floatBitsToUint({0})",
        },
    ),
    BuiltinSpec(
        "bitcast_f32",
        1,
        _fixed((U32,), F32),
        {
            "numba": "sk_bitcast_f32({0})",
            "cuda": "__uint_as_float({0})",
            "opencl": "as_float({0})",
            "wgsl": "bitcast<f32>({0})",
            "glsl": "uintBitsToFloat({0})",
        },
    ),
    BuiltinSpec(
        "reverse_bits",
        1,
        _fixed((U32,), U32),
        {
            "numba": "sk_reverse_bits({0})",
            "cuda": "__brev({0})",
            "opencl": "sk_reverse_bits({0})",
            "wgsl": "reverseBits({0})",
            "glsl": "bitfieldReverse({0})",
        },
    ),
    BuiltinSpec(
        "count_ones",
        1,
        _fixed((U32,), U32),
        {
            "numba": "sk_count_ones({0})",
            "cuda": "(unsigned int)__popc({0})",
            "opencl": "popcount({0})",
            "wgsl": "countOneBits({0})",
            "glsl": "uint(bitCount({0}))",
        },
    ),
)
BUILTINS: dict[str, BuiltinSpec] = {spec.name: spec for spec in SPECS}
