"""The Python API (docs/16 §4): `import structura as st`, documents, animation, and `structura run x.py`."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import structura as st
from structura.core.animation.timeline import Key, Timeline, Track
from structura.core.project.model import Project, save


def test_open_build_and_animate_a_project(tmp_path: Path) -> None:
    text = "#define N 2 (int:1-5)\nN * { x 1.5 } box\n"
    timeline = Timeline(start=0, end=2, tracks=(Track("param:N", (Key(0, 1.0), Key(2, 3.0))),))
    save(tmp_path / "p.structura", Project(text, seed=4, params={"N": 2.0}, timeline=timeline))
    doc = st.open(tmp_path / "p.structura")
    assert doc.seed == 4 and doc.dialect == 1 and len(doc.build()) == 2
    doc.params["N"] = 5
    assert len(doc.build()) == 5
    counts = [len(scene) for _frame, scene in doc.animate()]
    assert counts == [1, 2, 3]  # the keyed parameter wins over the document's value
    assert isinstance(st.Document, type) and st.open(tmp_path / "p.structura").camera_at(1) is None


def test_structura_run_runs_python_scripts(tmp_path: Path) -> None:
    (tmp_path / "s.py").write_text("import structura as st\nprint(len(st.build('3 * { x 1 } box')))\n")
    out = subprocess.run([sys.executable, "-m", "structura.cli.main", "run", str(tmp_path / "s.py")],
                         capture_output=True, text=True, check=True)  # fmt: skip
    assert out.stdout.strip().endswith("3")
