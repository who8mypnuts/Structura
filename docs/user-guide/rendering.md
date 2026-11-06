# Rendering

Structura has two engines:

- the **viewport** (OpenGL): instant, interactive, for building and framing. **View ▸ Look** switches
  between Studio, Legacy (Structure Synth's look) and Clay;
- the **precision renderer** in the **Render** tab (F9): a path tracer and three faster integrators on the
  GPU (CUDA, OpenCL or wgpu), or on all CPU cores with the same result.

## The Render view

The tool bar: **Render** (F9), **Stop**, **Save…**, integrator, samples per pixel, device, denoiser, exposure,
view transform, and the channel to show. A render refines progressively; exposure and view transform apply
to the finished image without rendering again.

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
- **Pixel filter** (box, gaussian, Mitchell, Lanczos, …), **aperture** and **blades** for depth of field and
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

## Saving

**Save…** writes PNG, JPEG, WebP, TIFF (display-referred, with the current exposure and view transform) or
EXR (linear, with the channels). PNG and EXR files carry the script, seed, camera and settings, so a render
can be reproduced.
