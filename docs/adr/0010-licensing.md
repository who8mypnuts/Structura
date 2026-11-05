# ADR-0010: GPL-3.0-or-later; POV-Ray used for ideas only

- Status: Proposed
- Date: planning phase

## Context

- Structure Synth is licensed **LGPL-2.1 or GPL-3** (`LICENSE.README`). Structura's language semantics,
  templates and examples derive from it.
- Sunflow is **MIT**.
- POV-Ray 3.8 source is **AGPL-3**.
- PySide6 is LGPL-3.

## Decision

- License Structura under **GPL-3.0-or-later**. This is compatible with the LGPL/GPL legacy material, MIT
  (Sunflow), Apache-2.0 (OIDN, manifold3d), BSD (numpy, Numba, wgpu) and LGPL (PySide6, ffmpeg LGPL build).
- **POV-Ray: ideas only.** No POV-Ray source is copied or transliterated. Features inspired by POV-Ray are
  implemented from public documentation and the academic literature. Code reviews reject PRs that reference
  POV-Ray source lines.
- All third-party assets (themes, fonts, icons, HDRIs, community scripts) are recorded in
  `THIRD_PARTY_NOTICES.md` before they are bundled.

## Alternatives considered

- **AGPL-3 (to allow POV-Ray code reuse):** would impose network-use obligations on downstream users for little
  gain.
- **MIT/BSD:** incompatible with the LGPL/GPL-derived parts.

## Consequences

- The legal review items are tracked in risk R11. Community sample scripts stay internal until their licence
  is clarified.
