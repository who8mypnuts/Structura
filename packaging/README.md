# Packaging Structura (docs/03 §1, docs/18 §10)

Installers bundle Python, every dependency and the Numba caches into one folder, then wrap it per platform.
Everything here runs from the project root with the project's virtual environment.

| Target | Tooling | Command | Output |
|--------|---------|---------|--------|
| App folder (all platforms) | PyInstaller ≥ 6.10 (one-folder) | `python packaging/build.py` | `dist/Structura/` |
| Linux AppImage | appimagetool | `packaging/linux/build_appimage.sh` | `dist/Structura-x86_64.AppImage` |
| Linux Flatpak | flatpak-builder | `flatpak-builder build packaging/linux/io.github.structura.Structura.yml` | repo / bundle |
| Windows installer | Inno Setup 6 | `iscc packaging/windows/structura.iss` | `dist/Structura-Setup.exe` |
| macOS disk image | `hdiutil`, `codesign`, `notarytool` | `packaging/macos/build_dmg.sh` | `dist/Structura.dmg` |
| PyPI wheel | `python -m build` | `python -m build` | `dist/structura-*.whl` |

## What `build.py` does

1. Runs PyInstaller with `packaging/pyinstaller/structura.spec`: two executables (`Structura` for the GUI
   and `structura` for the command line) sharing one folder, with the resources, themes, catalogues,
   Jinja templates and the i18n catalogues as data.
2. Runs `structura warmup` from the bundle, so the first start compiles nothing. The kernels are cached in
   the user's cache folder (`NUMBA_CACHE_DIR`, set in `structura/__init__.py` for frozen apps).
3. Smoke test: `structura --version`, `structura doctor`, and a 32×24 headless render.

## PyMeshLab (GPL-3.0)

PyMeshLab is a required dependency (mesh clean-up and Check Mesh; ADR-0010 amendment 1) and is bundled like
every other dependency. Its Linux wheels need glibc ≥ 2.35 and `libOpenGL.so.0` on the target system: the
AppImage must either bundle `libOpenGL.so.0` (from libglvnd) or list `libopengl0` as a requirement; the
Flatpak runtime provides it. Because PyMeshLab is GPL-3, each installer must carry its licence text and an
offer of its source (put both in the installer's `licenses/` folder). To ship an installer without it, add
`pymeshlab` to `excludes` in `packaging/pyinstaller/structura.spec`; clean-up and Check Mesh then say that
PyMeshLab is unavailable.

## Open Image Denoise

Put the OIDN 2.x shared libraries (`OpenImageDenoise*`, `tbb*`) into `src/structura/resources/oidn/` before
building. The build copies them as data, and `render/denoise/oidn.py` finds them there. Without them the
bundled À-Trous denoiser is used.

## Not verified in the sandbox

The sandbox that produced these files has no PyInstaller, Windows, macOS or signing identities. The owner
runs each target once on its platform (release checklist, docs/18 §10); signing identities go in the
environment variables the scripts name.
