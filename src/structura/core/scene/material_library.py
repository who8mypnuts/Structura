"""Resolve every tag of a scene to a material (docs/07 §3, legacy keys docs/05 §6.3).

Index 0 is the *default* material used by untagged primitives. Like Structure Synth 1.5, untagged
primitives get 'set raytracer::phong|reflection', tagged ones get 'set raytracer::TAG::phong|reflection'
(each tag starts from the 0.6/0.6/0.6 defaults, not from the default class).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

import numpy as np

from .material import Material, legacy_phong, legacy_reflection, presets


@dataclass(frozen=True)
class MaterialTable:
    materials: tuple[Material, ...]
    by_tag: np.ndarray  # int32[len(tags)]: material index of each tag

    def __len__(self) -> int:
        return len(self.materials)


def _numbers(value: str) -> list[float]:
    return [float(p) for p in value.replace(",", " ").split()]


def _apply_legacy(material: Material, prop: str, value: str) -> Material:
    if prop not in ("reflection", "phong"):
        return material
    try:
        numbers = _numbers(value)
    except ValueError:
        return material  # malformed values are reported by the linter
    if prop == "reflection" and numbers:
        return legacy_reflection(material, numbers[0])
    if prop == "phong" and len(numbers) >= 3:
        return legacy_phong(material, *numbers[:3])
    return material


def _start(tag: str, declared: Mapping[str, Material], tag_presets: bool) -> Material:
    if tag in declared:
        return declared[tag]
    if tag_presets and tag in presets():
        return presets()[tag]
    return Material(name=tag or "default")


def resolve_materials(
    tags: tuple[str, ...],
    raytracer: Iterable[tuple[str, str]],
    declared: Mapping[str, Material] | None = None,
    tag_presets: bool = False,
) -> MaterialTable:
    """One material per tag; raytracer keys are (key without 'raytracer::', value) in execution order."""
    known = declared or {}
    materials = {tag: _start(tag, known, tag_presets) for tag in tags}
    for key, value in raytracer:
        tag, _, prop = key.lower().rpartition("::")
        if tag in materials:
            materials[tag] = _apply_legacy(materials[tag], prop, value)
    unique: dict[Material, int] = {}
    by_tag = np.array([unique.setdefault(materials[t], len(unique)) for t in tags], np.int32)
    return MaterialTable(tuple(unique), by_tag)
