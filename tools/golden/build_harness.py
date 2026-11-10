"""Build the golden-dump harness against the original Structure Synth 1.5 sources (test tooling only).

Copies the legacy model/parser sources into tools/golden/build/src, overlays OpenGL-free header stubs and
compiles everything with g++ against Qt 5.15 headers extracted into tools/golden/qt (see README.md).

    python tools/golden/build_harness.py                                # sample_source/…-r312-trunk
    python tools/golden/build_harness.py --source DIR --label "1.5.0"   # e.g. the 1.5.0 release tarball
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LEGACY = ROOT / "sample_source/structuresynth-code-r312-trunk"
BUILD = HERE / "build"
SRC = BUILD / "src"
QT_INC = HERE / "qt/usr/include/x86_64-linux-gnu/qt5"
QT_LIB_EXTRA = HERE / "qt/usr/lib/x86_64-linux-gnu"
SYS_LIB = Path("/usr/lib/x86_64-linux-gnu")
EXE = BUILD / "golden_dump"
LABEL = BUILD / "SOURCE"  # which Structure Synth the harness was built from (generate.py writes it to the manifest)

SOURCES = [
    *[
        f"StructureSynth/Model/{n}.cpp"
        for n in (
            "Action",
            "AmbiguousRule",
            "Builder",
            "ColorPool",
            "CustomRule",
            "ExecutionStack",
            "PrimitiveClass",
            "PrimitiveRule",
            "RandomStreams",
            "Rule",
            "RuleRef",
            "RuleSet",
            "State",
            "Transformation",
            "TransformationLoop",
        )
    ],
    "StructureSynth/Model/Rendering/TemplateRenderer.cpp",
    "StructureSynth/Model/Rendering/ObjRenderer.cpp",
    "StructureSynth/Parser/Preprocessor.cpp",
    "StructureSynth/Parser/Tokenizer.cpp",
    "StructureSynth/Parser/EisenParser.cpp",
    "SyntopiaCore/Logging/Logging.cpp",
    "SyntopiaCore/Math/Matrix4.cpp",
    "SyntopiaCore/Math/Vector3.cpp",
    "SyntopiaCore/Math/Random.cpp",
    "SyntopiaCore/Misc/ColorUtils.cpp",
    "SyntopiaCore/Misc/MiniParser.cpp",
    "golden_dump.cpp",
]
QT_MODULES = ("QtCore", "QtGui", "QtWidgets", "QtXml")


def copy_sources(legacy: Path) -> None:
    """Copies the Structure Synth sources the harness needs, with the stubbed GL engine and the dump program.

    Args:
        legacy: The Structure Synth source tree.
    """
    if SRC.exists():
        shutil.rmtree(SRC)
    for tree in ("StructureSynth", "SyntopiaCore", "ThirdPartyCode"):
        shutil.copytree(legacy / tree, SRC / tree)
    shutil.rmtree(SRC / "SyntopiaCore/GLEngine")
    shutil.copytree(HERE / "harness/stubs/SyntopiaCore/GLEngine", SRC / "SyntopiaCore/GLEngine")
    shutil.copy(HERE / "harness/golden_dump.cpp", SRC / "golden_dump.cpp")


def compile_one(rel: str) -> Path:
    obj = BUILD / "obj" / (rel.replace("/", "_") + ".o")
    obj.parent.mkdir(parents=True, exist_ok=True)
    includes = [f"-I{SRC}", f"-I{QT_INC}"] + [f"-I{QT_INC / m}" for m in QT_MODULES]
    cmd = ["g++", "-std=c++17", "-O2", "-fPIC", "-w", "-DQT_NO_DEBUG", *includes, "-c", str(SRC / rel), "-o", str(obj)]
    subprocess.run(cmd, check=True)
    return obj


def link(objects: list[Path]) -> None:
    libs = [f"-l:libQt5{m[2:]}.so.5" for m in QT_MODULES]
    cmd = [
        "g++",
        "-o",
        str(EXE),
        *map(str, objects),
        f"-L{SYS_LIB}",
        f"-L{QT_LIB_EXTRA}",
        *libs,
        f"-Wl,-rpath,{QT_LIB_EXTRA}",
    ]
    subprocess.run(cmd, check=True)


def main() -> int:
    """Builds the golden harness from a Structure Synth source tree (its label goes into the manifest).

    Returns:
        The exit code (1 when the Qt 5 headers are missing).
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=LEGACY, help="a Structure Synth source tree")
    parser.add_argument("--label", default="r312", help="its version, recorded in the golden manifest")
    args = parser.parse_args()
    if not QT_INC.exists():
        print("Qt 5 headers missing: see tools/golden/README.md", file=sys.stderr)
        return 1
    copy_sources(args.source)
    with ThreadPoolExecutor() as pool:
        objects = list(pool.map(compile_one, SOURCES))
    link(objects)
    LABEL.write_text(args.label, encoding="utf-8")
    print(f"built {EXE} from Structure Synth {args.label}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
