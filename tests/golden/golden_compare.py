"""Compare Structura's builder output with Structure Synth 1.5 golden dumps (docs/18 §3).

Our SceneIR rows are converted back into the renderer calls Structure Synth made (sphere centre/radius,
line end points, mesh frames, …) and interleaved with the scene events the dump records, so record indices
line up with the (possibly sampled) golden files.
"""

from __future__ import annotations

import json
import lzma
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from structura.core.build.api import build_scene
from structura.core.color import parse_color
from structura.core.errors import BuildError
from structura.core.lang.api import compile_script
from structura.core.lang.diagnostics import ParseError
from structura.core.scene.ir import PrimitiveKind as K
from structura.core.scene.ir import SceneIR, legacy_vectors

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "tests/golden/data"
ABS_TOL, REL_TOL = 2e-5, 1e-4
DUMPED_EVENTS = {"background", "translation", "rotation", "pivot", "scale", "perspective-angle"}
NAMES = {
    K.BOX: "box",
    K.GRID: "grid",
    K.SPHERE: "sphere",
    K.LINE: "line",
    K.DOT: "dot",
    K.MESH: "mesh",
    K.TRIANGLE: "triangle",
    K.TEMPLATE: "template",
}


@dataclass(frozen=True)
class Outcome:
    ok: bool
    message: str = ""


def _v(a: np.ndarray) -> list[float]:
    return [float(x) for x in a]


def _record(scene: SceneIR, i: int) -> dict[str, object]:
    kind = K(int(scene.kind[i]))
    base, d1, d2, d3 = legacy_vectors(scene.xform[i])
    rec: dict[str, object] = {"t": NAMES[kind], "cls": scene.tags[int(scene.tag[i])]}
    if kind != K.TEMPLATE:
        rec["rgb"], rec["a"] = _v(scene.rgba[i, :3]), float(scene.rgba[i, 3])
    aux = scene.aux_data[scene.aux[i]] if scene.aux[i] >= 0 else None
    centre = base + 0.5 * (d1 + d2 + d3)
    if kind in (K.BOX, K.GRID):
        rec.update(base=_v(base), d1=_v(d1), d2=_v(d2), d3=_v(d3))
    elif kind == K.SPHERE:
        rec.update(c=_v(centre), r=float(np.linalg.norm(0.5 * d3)))
    elif kind == K.LINE:
        start = base + 0.5 * d2 + 0.5 * d3
        rec.update({"from": _v(start), "to": _v(start + d1)})
    elif kind == K.DOT:
        rec.update(pos=_v(centre))
    elif kind == K.MESH and aux is not None:
        rec.update(
            sb=_v(aux[0:3]),
            sd1=_v(aux[3:6]),
            sd2=_v(aux[6:9]),
            eb=_v(base),
            ed1=_v(d1),
            ed2=_v(d2),
            prgb=_v(aux[9:12]),
            pa=float(aux[12]),
        )
    elif kind == K.TRIANGLE and aux is not None:
        rec.update(p1=_v(aux[0:3]), p2=_v(aux[3:6]), p3=_v(aux[6:9]))
    return rec


def _event_record(key: str, value: str) -> dict[str, object]:
    if key == "background":
        c = parse_color(value)
        assert c is not None
        return {"ev": "background", "rgb": [c.r / 65535, c.g / 65535, c.b / 65535]}
    numbers = [float(p) for p in value.replace("[", "").replace("]", "").split(" ")]
    name = {"perspective-angle": "fov"}.get(key, key)
    if key == "rotation":
        return {"ev": "rotation", "m": numbers}
    return {"ev": name, "v": numbers if len(numbers) > 1 else numbers[0]}


def merged_sequence(scene: SceneIR) -> list[tuple[str, int, object]]:
    """[(kind, index, payload)]: primitives interleaved with dumped events in execution order."""
    events = [(ev, before) for ev, _gen, before in scene.events if ev.key in DUMPED_EVENTS]
    seq: list[tuple[str, int, object]] = []
    e = 0
    for i in range(len(scene)):
        while e < len(events) and events[e][1] <= i:
            seq.append(("ev", e, events[e][0]))
            e += 1
        seq.append(("prim", i, None))
    seq.extend(("ev", k, events[k][0]) for k in range(e, len(events)))
    return seq


def _close(a: object, b: object) -> bool:
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_close(x, y) for x, y in zip(a, b, strict=True))
    if isinstance(a, float | int) and isinstance(b, float | int):
        return abs(a - b) <= ABS_TOL + REL_TOL * max(abs(a), abs(b))
    return a == b


def _diff(ours: dict[str, object], gold: dict[str, object]) -> str:
    for key, value in gold.items():
        if key == "i":
            continue
        if key not in ours or not _close(ours[key], value):
            return f"{key}: ours={ours.get(key)} golden={value}"
    return ""


def load_golden(script_id: str, seed: int) -> tuple[dict[str, object], list[dict[str, object]]]:
    with lzma.open(DATA / script_id / f"seed{seed}.jsonl.xz", "rt", encoding="utf-8") as fh:
        header = json.loads(fh.readline())
        return header, [json.loads(line) for line in fh]


def _build(path: Path, seed: int) -> SceneIR | str:
    try:
        compiled = compile_script(path.read_text(encoding="utf-8", errors="replace"), seed, script_dir=path.parent)
        return build_scene(compiled.program, seed).scene
    except (ParseError, BuildError) as exc:
        return f"error: {exc}"


def compare(script_id: str, seed: int) -> Outcome:
    header, golden = load_golden(script_id, seed)
    meta = header["meta"]
    result = _build(ROOT / str(header["script"]), seed)
    if isinstance(result, str):
        return Outcome(meta.get("error") is not None, f"{result} | golden error: {meta.get('error')}")
    if meta.get("error") is not None:
        return Outcome(False, f"golden failed ({meta['error']}) but we built {len(result)} objects")
    seq = merged_sequence(result)
    if len(seq) != header["count"]:
        return Outcome(False, f"record count: ours={len(seq)} golden={header['count']}")
    for gold in golden:
        kind, index, payload = seq[int(gold["i"])]
        ours = _record(result, index) if kind == "prim" else _event_record(payload.key, payload.value)  # type: ignore[union-attr]
        problem = _diff(ours, gold)
        if problem:
            return Outcome(False, f"record {gold['i']}: {problem}")
    return Outcome(True)
