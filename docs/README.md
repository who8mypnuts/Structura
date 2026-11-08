# Structura — Planning Documentation

Structura is a full rewrite of **Structure Synth** (Mikael Hvidtfeldt Christensen, 2007–2010) in Python with PySide6.
It keeps the EisenScript grammar language and adds a GPU-accelerated, Sunflow-derived renderer with a CPU fallback.
It also adds a modern code editor, app-wide theming, and export to mesh, USD, glTF and Blender formats.

This folder started as the **planning set**: what would be built, how, and in what order. The plan has since
been implemented milestone by milestone (M0–M11). [PROGRESS.md](PROGRESS.md) records what was built and every
deviation, and [22-implementation-notes.md](22-implementation-notes.md) gives the status of each milestone, the
refinements of the plan, and what is left (§4: the owner's installers and three deliberate omissions). Documents 00–21 keep the
original plan; where the program differs they carry "As built" notes. The
[user guide](user-guide/README.md) describes the finished program, and [reference/language.md](reference/language.md)
is the generated language reference.

---

## Reading order

| # | Document | Purpose |
|---|----------|---------|
| 00 | [Vision & Scope](00-vision-and-scope.md) | Goals, non-goals, personas, success criteria |
| 01 | [Legacy Analysis](01-legacy-analysis.md) | What Structure Synth, Sunflow and POV-Ray contain; what we keep, fix, drop |
| 02 | [Architecture](02-architecture.md) | Layers, packages, data flow, dependency rules |
| 03 | [Technology Stack](03-technology-stack.md) | Every runtime dependency, why it is required, licences |
| 04 | [Concurrency Model](04-concurrency-model.md) | Threads, Qt signals/slots, jobs, cancellation, GPU scheduling |
| 05 | [EisenScript Language](05-eisenscript-language.md) | Formal spec of v1 (compatible) and v2 (extended) |
| 06 | [Language Engine](06-language-engine.md) | Preprocessor → lexer → parser → resolver → compiler → builder |
| 07 | [Scene Model](07-scene-model.md) | SceneIR (struct-of-arrays), materials, lights, camera, project files |
| 08 | [Preview Engine & Viewport](08-viewport.md) | GLSL/OpenGL viewport with Numba fallback, picking, camera controls |
| 09 | [Precision Render Engine](09-renderer.md) | Sunflow-derived renderer: pipeline, BVH, samplers, film |
| 10 | [Renderer Shading](10-renderer-shading.md) | Integrators, materials, lights, cameras, legacy mapping, POV-Ray ideas |
| 11 | [Compute Backends](11-compute-backends.md) | CUDA, OpenCL, WGSL, GLSL and Numba from a single kernel source (SKL) |
| 12 | [Code Editor](12-editor.md) | Highlighting, completion, diagnostics, typing, live-coding tools |
| 13 | [Theming](13-theming.md) | Theme engine, 40 built-in themes (6 Nord variants), import formats |
| 14 | [UI / UX](14-ui-ux.md) | Window layout, panels, workflows, shortcuts, accessibility |
| 15 | [Export Pipeline](15-export.md) | OBJ/PLY/STL/3MF/glTF/USD/X3D, Blender script, templates, images, video |
| 16 | [Animation, Scripting & CLI](16-animation-scripting-cli.md) | Timeline, legacy `#javascript`, Python API, headless CLI |
| 17 | [Code Standards & Repository Layout](17-code-standards-and-layout.md) | DRY rules, size limits, typing, full package tree |
| 18 | [Testing & Quality](18-testing-and-quality.md) | Golden compat corpus, render regression, kernel parity, CI |
| 19 | [Roadmap](19-roadmap.md) | Phases, milestones, acceptance criteria |
| 20 | [Risks](20-risks.md) | Risk register and mitigations |
| 21 | [Brand & Logo](21-brand-and-logo.md) | Logo concept, construction, colours, usage |
| 22 | [Implementation Notes](22-implementation-notes.md) | Milestone status, where the code refines or departs from the plan, owner checks, and the backlog |
| — | [Progress Log](PROGRESS.md) | What has been executed so far, and what is next |
| — | [Architecture Decision Records](adr/README.md) | The key decisions and their alternatives |

## Non-negotiable principles (from the project brief)

1. **Python + PySide6.** All additional dependencies are **required**, not optional. Every user on Windows,
   macOS and Linux gets the same features.
2. **DRY.** Every concept has exactly one implementation. This applies even to GPU and CPU kernels; see
   [11](11-compute-backends.md) for how.
3. **Small units.** Files, classes and functions stay small and reviewable. The limits are in
   [17](17-code-standards-and-layout.md) and CI enforces them.
4. **GPU acceleration is a must.** There are two engines ([ADR-0013](adr/0013-two-render-engines.md)):
   - the **preview engine**: GLSL/OpenGL viewport, with a Numba fallback;
   - the **precision engine**: CUDA, OpenCL, WGSL (wgpu) or CPU, from one kernel source.
5. **Multithreaded CPU fallback is essential.** Every GPU feature has a multithreaded CPU path that gives the
   same results.
6. **Non-blocking.** The GUI thread never waits on work. All long-running work is a *Job* that reports through
   Qt signals/slots ([04](04-concurrency-model.md)).

## Glossary

| Term | Meaning |
|------|---------|
| **EisenScript** | The rule-based language of Structure Synth (`.es` files). |
| **v1 / compat mode** | EisenScript exactly as Structure Synth 1.5 interprets it, including quirks. |
| **v2** | Opt-in extended dialect (`#version 2`): materials, lights, camera blocks, expressions, includes. |
| **Rule** | A named production; several rules with the same name form an *ambiguous* (weighted random) rule. |
| **Action** | A statement inside a rule: optional transformation loops followed by a rule reference, or a `set`. |
| **State** | Current transform matrix + HSV colour + alpha + per-rule depth counters + seed. |
| **Builder** | The expansion engine that turns a rule set into primitives. |
| **SceneIR** | The struct-of-arrays scene produced by the builder and consumed by every other subsystem. |
| **Tag / class** | The `::name` suffix on a primitive (`box::shiny`), used to select materials. |
| **SKL** | *Structura Kernel Language*: a restricted, typed Python subset. Numba JIT-compiles it for the CPU; Structura transpiles it to WGSL for the GPU. |
| **Job** | A cancellable unit of background work with progress/partial/finished/failed signals. |
| **Provenance** | The link from every generated primitive back to the rule/action/source span that created it. |
| **spp** | Samples per pixel. |
| **AOV** | Arbitrary output variable (albedo, normal, depth, object id…). |

## Source material analysed

| Path | What it is |
|------|------------|
| `sample_source/structuresynth-code-r312-trunk` | Structure Synth SVN r312, the **canonical** legacy source (1.5.0 "Hinxton" + later fixes) |
| `sample_source/StructureSynth-orig`, `Structure-Synth` | Near-identical mirrors (Structure-Synth also holds `Misc/` templates, tutorials, roadmap) |
| `sample_source/StructureSynth-code-samples` | 117 community `.es` scripts (MIT), used in the compatibility corpus and bundled as examples |
| `sample_source/sunflow` | Sunflow 0.07.3 (Java, MIT), the **basis of the built-in renderer** |
| `sample_source/povray` | POV-Ray 3.8 (C++, **AGPL-3**). Used **for ideas only**; no code is ported (see ADR-0010) |

**Licence:** Structura is **MIT** ([ADR-0010](adr/0010-licensing.md)).
