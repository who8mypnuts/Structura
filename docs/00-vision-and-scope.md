# 00 — Vision & Scope

## 1. Vision

> **Structura is a modern, beautiful studio for grammar-based 3D fractal structures. You write a few lines of
> EisenScript, see millions of objects appear instantly, render them photorealistically inside the app, and
> send them to any 3D pipeline.**

Structure Synth showed that a few recursive rules can produce remarkable structures. What held it back was
everything around the language:

- a frozen GUI during builds,
- a fixed-function OpenGL preview,
- a basic Phong raytracer,
- export that required hand-editing XML templates and installing Java and Sunflow.

Structura keeps the language and modernises everything else.

## 2. Goals

| ID | Goal | Measured by |
|----|------|-------------|
| G1 | **Faithful compatibility.** Every Structure Synth 1.5 script builds the same structure. | All 156 unique `.es` files in the corpus match golden output ([18](18-testing-and-quality.md)) |
| G2 | **Instant feedback.** Live rebuild while typing. | 100k objects rebuilt and on screen in < 300 ms on the reference machine |
| G3 | **Scale.** Interactive viewport with very large structures. | 60 fps at 1M instances, 30 fps at 5M on the reference GPU |
| G4 | **Built-in photoreal rendering.** Sunflow-class GI (path tracing, AO, sun-sky, IBL, glass, DOF). | Feature matrix in [10](10-renderer-shading.md) complete; first progressive frame < 100 ms |
| G5 | **GPU-first, CPU-always.** GPU acceleration everywhere, with a multithreaded CPU fallback that gives the same image. | Kernel parity suite passes on both backends |
| G6 | **Modern editor.** Highlighting, completion, diagnostics, hover docs, typing aids, snippets, live tweaking. | Feature checklist in [12](12-editor.md) |
| G7 | **Beautiful and themeable.** App-wide themes: 6 Nord variants and 34 other schemes (40 total). | Themes in [13](13-theming.md) |
| G8 | **Open export.** OBJ, PLY, STL, 3MF, glTF/GLB, USD (a/c/z), X3D, Blender script, legacy templates. | All exporters round-trip through validators |
| G9 | **Never block.** The GUI thread stays responsive during build, render and export. | UI-stall watchdog in CI: no event-loop stall > 50 ms |
| G10 | **Maintainable.** DRY, small modules, typed, tested. | CI gates in [17](17-code-standards-and-layout.md) and [18](18-testing-and-quality.md) |

## 3. Non-goals (for 1.0)

| Non-goal | Rationale |
|----------|-----------|
| General-purpose 3D modelling (vertex editing, sculpting) | Structura is a generative tool; use Blender downstream. |
| FBX / Alembic writers | No open, redistributable FBX SDK exists. USD and glTF cover the same pipelines, and Blender converts them. |
| Hardware ray-tracing cores (RTX/Metal RT) | WebGPU does not expose them. Compute-shader BVH traversal is fast enough for our scenes. Revisit after 1.0. |
| Spectral rendering, volumetric heterogeneous media, SSS | Listed as post-1.0 ideas from POV-Ray ([10](10-renderer-shading.md) §8). |
| Running the original C++ | Structura is a rewrite. The original C++ is used only to generate golden test data. |
| Networked or distributed rendering | Out of scope. The CLI supports batch rendering on a farm. |
| Mobile or web builds | Desktop only (Windows 10+, macOS 12+, major Linux distributions with Vulkan). |

## 4. Personas

| Persona | Needs | Key features |
|---------|-------|--------------|
| **Returning Structure Synth artist** | Open old `.es` files and get the same output; nicer renders without Sunflow/Java setup. | Compat mode, built-in renderer, legacy `set raytracer::*` support, legacy templates. |
| **Generative-art newcomer** | A gentle learning curve and fast experimentation. | Examples gallery, completion with docs, live rebuild, number scrubbing, variation explorer. |
| **3D pipeline user** (Blender/Houdini/Unreal/Omniverse) | Clean geometry with materials and instancing. | USD PointInstancer, glTF `EXT_mesh_gpu_instancing`, Blender script, watertight STL/3MF. |
| **Educator** | Visualise recursion and L-system-like ideas. | Provenance picking (click an object to jump to the rule), generation slider, outline view. |
| **Batch / farm user** | Headless animation and batch rendering. | CLI, Python API, legacy `#javascript` movies. |

## 5. Product pillars

1. **Language.** EisenScript v1, exactly compatible, plus an opt-in v2 with materials, lights, camera and
   expressions ([05](05-eisenscript-language.md)).
2. **Engine.** A Numba-compiled builder that streams primitives into a struct-of-arrays SceneIR
   ([06](06-language-engine.md), [07](07-scene-model.md)).
3. **See.** A WebGPU viewport with instancing, sphere impostors, SSAO, shadows and picking
   ([08](08-viewport.md)).
4. **Render.** A Sunflow-derived progressive and final renderer on GPU and CPU ([09](09-renderer.md)–[11](11-compute-backends.md)).
5. **Write.** A modern code editor with a language service ([12](12-editor.md)) and theming ([13](13-theming.md)).
6. **Ship.** Exporters for meshes, scenes, images and video ([15](15-export.md)); animation, scripting and CLI
   ([16](16-animation-scripting-cli.md)).

## 6. Success criteria for 1.0

- All goals G1–G10 met on the reference platforms below.
- Zero P0/P1 bugs open; crash-free sessions ≥ 99.5% in beta telemetry (opt-in only).
- Documentation: user guide, language reference (generated from the same tables the editor uses), and
  developer guide.
- Signed installers for Windows (MSIX/MSI), macOS (notarised DMG, universal2), and Linux (AppImage + Flatpak),
  plus `pip install structura`.

### Reference platforms (for performance budgets)

| Class | CPU | GPU | Notes |
|-------|-----|-----|-------|
| Reference | 8-core x86-64 (2021+) or Apple M1 | NVIDIA RTX 3060 / AMD RX 6600 / Apple M1 (8-core GPU) | All budgets are quoted against this class |
| Minimum | 4-core x86-64 or Apple M1 | Any Vulkan 1.1 / Metal 2 / DX12 GPU, **or none** | With no GPU, the CPU fallback must stay usable (see [08](08-viewport.md) §9) |

## 7. Naming

- Product: **Structura**. Python package: `structura`. CLI: `structura`.
- Native project file: `.structura`. EisenScript files keep `.es`.
- The renderer is called **Structura Render** in the UI; internally it is `structura.render`.
