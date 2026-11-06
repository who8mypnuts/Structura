"""Scene-level declarations of EisenScript v2 (docs/05 §9.3–9.5): materials, lights, environment, camera
and render blocks. They travel with the RuleProgram into the SceneIR, so renderers and exporters see them."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .material import Material

Values = dict[str, Any]  # block key → parsed value (float, tuple of floats, colour string, name, bool)


@dataclass(frozen=True)
class LightSpec:
    name: str
    type: str  # sun | sphere | point | spot | rect
    values: Values = field(default_factory=dict)


@dataclass(frozen=True)
class SceneDeclarations:
    materials: dict[str, Material] = field(default_factory=dict)
    lights: tuple[LightSpec, ...] = ()
    environment: Values = field(default_factory=dict)
    camera: Values = field(default_factory=dict)
    render: Values = field(default_factory=dict)

    @property
    def empty(self) -> bool:
        return not (self.materials or self.lights or self.environment or self.camera or self.render)
