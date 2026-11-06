# PyInstaller spec for Structura (one folder, GUI + CLI). Run through packaging/build.py.
# ruff: noqa
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

ROOT = Path(SPECPATH).parents[1]
SRC = ROOT / "src"
PACKAGE = SRC / "structura"

# every non-Python file of the package (resources, themes, catalogues, shaders, templates), at its own path
datas = [(str(p), str(Path("structura") / p.parent.relative_to(PACKAGE)))
         for p in PACKAGE.rglob("*") if p.is_file() and p.suffix not in (".py", ".pyc") and "__pycache__" not in p.parts]
for module in ("pxr", "wgpu", "pyopencl", "imageio_ffmpeg", "OpenEXR"):
    datas += collect_data_files(module)
binaries = collect_dynamic_libs("wgpu") + collect_dynamic_libs("pyopencl") + collect_dynamic_libs("manifold3d")
hidden = collect_submodules("structura") + collect_submodules("pxr") + ["numba.core.typing.cffi_utils"]

analysis = Analysis([str(PACKAGE / "app" / "main.py"), str(PACKAGE / "cli" / "main.py")], pathex=[str(SRC)],
                    datas=datas, binaries=binaries, hiddenimports=hidden, excludes=["tkinter"])
pyz = PYZ(analysis.pure)
icon = str(PACKAGE / "resources" / "brand" / ("structura.icns" if sys.platform == "darwin" else "structura.ico"))
gui = EXE(pyz, analysis.scripts[:1], [], exclude_binaries=True, name="Structura", console=False, icon=icon)
cli = EXE(pyz, analysis.scripts[1:], [], exclude_binaries=True, name="structura", console=True)
folder = COLLECT(gui, cli, analysis.binaries, analysis.datas, name="Structura")
if sys.platform == "darwin":
    app = BUNDLE(folder, name="Structura.app", icon=icon, bundle_identifier="io.github.structura.Structura",
                 info_plist={"NSHighResolutionCapable": True, "CFBundleShortVersionString": "0.1.0",
                             "CFBundleDocumentTypes": [{"CFBundleTypeName": "EisenScript",
                                                        "CFBundleTypeExtensions": ["es", "structura"],
                                                        "CFBundleTypeRole": "Editor"}]})
