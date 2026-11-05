# ADR-0008: Semantic-role TOML themes with derivation and contrast enforcement

- Status: Proposed
- Date: planning phase

## Context

We need about 40 built-in themes that apply across the whole app (chrome, editor, viewport overlays, icons),
plus user themes and imports.

## Decision

Themes are **TOML files mapping semantic roles to colours** ([13](../13-theming.md)). Missing roles are derived
in OKLCH, and contrast is enforced automatically. One `ThemeService` generates the QPalette, QSS (from one
template), editor formats, icon tints and viewport colours. Importers exist for VS Code JSON and base16/base24.

## Alternatives considered

- **Hand-written QSS per theme:** 40 large files, no syntax roles, and massive duplication.
- **Per-widget colour settings:** not DRY; inconsistent results.

## Consequences

- Adding a theme takes about 30 lines of TOML.
- Screenshot and contrast tests cover every theme.
