# Third-party notices

Structura is MIT licensed. It bundles or depends on the following third-party material.

## Bundled assets

| Component | Location | Licence | Copyright |
|-----------|----------|---------|-----------|
| Structure Synth 1.5 templates & examples (unmodified data) | `src/structura/resources/legacy/` | LGPL-2.1 or GPL-3 | Mikael Hvidtfeldt Christensen (Syntopia) and contributors |
| Structure Synth community code samples | `src/structura/resources/examples/community/` | MIT | Respective authors |
| Inter typeface | `src/structura/resources/fonts/Inter*.ttf` | SIL OFL 1.1 | The Inter Project Authors |
| JetBrains Mono typeface | `src/structura/resources/fonts/JetBrainsMono*.ttf` | SIL OFL 1.1 | The JetBrains Mono Project Authors |

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
