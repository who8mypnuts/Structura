"""Render a SceneIR through a 1.5 template: begin, every primitive in emission order, end (docs/15 §5.1).

Each primitive text is compiled once into literal and placeholder segments; per instance only the
placeholders it uses are formatted. Output streams in chunks for progress and cancellation.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from dataclasses import dataclass, field

from ...core.color import parse_color
from ...core.scene.ir import PrimitiveKind as K
from ...core.scene.ir import SceneIR
from .placeholders import UID_PREFIX, VALUES, TemplateCamera, Values, begin_end_values
from .template_file import LegacyTemplate

log = logging.getLogger(__name__)
PLACEHOLDER = re.compile(r"\{[A-Za-z0-9_.]+\}")
KIND_NAMES = {kind: kind.name.lower() for kind in K}  # box, sphere, …, and the v2 cylinder, cone, torus, …
CHUNK = 4096  # primitives per yielded chunk


@dataclass(frozen=True)
class Compiled:
    segments: tuple[str, ...]  # even indices literal, odd indices placeholder names

    @classmethod
    def of(cls, text: str) -> Compiled:
        parts: list[str] = []
        pos = 0
        for m in PLACEHOLDER.finditer(text):
            parts += [text[pos : m.start()], m.group(0)]
            pos = m.end()
        parts.append(text[pos:])
        return cls(tuple(parts))

    @property
    def uses(self) -> frozenset[str]:
        return frozenset(self.segments[1::2])

    def render(self, values: Values) -> str:
        out = list(self.segments)
        for k in range(1, len(out), 2):
            out[k] = values.get(out[k], out[k])  # unknown placeholders stay as written, like QString::replace
        return "".join(out)


@dataclass
class TemplateExport:
    template: LegacyTemplate
    camera: TemplateCamera = field(default_factory=TemplateCamera)
    background: tuple[float, float, float] = (0.0, 0.0, 0.0)  # before the script's 'set background'
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._compiled = {name: Compiled.of(text) for name, text in self.template.primitives.items()}
        self._missing: set[str] = set()
        self._uid = 0

    def _exists(self, name: str) -> bool:
        if name in self._compiled:
            return True
        if name not in self._missing:
            self._missing.add(name)
            self.warnings.append(f"Template error: the primitive '{name}' is not defined.")
            log.warning(self.warnings[-1])
        return False

    def _frame_text(self, name: str, background: tuple[float, float, float]) -> str:
        if not self._exists(name):
            return ""
        return self._compiled[name].render(begin_end_values(self.camera, background))

    def _primitive(self, scene: SceneIR, i: int) -> str:
        kind = KIND_NAMES[K(int(scene.kind[i]))]
        if kind == "cylinder" and scene.declarations is None:
            return ""  # a v1 cylinder: Structure Synth 1.5 never handed it to a template (byte-identical output)
        tag = scene.tags[int(scene.tag[i])]
        name = kind + (f"::{tag}" if tag else "")
        if not self._exists(name):
            return ""
        compiled = self._compiled["mesh" if kind == "mesh" else name]  # 1.5 always uses the untagged mesh text
        if kind == "template":
            return compiled.render({})
        values = VALUES[kind](scene, i)
        if "{uid}" in compiled.uses:
            values["{uid}"] = f"{UID_PREFIX[kind]}{self._uid}"
            self._uid += 1
        return compiled.render(values)

    def chunks(self, scene: SceneIR) -> Iterator[str]:
        background = self.background
        yield self._frame_text("begin", background)
        events = [(ev.value, before) for ev, _gen, before in scene.events if ev.key == "background"]
        parts: list[str] = []
        for i in range(len(scene)):
            parts.append(self._primitive(scene, i))
            if len(parts) >= CHUNK:
                yield "".join(parts)
                parts = []
        yield "".join(parts)
        for value, _ in events:  # the last executed 'set background' is what end() sees
            c = parse_color(value)
            if c is not None:
                background = (round(c.r / 257) / 255, round(c.g / 257) / 255, round(c.b / 257) / 255)
        yield self._frame_text("end", background)

    def render(self, scene: SceneIR) -> str:
        return "".join(self.chunks(scene)).replace("\r", "")
