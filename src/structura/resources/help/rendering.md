# Rendering

Structura has two engines:

- the **viewport** (OpenGL): instant, interactive, for building and framing. **View ▸ Look** switches
  between Studio, Legacy (Structure Synth's look), Clay and Technical (flat colours with dark edges);
- the **precision renderer** in the **Render** tab (F9): a path tracer and three faster integrators on the
  GPU (CUDA, OpenCL or wgpu), or on all CPU cores with the same result.

## The viewport

- **View ▸ Colour By** shows the structure coloured by how it was made — generation (a colour-blind-safe
  cividis ramp), call site, tag, primitive kind or random — instead of its own colours. Renders and exports
  always use the script's colours.
- **View ▸ Overlays:** a ground grid under the structure (OpenGL viewport), the axis gizmo, the bounding box,
  and the object counts. A warning badge appears while the script has errors: the viewport keeps showing the
  last good build.
- **View ▸ Standard Views** (front, back, left, right, top, bottom, isometric) and the **Camera** panel: the
  camera in numbers (position, target, up, field of view, aperture, focus), saved views, and **Copy to
  Script**, which writes the camera into the script (`set translation/rotation/pivot/scale` in v1 scripts, a
  `camera { }` block in v2).
- The **Inspector** panel describes the object you clicked (kind, generation, tag, colour, position, size,
  the line that made it) and selects everything alike: the same call site, tag, generation or kind.
  **Isolate Selection** hides everything else in the viewport; **View ▸ Show All** brings it back.
- **View ▸ X-Ray** makes the structure see-through in the viewport.
- **View ▸ Rendered View** (Ctrl+Alt+V) path-traces the viewport itself with the script's render settings,
  refining while the camera rests — like Blender's rendered view.
- **Alt+click** a surface to focus the camera there (depth of field in renders); **Shift+F** frames the
  clicked object.
- **Lock to script** (Camera panel) shows the script's own camera after every build.
- **Build ▸ Show Ancestry** (or the Inspector's button) lists how the clicked object was made: the chain of
  rule calls from the top level, each line jumping to its call in the script.
- On a slow GPU the viewport drops ambient occlusion while you move the camera and brings it back when you stop.
- If OpenGL 3.3 is not available, the viewport draws with the render kernels instead (on the GPU when CUDA,
  OpenCL or wgpu is there): the badge says "CUDA preview" or "CPU preview" and a banner explains why once.

## The Render view

The tool bar: **Render** (F9), **Stop**, **Save…**, **Report…**, **A/B** compare, the **preset**, integrator,
samples per pixel, device, denoiser, exposure, view transform, and the channel to show. A render refines
progressively; exposure and view transform apply to the finished image without rendering again.

| Preset | Samples | Long edge | Noise threshold |
|--------|---------|-----------|-----------------|
| Draft | 16 | 960 px | — |
| Standard | 128 | 1280 px | 0.02 |
| Final | 1024 | 1920 px | 0.005 |
| Print 4K | 2048 | 3840 px | 0.003 |

**Stop** pauses a render; **Resume** continues it from the samples it had (the result is the same as an
uninterrupted render). The image keeps the viewport's aspect. Changing the samples by hand switches to **Custom** (the viewport's
size, at most 1280 px). Opening a Structure Synth script with raytracer settings offers, once, to render it
with the **legacy look** (the `classic` integrator) or the modern path tracer; **Render ▸ Render (Legacy
Look)** does it any time. The first picture of a render is a quick blocky preview; it is refined at once.

- **Render ▸ Render Region**, or Shift+drag over the image: only that rectangle renders again.
- **Render ▸ Denoise** denoises the finished render now.
- Renders that would need more than the **memory guard**'s share of the free memory (Preferences ▸
  Rendering) are refused with a message — lower the size or raise the guard.

| Integrator | Use |
|------------|-----|
| `path` | Physically based: global illumination, glass, metals, lights, HDRI and sun-sky, depth of field |
| `ao` | Ambient occlusion: the "white studio" look |
| `classic` | Structure Synth 1.5's raytracer look (Phong, shadows, reflections) |
| `preview` | Fast key light + AO, for thumbnails |

**Render Settings** (left dock) shows every renderer option with the script's values; what you change there
overrides the script for this tab until **Reset to script**. Highlights:

- **Noise threshold** (adaptive sampling): pixels stop once their noise is below it (0.01 is a good final
  value); the **samples** channel shows where the samples went. **Time limit** stops a render after N s.
- **Image sampler:** `progressive` (the whole image gets better pass by pass) or `tiled` — square **buckets**
  rendered one after another, like Sunflow, in the chosen **bucket order** (hilbert, spiral from the centre,
  rows, columns, diagonal, random); the bucket being rendered is marked in the image. Both give the same
  picture.
