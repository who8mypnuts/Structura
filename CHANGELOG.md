# Changelog

All notable changes. The format follows [Keep a Changelog](https://keepachangelog.com/); versions follow
semantic versioning. The detailed record, with every deviation from the plan, is [docs/PROGRESS.md](docs/PROGRESS.md).

## [Unreleased] — 0.1.0

The first complete implementation of the plan in [docs/](docs/README.md) (milestones M0–M8, M9 in progress).

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
- Folding, multiple cursors, minimap, sticky scroll, split view, number scrubbing and colour pickers.
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
  compare, region re-render.

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
