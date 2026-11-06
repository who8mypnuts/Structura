"""Build the Structura app folder with PyInstaller, warm its kernels and smoke-test it (packaging/README.md)."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist" / "Structura"
SMOKE = "set background #223\n{ color #f80 } sphere\n"


def run(*args: str | Path) -> None:
    print("$", " ".join(map(str, args)), flush=True)
    subprocess.run([str(a) for a in args], check=True, cwd=ROOT)


def cli() -> Path:
    name = "structura.exe" if sys.platform == "win32" else "structura"
    app = DIST.parent / "Structura.app" / "Contents" / "MacOS" / name
    return app if app.exists() else DIST / name


def main() -> int:
    run(sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", ROOT / "packaging/pyinstaller/structura.spec")
    run(cli(), "--version")
    run(cli(), "warmup")
    run(cli(), "doctor")
    with tempfile.TemporaryDirectory() as tmp:
        script = Path(tmp) / "smoke.es"
        script.write_text(SMOKE)
        run(cli(), "render", script, "-o", Path(tmp) / "smoke.png", "--size", "32x24", "--samples", "2", "--device", "cpu")
    print(f"built {DIST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