- **Sample sequence:** `random` (default) or `halton` (Sunflow's quasi-random numbers, for comparisons).
- **Bounces:** `max_bounces`, and separate limits for diffuse, glossy and transmission bounces (−1 = only the
  maximum). **AO: add direct light** lights the `ao` integrator by the sun and the lights too.
- **Pixel filter** (box, gaussian, Mitchell, Lanczos, sinc, …), **aperture** and **blades** for depth of field and
  polygonal bokeh, **camera** type (perspective, orthographic, spherical 360°, fisheye).
- **Environment:** gradient sky, **HDRI** (`.exr` / `.hdr`) with rotation and intensity, or the Preetham
  **sun-sky**.
- **Ground:** a plane under the structure, or a **shadow catcher** (the background stays visible, darkened
  where shadows fall — for compositing).
- **Fog:** density, height falloff and colour.
- **Caustics:** `filtered` (default: smooth, slightly blurred light through glass), `on` (unbiased, noisy),
  or `photons` — sunlight focused by glass and mirrors is traced as photons first, giving sharp caustics
  quickly (`photon_count`, `photon_radius`).
- **View transform:** AgX (default for `path` and `ao`), ACES, Filmic, Standard (default for `classic`),
  Soft.

## Denoising and channels

- **Denoise** runs when a render finishes: Intel Open Image Denoise when it is installed, otherwise the
  built-in À-Trous filter. Change it afterwards to denoise again without rendering.
- **Channels:** beauty, albedo, normal, depth, alpha, instance id, material id, samples. Saving to **EXR**
  writes all of them as layers.

## Materials and lights (v2 scripts)

```
#version 2
material glass  { preset glass }                       // glass, mirror, metal, gold, chrome, matte, plastic,
material lamp   { emission #ffeecc 8 }                 // emissive, clay, ceramic — or any principled values
light key  { type sun direction [-1 -2 -1] intensity 3 angle 0.5 }
light fill { type sphere position [0 8 4] radius 1 power 200 }
light soft { type rect position [0 6 0] target [0 0 0] size [4 2] power 300 }
environment { type hdri file "studio.exr" rotation 90 }
render { integrator path samples 512 noise_threshold 0.01 filter mitchell ground catcher }
{ x 2 } sphere::glass
```

Objects with an emissive material light the scene (and are sampled as lights). A tag named like a preset
(`box::gold`) uses that preset.

The **Materials** panel lists the tags of the built structure and the material each renders with (declared,
a preset named like the tag, or the default). Choose a preset, change colours and values with a live swatch,
and **Write to Script** adds or updates the tag's `material` block. The **Lights** panel lists the `light`
blocks and adds new ones (sun, point, sphere, spot, area) placed around the structure. Both offer to convert a
Structure Synth (v1) script to v2 first; it builds the same.

## Saving

**Save…** (Ctrl+Alt+S) asks for two things in one dialog:

- **Image:** where the image goes (type a path or **Browse…**): PNG, JPEG, WebP, TIFF (display-referred, with
  the current exposure and view transform) or EXR (linear, with the channels);
- **Report:** the render report written **beside the image** — PDF, HTML, Markdown, plain text, JSON, CSV,
  OpenDocument, or no report. It is named after the image (`tree.png` → `tree-report.pdf`); the dialog shows
  the name. Your choice is remembered.

PNG and EXR files carry the script, seed, camera and settings, so a render can be reproduced — **File ▸ Open
from Render…** reopens them.

## Final renders

**Render ▸ Final Render…** (Shift+F9) — and **Render** (F9) whenever the preset is **Final** or **Print 4K** —
opens the same dialog before anything is rendered: pick the **quality** (Final, Print 4K, the other presets, or
Custom for the tool bar's own settings), **where the image is saved**, and the **report** to write beside it.
**Render** starts; when the render (and its denoising) finishes, the image and the report are saved there and
a notice offers **Show in Folder**. **Render Only** renders without saving (use Save… later).

## Render reports

**Report…** (or **Render ▸ Save Render Report…**) writes everything about the render, for your notes, a
client, or a forum post:

- **at a glance:** resolution, objects, samples, time, integrator, device, a preview, the histogram and the
  palette of dominant colours;
- **script:** file, dialect, lines, rule definitions, SHA-256, seed, parameter values;
- **geometry:** objects by kind with triangles if baked, generations, bounding box, extent, density, instance
  size range, mirrored and sheared instances, distinct colours, tags, memory;
- **build:** time, throughput, rule applications, generations against `maxdepth`, objects against
  `maxobjects`, culling;
- **camera:** position, target, direction, heading and pitch, field of view both ways, the 35 mm focal length,
  depth of field;
- **render settings, lighting and environment, and the material table;**
- **image:** exposure, dynamic range in stops, clipped and crushed pixels, samples per pixel (min / mean /
  max), pixels that converged early, **coverage**, how many objects are actually **visible**, depth range;
- **performance:** render and preparation time, samples per second, passes, BVH nodes, leaves, depth and
  memory;
- **system** and a **command line** that renders the same image with `structura render`.

Formats: **PDF**, **HTML** (one file, images inlined, light and dark), **Markdown** (with a preview image
beside it), **plain text**, **JSON** (every value, machine-readable), **CSV** (one row per value) and
**OpenDocument** (`.odt`). Reports are usually written with the image (Save…, Final Render, the queue);
**Report…** writes one on its own, starting beside the image you saved last. `structura render … --report
report.pdf` writes the same report from the command line.

## The render queue

**Render ▸ Add to Render Queue…** (Ctrl+Shift+F9) asks for the image file and the report (the same dialog as
Save…) and queues the current view with the tool bar's settings. Queued renders run one after another while
you keep working, and each is saved when it finishes, with its report beside it. The panel shows progress and time; cancel, remove or show a render in its folder.
