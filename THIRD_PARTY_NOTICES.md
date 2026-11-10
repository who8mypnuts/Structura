# Third-party notices

Structura is MIT licensed. It bundles or depends on the following third-party material.

## Bundled assets

| Component | Location | Licence | Copyright |
|-----------|----------|---------|-----------|
| Structure Synth 1.5 templates & examples (unmodified data) | `src/structura/resources/legacy/` | LGPL-2.1 or GPL-3 | Mikael Hvidtfeldt Christensen (Syntopia) and contributors |
| Structure Synth community code samples | `src/structura/resources/examples/community/` | MIT | Respective authors |
| Inter typeface 4.1 | `src/structura/resources/fonts/Inter*.ttf` | SIL OFL 1.1 | The Inter Project Authors (sources: `fonts/SOURCES.md`, fetched by `tools/fetch_fonts.py`) |
| JetBrains Mono typeface 2.251 | `src/structura/resources/fonts/JetBrainsMono*.ttf` | SIL OFL 1.1 | The JetBrains Mono Project Authors (sources: `fonts/SOURCES.md`) |

## Ported algorithms

| Component | Licence | Notes |
|-----------|---------|-------|
| Sunflow 0.07.3 (Christopher Kulla) | MIT | Renderer architecture and algorithms ported to SKL kernels; the notice is retained in each ported module |
| Mersenne Twister MT19937 (Matsumoto & Nishimura) | BSD-3 | Standard algorithm (`init_genrand`) re-implemented |

## Runtime dependencies (installed, not bundled in source)

PySide6 (LGPL-3), numpy (BSD-3), numba/llvmlite (BSD-2), ModernGL (MIT), wgpu-py (BSD-2), pyopencl (MIT),
pocl (MIT), cuda-python and NVRTC (NVIDIA licence; redistribution per the CUDA EULA), usd-core (modified
Apache-2.0), pygltflib (MIT), manifold3d (Apache-2.0), Pillow (MIT-CMU), OpenEXR (BSD-3), imageio (BSD-2),
imageio-ffmpeg (BSD-2; ffmpeg binaries LGPL), Jinja2 (BSD-3), platformdirs (MIT), tomli-w (MIT), psutil (BSD-3).

**PyMeshLab (GPL-3.0)** — MeshLab's filters as a Python library, used for mesh clean-up and mesh checks on
export (`export/mesh/meshlab.py`). It is a required dependency by the owner's decision (ADR-0010, amendment
1), imported only when a clean-up or check runs; no MeshLab code is copied into Structura, whose own source
stays MIT. Distributions that *bundle* PyMeshLab (the installers) carry GPL-3 software and must meet its terms
for that component (its licence text and an offer of its source). On Linux its wheels need `libOpenGL.so.0`
(`libopengl0`) and glibc ≥ 2.35.

## Theme palettes

The 40 built-in themes reproduce published colour palettes (Nord, Dracula, Solarized, Gruvbox, Catppuccin,
Tokyo Night, One Dark, Ayu, and others). Each theme file in `src/structura/themes/builtin/` records the
palette's author and licence (`author` and `license` keys in `[meta]`); none of the
original editor theme files are copied.

## Algorithms implemented from publications (no code copied)

| Algorithm | Source | Where |
|-----------|--------|-------|
| Edge-avoiding À-Trous wavelet denoising | Dammertz, Sewtz, Hanika, Lensch (HPG 2010) | `render/denoise/atrous.py` |
| Preetham daylight model | Preetham, Shirley, Smits (SIGGRAPH 1999) | `render/environment.py` |
| AgX base view transform | Troy Sobotka (published matrices and fitted curve) | `render/views.py` |
| ACES fitted RRT + ODT | Stephen Hill (public fit) | `render/views.py` |
| Filmic curve | John Hable (public) | `render/views.py` |
| Adaptive sampling with an even-sample half buffer | The approach of Cycles' adaptive sampling (Apache-2.0), re-implemented | `render/film.py` |
| Filter importance sampling | Ernst, Stamminger, Greiner (2006) | `render/filters.py` |
| Integer hash for sample sequences ("lowbias32") | Chris Wellons (public domain) | `render/kernels/sampling.py` |
| Branchless orthonormal basis | Duff et al. (JCGT 2017) | `render/kernels/sampling.py` |

## Optional bundled binaries (installers)

| Component | Licence | Notes |
|-----------|---------|-------|
| Intel Open Image Denoise 2.x (`resources/oidn/`) | Apache-2.0 | Shipped by the installers when present; loaded through ctypes. Without it the À-Trous denoiser is used. |
| ffmpeg (through imageio-ffmpeg) | LGPL-2.1+ | Video encoding for animations |
