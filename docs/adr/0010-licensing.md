# ADR-0010: MIT licence; clean re-implementation of Structure Synth; POV-Ray for ideas only

- Status: **Accepted** (project owner decision)
- Supersedes: the earlier "GPL-3.0-or-later" proposal

## Context

| Source | Licence | How Structura may use it |
|--------|---------|--------------------------|
| Structure Synth 1.5 (C++) | LGPL-2.1 **or** GPL-3 (`LICENSE.README`) | Behaviour may be re-implemented. Code may **not** be translated into MIT code. |
| Structure Synth `Misc/*.rendertemplate`, `Examples/*.es` | LGPL-2.1/GPL-3 (as part of Structure Synth) | Redistributed **unchanged** as separately licensed data (aggregation) |
| StructureSynth-code-samples (community scripts) | **MIT** (confirmed by the project owner) | Bundled with attribution |
| Sunflow 0.07.3 | MIT | Code may be ported directly, with its copyright notice kept in `THIRD_PARTY_NOTICES.md` |
| POV-Ray 3.8 | AGPL-3 | Ideas only; no code |
| Qt / PySide6 | LGPL-3 | Dynamically used library; no Qt code copied (this matters for `QColorCompat`) |

## Decision

1. **Structura is licensed MIT.**
2. **Clean re-implementation rule.** The Structure Synth behaviour captured in the specification
   ([05](../05-eisenscript-language.md), [06](../06-language-engine.md)) is implemented **from the spec**.
   Contributors must not translate C++ functions line by line.
   - Matching observable behaviour (output structures, RNG order, quirks) is interoperability, not copying.
     The golden suite checks behaviour, never source similarity.
   - Where the spec needs a precise formula (for example the HSV conversion), the formula is written down in
     the spec in mathematical form and implemented from that.
3. **Legacy data** (templates, 1.5 examples) lives in `resources/legacy/` with its own `LICENSE-LEGACY.txt`
   (LGPL-2.1/GPL-3 text). It is shipped as unmodified data files that Structura reads. It is not linked code.
4. **Golden generator** (`tools/golden/`) compiles the original GPL/LGPL C++ for *testing only*. It is never
   part of the Structura distribution, and the folder carries its own licence notice.
5. **QColorCompat** is implemented from documented Qt behaviour and **verified** against PySide6 at test time.
   No Qt source is copied.
6. **POV-Ray: ideas only**, from public documentation and papers.
7. **Third-party runtime dependencies** must be MIT-compatible for distribution:
   - BSD, MIT, Apache-2.0 and LGPL (dynamically linked) are allowed.
   - NVIDIA redistributables (NVRTC) follow the CUDA EULA redistribution terms. Their notice must be in
     `THIRD_PARTY_NOTICES.md`.

## Consequences

- Structura can be freely reused, including commercially.
- Reviewers reject PRs whose code is visibly transliterated from `sample_source/structuresynth-*`.
- Sunflow code may be ported directly, which speeds up the renderer. Sunflow's MIT notice must be retained.

## Amendment 1 (owner review): PyMeshLab is a required dependency

- Status: **Accepted** (project owner decision), with the consequences below for the owner to confirm.
- Context: MeshLab integration (mesh clean-up presets on export, Check Mesh, `.mlp` projects) uses PyMeshLab,
  which is **GPL-3.0**. Rule 7 above allows only MIT-compatible runtime dependencies *for distribution*.
- Decision: PyMeshLab is listed in `dependencies` (every install has the same features). Structura's code
  stays MIT: it calls PyMeshLab's public API, imports it lazily (only when a clean-up or check runs), and
  copies no MeshLab code.
- Consequences:
  - `pip install structura` resolves PyMeshLab as a separate package; nothing GPL is in Structura's wheel.
  - **Installers bundle it**, so the installer as a distribution contains GPL-3 software: ship PyMeshLab's
    licence text and a written offer (or link) for its corresponding source with each installer. If that is
    not acceptable for a target, exclude PyMeshLab from that installer (`packaging/pyinstaller/structura.spec`
    `excludes`); clean-up and Check Mesh then report that PyMeshLab is unavailable, everything else works.
  - The owner should have this reviewed before the first public installer release (docs/18 §10 checklist).
