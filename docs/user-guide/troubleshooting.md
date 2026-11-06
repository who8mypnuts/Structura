# Troubleshooting

## Start with `structura doctor`

It prints the Qt platform, each OpenGL configuration tried (and why one failed), and the compute devices
(CUDA, OpenCL, wgpu, CPU) with their names.

## The viewport says "CPU preview"

OpenGL 3.3 could not be used (old driver, remote desktop, some Wayland/EGL setups). Structura then draws the
viewport on the CPU instead of failing. Update the graphics driver, or force a platform:
`QT_QPA_PLATFORM=xcb structura-gui` on Linux. **Preferences ▸ Viewport** chooses `gpu`, `cpu` or `auto`.

## Renders use the CPU

The Render tab's **device** list shows what is available; `auto` picks CUDA, then OpenCL, then wgpu, then the
CPU. NVIDIA GPUs need a driver with CUDA 12 support; AMD and Intel GPUs work through OpenCL or wgpu. The CPU
renderer produces the same image, only slower.

## The first build or render is slow

The kernels are compiled once (about a minute) and cached. Installers do this during installation; otherwise
it happens in the background at the first start. `structura warmup` does it explicitly. If a cache ever gets
stale (for example after an upgrade), delete the `structura` folder in your user cache directory.

## Denoising is "À-Trous", not Open Image Denoise

Open Image Denoise is used when its library is available: installers bundle it; with pip, set
`STRUCTURA_OIDN=/path/to/libOpenImageDenoise.so` (or `.dll` / `.dylib`). The built-in À-Trous filter is used
otherwise.

## Large structures

- The viewport handles millions of instances on a recent GPU. Lines and grids cost more than boxes.
- `set maxobjects` caps a runaway script; the Build Stats dock shows counts and timings.
- Renders of huge scenes need GPU memory; the CPU renderer uses system memory instead.

## Reporting a problem

**Help ▸ About** shows the version. Include the output of `structura doctor` and, if possible, the script.
