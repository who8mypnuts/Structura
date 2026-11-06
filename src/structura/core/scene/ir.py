"""SceneIR — the immutable struct-of-arrays scene every consumer reads (docs/07-scene-model.md §2).

Row order is emission order. ``xform`` holds the (N, 3, 4) float32 state matrices [L | t] exactly as the
builder had them: the columns are the linear images of the unit axes, and the translation. Structure Synth
handed its renderers *derived* vectors instead (dir_k = M·e_k − M·0, rounded in float32); code that must
reproduce 1.5 output byte for byte uses ``legacy_vectors``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

import numpy as np

from ..lang.compile.setops import SceneEvent
from .declarations import SceneDeclarations


class PrimitiveKind(IntEnum):
    BOX = 0
    SPHERE = 1
    ELLIPSOID = 2
    CYLINDER = 3
    CONE = 4
    TORUS = 5
    LINE = 6
    TUBE = 7
    DOT = 8
    GRID = 9
    MESH = 10
    TRIANGLE = 11
    TEMPLATE = 12  # no geometry: a template::id marker kept in emission order


# legacy primitive index (core.lang.resolve.PRIMITIVE_NAMES order, 8 = triangle) → PrimitiveKind
LEGACY_KIND = np.array(
    [
        PrimitiveKind.BOX,
        PrimitiveKind.SPHERE,
        PrimitiveKind.CYLINDER,
        PrimitiveKind.MESH,
        PrimitiveKind.LINE,
        PrimitiveKind.DOT,
        PrimitiveKind.GRID,
        PrimitiveKind.TEMPLATE,
        PrimitiveKind.TRIANGLE,
    ],
    dtype=np.uint8,
)


def legacy_vectors(xform: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """(base, dir1, dir2, dir3) as Structure Synth 1.5 computed them in float32: M·e_k − M·0."""
    x = np.asarray(xform, np.float32)
    base = x[..., 3]
    dirs = [(x[..., k] + base) - base for k in range(3)]
    return base, dirs[0], dirs[1], dirs[2]


def _frozen(array: np.ndarray) -> np.ndarray:
    array.flags.writeable = False
    return array


@dataclass(frozen=True)
class SceneIR:
    kind: np.ndarray  # uint8[N]  PrimitiveKind
    xform: np.ndarray  # float32[N,3,4]
    rgba: np.ndarray  # float32[N,4] authored sRGB + alpha
    tag: np.ndarray  # int32[N] index into tags
    source: np.ndarray  # int32[N] call-site action id (provenance), -1 for the root
    generation: np.ndarray  # int32[N]
    aux: np.ndarray  # int32[N] row in aux (mesh / triangle) or -1
    aux_data: np.ndarray  # float32[M,13]
    tags: tuple[str, ...]
    events: tuple[tuple[SceneEvent, int, int], ...] = field(
        default_factory=tuple
    )  # (event, generation, emitted-before)
    declarations: SceneDeclarations | None = None  # EisenScript v2 blocks (materials, lights, camera, render)

    def __post_init__(self) -> None:
        for name in ("kind", "xform", "rgba", "tag", "source", "generation", "aux", "aux_data"):
            _frozen(getattr(self, name))

    def __len__(self) -> int:
        return int(self.kind.shape[0])

    @property
    def base(self) -> np.ndarray:
        return self.xform[:, :, 3]

    def subset(self, rows: np.ndarray) -> SceneIR:
        """The scene restricted to ``rows`` (emission order kept; aux rows re-indexed; events dropped)."""
        rows = np.asarray(rows, np.int64)
        aux = self.aux[rows]
        used = aux >= 0
        new_aux = np.full(len(rows), -1, np.int32)
        new_aux[used] = np.arange(int(used.sum()), dtype=np.int32)
        return SceneIR(
            self.kind[rows].copy(), self.xform[rows].copy(), self.rgba[rows].copy(), self.tag[rows].copy(),
            self.source[rows].copy(), self.generation[rows].copy(), new_aux, self.aux_data[aux[used]].copy(),
            self.tags,
            declarations=self.declarations,
        )  # fmt: skip

    def count(self, kind: PrimitiveKind) -> int:
        return int(np.count_nonzero(self.kind == kind))
