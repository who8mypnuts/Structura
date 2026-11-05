# ADR-0009: USD export via usd-core

- Status: Proposed
- Date: planning phase

## Context

The brief requires USD export. Useful USD output needs `.usdc`/`.usdz`, PointInstancer, UsdShade materials
and UsdLux lights.

## Decision

Use Pixar's **`usd-core`** wheel. The default is instanced export through `UsdGeomPointInstancer`, with
per-instance `displayColor` and UsdPreviewSurface materials that read it. A flattened mode and the shear
policies are described in [15](../15-export.md) §2.2 and §4.1.

## Alternatives considered

- **Hand-written `.usda`:** no binary crate, no usdz, fragile, and unvalidated.

## Consequences

- A large wheel (tens of MB). Its licence is a modified Apache-2.0; legal review is tracked under risk R11.
- We can validate our own output with `Usd.Stage.Open` and `usdchecker` in CI.
