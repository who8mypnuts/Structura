# Getting started

## Install

- **Installers** (Windows, macOS, Linux AppImage/Flatpak) contain everything: no Python needed. The
  installer prepares the render kernels once; otherwise the first start does it in the background.
- **From PyPI:** `pip install structura`, then start `structura-gui` (the app) or `structura` (command line).
  Python 3.12 or newer.

Structura uses your GPU when it can (OpenGL for the viewport; CUDA, OpenCL or Vulkan/Metal/DirectX through
wgpu for rendering) and falls back to all CPU cores otherwise, with the same results. `structura doctor` shows
what was found.

## The window

```
┌ header: build ▶, live build ⚡, seed, views ──────────────────────────────────────────┐
│ Examples │ editor tabs                         │ Viewport | Render                      │
│ Outline  │                                     │                                        │
│ Params   │                                     │                                        │
│ …        │                                     │                                        │
├──────────┴─────────────────────────────────────┴────────────────────────────────────────┤
│ Problems · Console · Build Stats · Timeline · Search                                     │
└ status bar: position, encoding, dialect, objects, build time, preview engine ───────────┘
```

- **Left docks:** Examples, Outline (rules), Parameters (sliders), Variations, Render Settings.
- **Bottom docks:** Problems, Console, Build Stats, Timeline, Search.
- Every command is in the **command palette** (Ctrl+Shift+P). **Quick Open** (Ctrl+P) opens files, examples
  and `@rules`.

## Your first structure

1. **File ▸ New Script** (Ctrl+N) and type:

   ```
   set maxdepth 60
   R1
   rule R1 { { x 1 rz 6 ry 6 s 0.97 hue 4 } R1 box }
   ```

2. With **live build** on (the ⚡ button), the structure appears in the viewport as you type. Otherwise press
   **F5**.
3. Orbit with the left mouse button, pan with the middle one, zoom with the wheel. **View ▸ Frame All** fits
   the structure.
4. Click an object: the editor jumps to the rule call that made it.
5. **Alt+drag** over the `6` after `rz`: dragging left or right changes the number and rebuilds live (Shift =
   fine, Ctrl = coarse; the whole drag is one undo step).
6. **Render ▸ Render** (F9) renders the current view with the path tracer in the **Render** tab. Save it with
   **Render ▸ Save Render…** (PNG, JPEG, WebP, TIFF or EXR; the script is embedded in the image).
7. **Export ▸** writes the structure as OBJ, glTF, USD, STL, 3MF, a Blender script and more.

## Examples

The **Examples** dock lists Structure Synth's classic examples and tutorials and community scripts. Double-click
to open one (use **Save As** to keep your changes elsewhere). **Build ▸ Explore Seed Variations** (Ctrl+Shift+V) shows nine seeds of the current script;
click one to adopt it.

## Projects

A script is a `.es` file. A **project** (`.structura`, **File ▸ Save Project As…**) also keeps the seed, parameter
values, the camera, Render Settings changes, the animation timeline and a thumbnail. The script can be
embedded or linked to an `.es` file next to the project.
