"""Public SKL authoring API (docs/11 §3).

Kernel modules import their vocabulary from here::

    from structura.kernels.skl import func, kernel, struct, f32, u32, vec3, uvec3, Buf, BufRW, dot, select

The decorators only *tag* objects; the SKL compiler reads the functions' source through ``ast``. The type
names and builtins below exist so that kernel modules are ordinary, importable Python.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SklMeta:
    kind: str  # "func" | "kernel" | "struct"
    workgroup: tuple[int, int, int] = (8, 8, 1)
    exact: bool = False


def func[F: Callable[..., Any]](fn: F | None = None, *, exact: bool = False) -> Any:
    """Mark a device function. ``exact=True`` forbids fast-math contractions (geometry code)."""

    def mark(f: F) -> F:
        f.__skl__ = SklMeta("func", exact=exact)  # type: ignore[attr-defined]
        return f

    return mark(fn) if fn is not None else mark


def kernel[F: Callable[..., Any]](workgroup: tuple[int, int, int] = (8, 8, 1)) -> Callable[[F], F]:
    """Mark a compute entry point; its first parameter is ``gid: uvec3``."""

    def mark(f: F) -> F:
        f.__skl__ = SklMeta("kernel", workgroup=workgroup)  # type: ignore[attr-defined]
        return f

    return mark


def struct[T](cls: type[T]) -> type[T]:
    cls.__skl__ = SklMeta("struct")  # type: ignore[attr-defined]
    return cls


def bufset[T](cls: type[T]) -> type[T]:
    """A named group of buffer parameters, passed around as one argument (docs/11 §3.2).

    The front end expands a ``scene: SceneBufs`` parameter into the individual buffers (named after the
    fields), rewrites ``scene.prim_f`` to ``prim_f`` and expands ``scene`` in call arguments. The IR and the
    emitted code only ever see plain buffer parameters.
    """
    cls.__skl__ = SklMeta("bufset")  # type: ignore[attr-defined]
    return cls


class _TypeName:
    def __init__(self, name: str) -> None:
        self.name = name

    def __call__(self, *args: Any) -> Any:  # casts / constructors are only meaningful to the compiler
        raise RuntimeError(f"SKL {self.name}(...) is compiled, not executed directly")

    def __getitem__(self, item: Any) -> _TypeName:
        return _TypeName(f"{self.name}[{getattr(item, 'name', item)}]")


f32, i32, u32 = _TypeName("f32"), _TypeName("i32"), _TypeName("u32")
vec2, vec3, vec4 = _TypeName("vec2"), _TypeName("vec3"), _TypeName("vec4")
uvec2, uvec3, uvec4 = _TypeName("uvec2"), _TypeName("uvec3"), _TypeName("uvec4")


class Buf[T]:
    """Read-only flat storage buffer (f32 or u32)."""


class BufRW[T]:
    """Read-write flat storage buffer (f32 or u32)."""


def _builtin(name: str) -> Callable[..., Any]:
    def stub(*args: Any) -> Any:
        raise RuntimeError(f"SKL builtin {name}() is compiled, not executed directly")

    stub.__name__ = name
    return stub


_BUILTINS = [
    "abs",
    "min",
    "max",
    "clamp",
    "sqrt",
    "sin",
    "cos",
    "tan",
    "asin",
    "acos",
    "atan",
    "atan2",
    "exp",
    "log",
    "pow",
    "floor",
    "ceil",
    "fract",
    "trunc",
    "mix",
    "dot",
    "cross",
    "length",
    "normalize",
    "min3",
    "max3",
    "select",
    "bitcast_u32",
    "bitcast_f32",
    "reverse_bits",
    "count_ones",
    "fmod",
    "local",
]
globals().update({name: _builtin(name) for name in _BUILTINS})
INF = 3.0e38
PI = 3.14159265358979

__all__ = [  # noqa: RUF022 - grouped: API, types, builtins
    "INF",
    "PI",
    "Buf",
    "BufRW",
    "SklMeta",
    "bufset",
    "f32",
    "func",
    "i32",
    "kernel",
    "struct",
    "u32",
    "uvec2",
    "uvec3",
    "uvec4",
    "vec2",
    "vec3",
    "vec4",
    "abs",
    "min",
    "max",
    "clamp",
    "sqrt",
    "sin",
    "cos",
    "tan",
    "asin",
    "acos",
    "atan",
    "atan2",
    "exp",
    "log",
    "pow",
    "floor",
    "ceil",
    "fract",
    "trunc",
    "mix",
    "dot",
    "cross",
    "length",
    "normalize",
    "min3",
    "max3",
    "select",
    "bitcast_u32",
    "bitcast_f32",
    "reverse_bits",
    "count_ones",
    "fmod",
    "local",
]
