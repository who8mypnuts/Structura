# Changelog

All notable changes. The format follows [Keep a Changelog](https://keepachangelog.com/); versions follow
semantic versioning. The detailed record, with every deviation from the plan, is [docs/PROGRESS.md](docs/PROGRESS.md).

## [Unreleased] — 0.1.0

The first complete implementation of the plan in [docs/](docs/README.md) (milestones M0–M8 and M10; M9 waits
on the owner's platform checks).

### Window and workflow (M10)

- An activity rail: one readable side panel at a time (Files, Examples, Outline, Parameters, Camera,
  Inspector, Materials, Lights, Variations, Render Settings); bottom panels with tabs on top.
- Workspaces (Code, Explore, Render, Present) that remember their layouts; Reset Layout.
- A welcome page; toasts with Show in Folder; banners; an Activity panel of background jobs.
- An Examples gallery with cached thumbnails; examples open as copies.
- Save As dialogs everywhere, starting in remembered folders (never the program's folder).
- File ▸ Export As… with every format, an export sheet (destination, contents, presets, options), export
  presets shared with `structura export --preset`, and template 'runAfter' commands (after confirmation).
- File ▸ Open from Render: reopen the script and settings stored in a PNG or EXR.

### Language

- EisenScript 1.5, compatible: the golden corpus (154 scripts × 4 seeds) builds bit-identical structures.
  Template and OBJ exports are byte-identical to Structure Synth 1.5.
- EisenScript v2 (`#version 2`):
  - material, light, environment, camera and render blocks;
  - `( expressions )` with `frame` / `time` / `fps`, and `#param` sliders;
  - `mat` inheritance;
  - cylinder, cone, torus, ellipsoid and tube;
  - whole-word defines.
- `structura convert --to v2`, and Edit ▸ Convert to EisenScript v2.
- `#javascript` movie scripts through QJSEngine (`structura run`, F7).

### Editor

- Semantic highlighting, completion, signature help, hover and inlay hints.
- Diagnostics with quick fixes, rename, format, peek and references.
- Folding, multiple cursors, minimap, sticky scroll, split view and number scrubbing.
- A colour picker on right-click (live preview, one undo step, the literal's style kept) and a context menu
  with the language commands.
- Every broken rule is reported at once (a recovering parser for the editor).
- Snippets with tab stops.
- Sessions with crash recovery.
- 40 themes with a theme editor, keymap presets and an editor for them.

### Rendering

- A GLSL preview with a CPU fallback, and an OpenGL probe that avoids invisible windows.
- Precision engine from one kernel source on CUDA, OpenCL, WGSL and Numba:
  - path, AO, classic and preview integrators with a principled BSDF;
  - sun, point, sphere, spot and rect lights, and emissive geometry;
  - HDRI and Preetham sun-sky environments;
  - perspective, orthographic, spherical and fisheye cameras, with bokeh;
  - eight pixel filters, adaptive sampling and AOVs;
  - denoising with OIDN or À-Trous;
  - ground and shadow catcher, fog, and photon-mapped caustics;
  - AgX, ACES and filmic view transforms.
- Render view: live exposure and view transform, channels, denoise, zoom and pan, pixel inspector, A/B
  compare, region re-render, presets (Draft, Standard, Final, Print 4K), and a render queue.
- Render reports (PDF, HTML, Markdown, text, JSON, CSV, ODT) with geometry, camera, settings, image
  statistics, visible objects, BVH and performance figures; `structura render --report`.
- Viewport: colour-by modes, a ground grid, a technical look, gizmo/bounds/HUD overlays, navigation presets
  (Structura, Structure Synth 1.5, Blender) with a fly mode, standard views, animated camera moves, the Camera
  panel with saved views and Copy Camera to Script, the Inspector, CPU picking in the compute preview and
  Alt+click focus.
- The GPU viewport works on NVIDIA under Wayland (desktop OpenGL requested explicitly; XWayland fallback); the
  no-OpenGL fallback draws on the GPU with CUDA/OpenCL/wgpu. CUDA kernels are cached as machine code, and
  render passes are paced by GPU time.

### Animation

- A timeline with keyed parameters, seed and camera; scrubbing and playback.
- Render Animation to image sequences and MP4, WebM or GIF; `structura animate` reads projects.

### Export

- OBJ, PLY, STL (watertight), 3MF (instanced), glTF/GLB (optional GPU instancing), USD/USDZ (instanced,
  flattened or matrix policy), X3D, VRML97, and a Blender script (meshes or Geometry Nodes).
- POV-Ray 3.8, Sunflow and Mitsuba 3 scenes, and the 1.5 render templates.
- CSG markers evaluated with manifold3d.

### Platform

- A non-blocking GUI (job lanes, fair parallel sections, banded dispatch) with a UI-stall watchdog.
- Kernel warm-up, i18n (German and a pseudo-locale) and accessible names.
- Packaging scripts for Windows, macOS and Linux; CI workflows; a user guide.
- CLI: `theme list/check/import`, `devices`, `template`, and `structura FILE` to open the app.
