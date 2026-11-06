"""SKL type system (docs/11 §3.2).

Scalars (f32, i32, u32, bool), float vectors (vec2..4), unsigned vectors (uvec2..4), user structs, flat
storage buffers (Buf / BufRW of f32 or u32) and fixed-size local arrays. Vectors and structs are immutable
values; only buffers and local arrays are mutable.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class SklType:
    """Base class of all SKL types."""

    name: str = "?"

    def __repr__(self) -> str:
        return self.name


@dataclass(frozen=True, repr=False)
class Scalar(SklType):
    name: str  # "f32" | "i32" | "u32" | "bool"

    @property
    def is_float(self) -> bool:
        return self.name == "f32"

    @property
    def is_int(self) -> bool:
        return self.name in ("i32", "u32")


@dataclass(frozen=True, repr=False)
class Vector(SklType):
    elem: Scalar
    size: int

    @property
    def name(self) -> str:  # type: ignore[override]
        return ("vec" if self.elem.is_float else "uvec") + str(self.size)


@dataclass(frozen=True, repr=False)
class Struct(SklType):
    name: str
    fields: tuple[tuple[str, SklType], ...] = field(default=())

    def field_type(self, name: str) -> SklType | None:
        return dict(self.fields).get(name)

    def field_index(self, name: str) -> int:
        return [n for n, _ in self.fields].index(name)


@dataclass(frozen=True, repr=False)
class Buffer(SklType):
    elem: Scalar
    writable: bool

    @property
    def name(self) -> str:  # type: ignore[override]
        return f"{'BufRW' if self.writable else 'Buf'}[{self.elem.name}]"


@dataclass(frozen=True, repr=False)
class LocalArray(SklType):
    elem: Scalar
    size: int

    @property
    def name(self) -> str:  # type: ignore[override]
        return f"local({self.elem.name}, {self.size})"


@dataclass(frozen=True, repr=False)
class VoidType(SklType):
    name: str = "void"


F32, I32, U32, BOOL = Scalar("f32"), Scalar("i32"), Scalar("u32"), Scalar("bool")
VOID = VoidType()
VEC2, VEC3, VEC4 = Vector(F32, 2), Vector(F32, 3), Vector(F32, 4)
UVEC2, UVEC3, UVEC4 = Vector(U32, 2), Vector(U32, 3), Vector(U32, 4)

NAMED: dict[str, SklType] = {
    "f32": F32,
    "i32": I32,
    "u32": U32,
    "bool": BOOL,
    "None": VOID,
    "vec2": VEC2,
    "vec3": VEC3,
    "vec4": VEC4,
    "uvec2": UVEC2,
    "uvec3": UVEC3,
    "uvec4": UVEC4,
}
COMPONENTS = "xyzw"


def is_numeric(t: SklType) -> bool:
    return (isinstance(t, Scalar) and t.name != "bool") or isinstance(t, Vector)


def elem_of(t: SklType) -> Scalar | None:
    if isinstance(t, Scalar):
        return t
    if isinstance(t, Vector):
        return t.elem
    return None
