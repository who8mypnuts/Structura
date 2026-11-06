"""Legacy exports are byte-identical to Structure Synth 1.5: text templates and OBJ (docs/15 §5, docs/18 §3)."""

from __future__ import annotations

import json
import lzma
from functools import cache
from pathlib import Path

import pytest

from structura.core.build.api import build_scene
from structura.core.lang.api import compile_script
from structura.core.scene.ir import SceneIR
from structura.export.legacy_obj import LegacyObjExport
from structura.export.templates.engine import TemplateExport
from structura.export.templates.template_file import LegacyTemplate, bundled_templates, load_template
from tests.golden.golden_compare import DATA, ROOT

_MANIFEST = json.loads((DATA / "manifest.json").read_text()) if (DATA / "manifest.json").exists() else {"scripts": []}
_ENTRIES = {e["id"]: e for e in _MANIFEST["scripts"]}
_TEMPLATE_CASES = [
    (sid, name)
    for sid in _ENTRIES
    for name in _MANIFEST.get("templates", [])
    if (DATA / sid / f"template_{name}.txt.xz").exists()
]
_OBJ_CASES = [sid for sid in _ENTRIES if (DATA / sid / "obj.txt.xz").exists()]


@cache
def _scene(script_id: str) -> SceneIR:
    path = ROOT / _ENTRIES[script_id]["path"]
    return build_scene(compile_script(path.read_text(encoding="utf-8"), 0, None, path.parent).program, 0).scene


@cache
def _template(name: str) -> LegacyTemplate:
    return load_template(bundled_templates()[name])


def _gold(path: Path) -> str:
    return lzma.decompress(path.read_bytes()).decode("utf-8")


@pytest.mark.golden
@pytest.mark.parametrize(("script_id", "template"), _TEMPLATE_CASES, ids=[f"{s}-{t}" for s, t in _TEMPLATE_CASES])
def test_template_output_is_byte_identical(script_id: str, template: str) -> None:
    ours = TemplateExport(_template(template)).render(_scene(script_id))
    assert ours == _gold(DATA / script_id / f"template_{template}.txt.xz")


@pytest.mark.golden
@pytest.mark.parametrize("script_id", _OBJ_CASES)
def test_obj_output_is_byte_identical(script_id: str) -> None:
    assert LegacyObjExport().render(_scene(script_id)) == _gold(DATA / script_id / "obj.txt.xz")
