# Architecture Decision Records

ADRs record significant decisions, the alternatives considered, and their consequences. They are immutable
once *Accepted*. To change a decision, write a new ADR that *supersedes* the old one.

| ADR | Title | Status |
|-----|-------|--------|
| [0001](0001-python-pyside6.md) | Python 3.12 + PySide6 as the application platform | Proposed |
| [0002](0002-gpu-api-wgpu.md) | WebGPU (wgpu-py) as the single GPU API | Proposed |
| [0003](0003-cpu-fallback-numba.md) | Numba for the multithreaded CPU fallback | Proposed |
| [0004](0004-single-source-kernels.md) | SKL: single-source kernels transpiled to WGSL and JIT-compiled by Numba | Proposed (pending spike S1) |
| [0005](0005-builder-numba.md) | Numba-compiled, resumable builder over flat rule tables | Proposed (pending spike S4) |
| [0006](0006-scene-ir-soa.md) | Immutable struct-of-arrays SceneIR as the universal scene contract | Proposed |
| [0007](0007-editor-widget.md) | Custom editor on `QPlainTextEdit` (no QScintilla, no web editor) | Proposed |
| [0008](0008-theme-format.md) | Semantic-role TOML themes with derivation and contrast enforcement | Proposed |
| [0009](0009-usd-usd-core.md) | USD export via `usd-core` | Proposed |
| [0010](0010-licensing.md) | GPL-3.0-or-later; POV-Ray used for ideas only | Proposed |
| [0011](0011-eisenscript-dialects.md) | v1 compatibility by default, opt-in v2 dialect | Proposed |
| [0012](0012-gpu-on-gui-thread.md) | All wgpu calls on the GUI thread via a cooperative scheduler | Proposed (pending spike S6) |

## Template

```markdown
# ADR-NNNN: Title
- Status: Proposed | Accepted | Superseded by ADR-XXXX
- Date: YYYY-MM-DD
## Context
## Decision
## Alternatives considered
## Consequences
```
