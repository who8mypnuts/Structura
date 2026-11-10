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
┌ header: build ▶, live build ⚡, seed, workspace, render, frame, command palette ──────────────┐
│ rail │ side panel   │ editor tabs (or the welcome page)   │ Viewport | Render                     │
│  ▤   │ (one at a    │                                     │                                       │
│  ☰   │  time)       │                                     │                                       │
│  …   │              │                                     │                                       │
├──────┴──────────────┴─────────────────────────────────────┴───────────────────────────────────────┤
│ Problems · Console · Build Stats · Timeline · Search · Render Queue                                │
└ status bar: position, encoding, dialect, objects, build time, preview engine ─────────────────────┘
```

- **Welcome page:** while no script is open, the editor area offers New, Open, the examples, your recent
  files, four theme previews, and the render device Structura found.
- **Activity rail** (the icon strip on the far left): each icon opens one side panel — Files, Examples,
  Outline, Parameters, Camera, Inspector, Materials, Lights, Variations, Render Settings. Only one is open at
  a time, at full size; click the open panel's icon again to collapse the side bar. Hover an icon for its
  name and shortcut. **View ▸ Panels** lists every panel, including the hidden **Activity** panel (all
  background jobs).
- **Bottom panels:** Problems, Console, Build Stats, Timeline, Search, Render Queue and History, as tabs along
  the top of the panel.
- **Workspaces** (the button in the header, or Ctrl+1 … Ctrl+3): **Code** (wide editor, Problems),
  **Explore** (large viewport, Parameters) and **Render** (the Render tab, Render Settings). Each remembers
  how you arranged it. **Present** (Ctrl+4) shows only the image, full screen; Esc returns. **View ▸
  Workspace ▸ Reset Layout** puts every panel back.
- Every command is in the **command palette** (Ctrl+Shift+P). **Quick Open** (Ctrl+P) opens files, examples
  and `@rules`.
- Short notices (a saved file, a finished export) appear as **toasts** at the bottom right, with **Show in
  Folder**. **File ▸ Preferences ▸ Reduce motion** turns their fades off.

## Your first structure

1. **File ▸ New Script** (Ctrl+N) and type:

   ```
   set maxdepth 60
   R1
   rule R1 { { x 1 rz 6 ry 6 s 0.97 hue 4 } R1 box }
   ```

2. With **live build** on (the ⚡ button), the structure appears in the viewport as you type. Otherwise press
   **F5**.
3. Orbit with the left mouse button, pan with the middle or the right one, zoom with the wheel; Alt+right
   drag looks around, and W A S D / Q E fly while the viewport has the focus. **Shift** slows any of these to
   a quarter, **Ctrl** keeps a drag on one axis, and **View ▸ Orbit Lock** does that permanently. A
   **right-click** opens the viewport menu: framing, standard views, looks, overlays, the orbit lock and the
   mouse layout (Structura, Structure Synth or Blender). **View ▸ Frame All** fits the structure.
4. Click an object: the editor jumps to the rule call that made it.
5. **Alt+drag** over the `6` after `rz`: dragging left or right changes the number and rebuilds live (Shift =
   fine, Ctrl = coarse; the whole drag is one undo step).
6. **Render ▸ Render** (F9) renders the current view with the path tracer in the **Render** tab. Save it with
   **Render ▸ Save Render…** (PNG, JPEG, WebP, TIFF or EXR; the script is embedded in the image), and keep a
   detailed **render report** with **Render ▸ Save Render Report…** (PDF, HTML, Markdown, text, JSON, CSV or
   ODT).
7. **File ▸ Export As…** (Ctrl+E) or **Export ▸** writes the structure as OBJ, glTF, USD, STL, 3MF, a Blender
   script and more. A Save As dialog asks where; the next dialog shows the full path, what is in the file and
   the format's options.

## Your first v2 scene: materials, light and a lens

**File ▸ New v2 Script** (Ctrl+Alt+N) starts from a small EisenScript v2 scene with a material, glass, a sun,
a sky and a ground. v2 adds blocks for what Structure Synth left to the renderer:

```
#version 2
material glass { preset glass  attenuation_color #7fd0ff  attenuation_distance 3 }
light sun { type sun  direction [-0.5 -0.9 -0.35]  intensity 3 }
environment { type sunsky  sun sun }
camera { position [6 4 10]  target [0 1 0]  lens 50mm  fstop 2.8  focus auto }
render { integrator path  samples 256  ground plane  look subtle }
{ y 1 s 2 } sphere::glass
{ x 2.5 y 0.5 } cylinder
```

- `#version 2` must be the first line (anything before it keeps the script v1; warning W116 offers to move it).
- The **Materials** and **Lights** panels write these blocks for you (Lights ▸ **Lighting Rig** sets up a
  whole studio); the **Camera** panel's lens editor writes the `camera` block.
- v2 adds `cylinder`, `cone[r]`, `torus[r]`, `ellipsoid` and `tube[r]`; `( expressions )` with `rand(a, b)`;
  and typed `#param` sliders. See [Writing scripts](writing-scripts.md) and the
  [language reference](language.md).

## Examples

The **Examples** panel is a gallery of **Structura v2** showcase scenes (glass, neon and bloom, every
primitive, depth of field, a studio rig, a sunset city), Structure Synth's classic examples and tutorials and
the community scripts, with a thumbnail of each (rendered once in the background and cached). Search by name or pick a
group. Double-click to open a **copy** — the bundled file stays untouched; **Save As** offers its name.

**Build ▸ Explore Seed Variations** (Ctrl+Shift+V) shows nine seeds of the current script; click one to adopt
it. Switch the Variations panel to **Parameters** to vary the `#define` sliders instead; right-click a cell ▸
**Expand Around This** explores closer around it. **Build ▸ Take Snapshot** (Ctrl+Alt+H) keeps the script, seed, parameters and camera in the **History**
panel with a thumbnail; double-click a snapshot to go back to it (one undo step).

## Projects

A script is a `.es` file. A **project** (`.structura`, **File ▸ Save Project As…**) also keeps the seed, parameter
values, the camera, Render Settings changes, the animation timeline and a thumbnail. The script can be
embedded or linked to an `.es` file next to the project. Saved views (Camera panel) are kept in projects too.

**File ▸ Open from Render…** reopens the script, seed, parameters, camera and render settings stored in a PNG
or EXR that Structura rendered. The **Files** panel does the same when you double-click a render.

## Where files go

Save As dialogs never start in the program's folder. Each kind of file (scripts, projects, exports, renders,
reports) starts where you last saved that kind, else next to the current script, else in a **Structura**
folder in your Documents (Pictures for renders).
