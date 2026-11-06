<p align="center">
  <img src="src/structura/resources/brand/png/structura-logo-on-light@2x.png" alt="Structura" width="420">
</p>

**Structura** is a studio for grammar-based 3D structures. It succeeds
[Structure Synth](http://structuresynth.sourceforge.net/) and is rewritten in Python with PySide6. It has:

- **EisenScript**, 1.5-compatible: builds, template exports and OBJ exports are verified against
  Structure Synth 1.5 itself. There is also an opt-in **v2** dialect with materials, lights, camera and
  render blocks, `( expressions )`, `#param` sliders and animation.
- A code editor with:
  - semantic highlighting, completion with docs, signature help, hover (including rule probabilities) and inlay hints;
  - go to definition, rename and format;
  - number scrubbing (Alt+drag), colour swatches, and 61 snippets;
  - 40 themes (6 Nord variants), plus VS Code and base16 import.
- Two render engines:
  - the **preview engine** (GLSL: instancing, sphere impostors, SSAO, shadows, order-independent
    transparency, picking with jump-to-source, accumulation AA), with a CPU fallback;
  - the **precision engine** (Sunflow-derived path tracing: principled BSDF, MIS sun, point/sphere/spot
    lights, Structure Synth's classic look). One kernel source runs on **CUDA, OpenCL, WGSL and the CPU
    (Numba)**.
- Exports: OBJ (+MTL), PLY, STL (with a watertight union), 3MF (colour printing), glTF/GLB (optionally
  `EXT_mesh_gpu_instancing`), USD/USDZ (instanced), X3D, VRML97, a Blender script, and every Structure
  Synth render template (byte-identical to 1.5).

![Structura](docs/screenshots/window-nord.png)

## Install and run

Python 3.12. Every dependency is required, so all features work the same everywhere.

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e ".[dev]"
.venv/bin/structura-gui                      # the studio (or: python -m structura)
```

### Troubleshooting

- **First launch is slow** (up to a minute): Numba compiles the builder and renderer kernels once, then
  caches them.
- **No 3D viewport / "CPU preview" badge:** the viewport needs desktop OpenGL 3.3. Structura probes the
  driver before creating the window and falls back to the CPU preview, logging one line that explains why.
  Run `structura doctor` from your desktop session to see every OpenGL format tried and the result, and
  include its output in bug reports.
- **Force a backend:** `STRUCTURA_PREVIEW=cpu structura-gui`, or `gpu` to try OpenGL even when the probe
  failed.
- **Linux, Wayland:** if OpenGL fails under Wayland but works under X11 (some NVIDIA setups), run through
  XWayland with `QT_QPA_PLATFORM=xcb structura-gui`.
- **Linux, X11:** Qt ≥ 6.5 needs `libxcb-cursor0` (Debian/Ubuntu: `sudo apt install libxcb-cursor0`).

## Command line

```bash
structura lint   spiral.es                                # diagnostics with line:column
structura build  spiral.es --seed 3                       # object counts and stats
structura render spiral.es -o spiral.png --samples 256 --integrator path --device auto
structura render legacy.es -o legacy.png --integrator classic       # the Structure Synth 1.5 look
structura export spiral.es -o spiral.usdz                 # .obj .ply .stl .glb .usd[a|c|z] .py .pov .sc …
structura export spiral.es -o spiral.stl --option watertight=true --option unit_scale=10
structura animate anim.es -o frames/f.png --frames 0:96 --video anim.mp4    # v2: frame, time, fps
structura run "JavaScript - Movie.es" --limit 10          # Structure Synth '#javascript' scripts
structura doctor                                          # Qt platform, OpenGL and compute devices
```

Devices: `auto` picks CUDA, then an OpenCL GPU, then a wgpu GPU, then the multithreaded CPU backend.

## Python API

```python
import structura.api as st

scene = st.build("spiral.es", seed=3)
st.render(scene, "spiral.png", samples=128, integrator="path")
st.export(scene, "spiral.glb")
```

## EisenScript v2 in one example

```
#version 2
#param arms int = 6 range 3..12
material gilded { preset gold roughness 0.2 }
light lamp { type sphere position [2 4 3] radius 0.4 power 600 }
environment { type gradient top #9bd bottom #fff }
camera { position [0 6 14] target [0 0 0] fov 40 }
render { integrator path samples 256 size 1280x720 }

arms * { ry (360 / arms) } 1 * { x 2 } arm
rule arm md 12 { { y 0.45 rz (6 + 4 * sin(time * 90)) s 0.92 } arm  { s 0.8 } box::gilded }
```

## Development

```bash
.venv/bin/pytest -m "not golden"              # unit, parity, render, preview, UI (offscreen)
.venv/bin/pytest -m golden                    # compatibility with Structure Synth 1.5 (943 cases)
.venv/bin/pytest -m gpu                       # on a machine with an NVIDIA GPU (reference: GTX 1660)
.venv/bin/ruff check src tests tools && .venv/bin/mypy && .venv/bin/lint-imports && .venv/bin/python tools/check_sizes.py
```

The plan, design and status are in [`docs/`](docs/README.md). [`docs/PROGRESS.md`](docs/PROGRESS.md) is
the running log.

## Licence

MIT. See [LICENSE](LICENSE) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). The bundled legacy
examples and templates keep their original licences ([resources/legacy](src/structura/resources/legacy)).
