"""SceneIR ⇄ .npz (``structura build --dump``, and scenes a '#javascript' script process hands to the
window). The arrays are stored as they are; tags and scene events as text; v2 declarations are not kept."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ..lang.compile.setops import SceneEvent
from .ir import SceneIR

ARRAYS = ("kind", "xform", "rgba", "tag", "source", "generation", "aux", "aux_data")


def save_scene(scene: SceneIR, path: Path, compressed: bool = True) -> None:
    events = json.dumps([[e.key, e.value, g, b] for e, g, b in scene.events])
    save = np.savez_compressed if compressed else np.savez
    save(path, **{k: getattr(scene, k) for k in ARRAYS}, tags=np.array(scene.tags), events=np.array(events))


def load_scene(path: Path) -> SceneIR:
    with np.load(path, allow_pickle=False) as data:
        kind, xform, rgba, tag, source, generation, aux, aux_data = (data[k].copy() for k in ARRAYS)
        tags = tuple(str(t) for t in data["tags"])
        raw = json.loads(str(data["events"])) if "events" in data else []
    events = tuple((SceneEvent(str(k), str(v)), int(g), int(b)) for k, v, g, b in raw)
    return SceneIR(kind, xform, rgba, tag, source, generation, aux, aux_data, tags, events)
