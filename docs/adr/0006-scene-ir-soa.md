# ADR-0006: Immutable struct-of-arrays SceneIR as the universal scene contract

- Status: Proposed
- Date: planning phase

## Context

Structure Synth used a renderer-visitor interface with three implementations (OpenGL, template, OBJ), each
re-deriving geometry. Structura adds a viewport, two renderer backends and about ten exporters. A visitor
would multiply duplication and per-object Python overhead.

## Decision

The builder emits one **immutable, struct-of-arrays `SceneIR`** ([07](../07-scene-model.md)): instance kind,
3×4 transform, colour, tag, material, provenance and generation, plus aux tables. All consumers read arrays;
there are no callbacks.

## Alternatives considered

- **Visitor/renderer interface (1.5 style):** per-object virtual calls in Python are too slow, and
  duplicated.
- **Pre-tessellated triangle soup:** very large memory footprint; loses analytic primitives and instancing.

## Consequences

- Zero-copy paths to the GPU, Numba and exporters; trivially thread-safe.
- Tessellation is a shared, lazy service for the consumers that need triangles.
- Emission order is preserved for template compatibility.
