# Troubleshooting

## Start with `structura doctor`

It prints the Qt platform, each OpenGL configuration tried (and why one failed), whether PyMeshLab and Open
Image Denoise load, and the compute devices (CUDA, OpenCL, wgpu, CPU) with their names.

## Mesh clean-up says "PyMeshLab is unavailable"

PyMeshLab (mesh clean-up and Check Mesh) needs, on Linux, the system's `libOpenGL.so.0`: install
`libopengl0` (Debian/Ubuntu) or `libglvnd` (Fedora, Arch). Its wheels also need glibc 2.35 or newer. Every
other feature works without it.

## The viewport says "CUDA preview" or "CPU preview"

The interactive OpenGL viewport could not get an OpenGL 3.3 context. Common causes are an old driver, a remote
desktop, or some Wayland/EGL setups. Structura then draws the viewport with the render kernels instead of
failing: on a GPU (CUDA, OpenCL or wgpu) when one is available, otherwise on the CPU.

- **Linux, Wayland.** When native Wayland gives no desktop OpenGL, Structura restarts itself once on XWayland
  and remembers the choice if that works. To force it, start with `QT_QPA_PLATFORM=xcb structura-gui`.
- **Check what works.** `structura doctor` shows each attempt, including the XWayland one.
- **Override the choice.** `STRUCTURA_PREVIEW=gpu|cpu|off` sets the preview mode.
  `STRUCTURA_PREVIEW_DEVICE=cuda|opencl|wgpu|cpu` picks the device of the compute preview.

## Renders use the CPU

The Render tab's **device** list shows what is available; `auto` picks CUDA, then OpenCL, then wgpu, then the
CPU. NVIDIA GPUs need a driver with CUDA 12 support; AMD and Intel GPUs work through OpenCL or wgpu. The CPU
renderer produces the same image, only slower.

## Clearing the caches

**Preferences ▸ Advanced ▸ Clear Caches** deletes the compiled kernels, CUDA binaries and thumbnails; they
are made again when next needed (`structura warmup` compiles the kernels ahead of time). **Reset Window
Layout** puts every panel back where it started.

## The first build or render is slow

The kernels are compiled once (about a minute) and cached. Installers do this during installation; otherwise
it happens in the background at the first start, for the CPU and for the render device. CUDA machine code is
cached too, so only the first render on a machine (or after an update) waits for the CUDA compiler.
`structura warmup` (and `structura warmup --device cuda`) does it explicitly. If a cache ever gets
stale (for example after an upgrade), delete the `structura` folder in your user cache directory.

## Denoising is "À-Trous", not Open Image Denoise

Open Image Denoise is used when its library is available: installers bundle it; with pip, set
`STRUCTURA_OIDN=/path/to/libOpenImageDenoise.so` (or `.dll` / `.dylib`). The built-in À-Trous filter is used
otherwise.

## Large structures

- The viewport handles millions of instances on a recent GPU. Lines and grids cost more than boxes.
- `set maxobjects` caps a runaway script; **Build ▸ Build Limits…** caps every build (objects, time, memory).
  The Build Stats dock shows counts and the time each phase took.
- Renders of huge scenes need GPU memory; the CPU renderer uses system memory instead.

## The Examples gallery shows grey tiles

Thumbnails are rendered once, one at a time in the background, and cached (in the `structura/thumbnails`
folder of your user cache directory). The first time, the gallery fills in over a minute or two. With
`STRUCTURA_PREVIEW=off` no thumbnails are made.

## Where did my file go?

Save As dialogs start in the folder last used for that kind of file, else next to the script, else in
*Documents/Structura* (*Pictures/Structura* for renders). The toast after saving has **Show in Folder**, and
the Console logs every path written.

## Structura crashed — where is my work?

- **Recovery:** a few seconds after every edit (and every minute — Preferences ▸ General) Structura writes a
  recovery snapshot of every open tab: the unsaved text, parameters, render overrides, camera, saved views and
  timeline. If Structura did not close cleanly, the next start offers to restore it. Declined it by mistake?
  **File ▸ Recover ▸ Restore Declined Recovery**.
- **Backups:** before a script is overwritten, the version on disk is copied to the backups folder (the last
  20 of each file): **File ▸ Recover ▸ Open Backups Folder**.
- **Internal errors** do not close the window: a banner says what happened (**Details**, **Copy Report**) and
  a recovery snapshot is written at once. Everything is logged in `logs/structura.log` in Structura's data
  folder; a hard crash (a driver, a kernel) leaves the traceback of every thread in `logs/crash.log`.

## Reporting a problem

**Help ▸ About** shows the version. **Help ▸ System Report…** shows what `structura doctor` finds (Qt
platform, OpenGL, compute devices) with a **Copy** button: include it and, if possible, the script. A
**render report** (Render ▸ Save Render Report…, or `structura render … --report report.txt`) records the
settings, the device and the system in one file; **Render ▸ Copy Report as Markdown** copies it for a post.
The error banner's **Copy Report** includes the traceback, the log folder and the system details.
