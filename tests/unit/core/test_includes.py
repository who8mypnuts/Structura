"""'#include' (docs/05 §2.4): expansion, include-once, E012, library folders, spans mapped to the edited file."""

from __future__ import annotations

from pathlib import Path

import pytest

from structura.core.build.api import build_scene
from structura.core.lang.analysis import analyze
from structura.core.lang.api import compile_script
from structura.core.lang.includes import expand_includes, set_library_paths


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    (tmp_path / "lib.es").write_text('#define W 2\nrule leaf { { s W } box }\n#include "more.es"\n')
    (tmp_path / "more.es").write_text("rule twig { leaf { x 1 } leaf }\n")
    return tmp_path


def test_included_rules_and_defines_build(folder: Path) -> None:
    text = '#include "lib.es"\n#include "lib.es"\ntwig\nW * { y 3 } sphere\n'
    program = compile_script(text, script_dir=folder).program
    assert len(build_scene(program).scene) == 2 + 2  # two leaves, two spheres; lib.es is included once
    analysis = analyze(text, script_dir=folder)
    assert analysis.ok and {r.name for r in analysis.rules} == {"leaf", "twig"}
    include_line = text.index('#include "lib.es"')
    assert all(r.span.start == include_line for r in analysis.rules)  # defined in an included file
    assert any(text[s.start : s.end] == "twig" for s in analysis.references["twig"])  # own lines stay exact


def test_missing_files_and_cycles_are_e012(folder: Path) -> None:
    (folder / "loop.es").write_text('#include "loop.es"\n')
    text = 'box\n#include "nope.es"\n#include "loop.es"\n'
    codes = [(d.code, text[d.span.start : d.span.end]) for d in analyze(text, script_dir=folder).diagnostics]
    assert ("E012", '#include "nope.es"') in codes and ("E012", '#include "loop.es"') in codes


def test_library_folders_are_searched_after_the_script_folder(
    folder: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    elsewhere = tmp_path_factory.mktemp("script")
    assert not expand_includes('#include "lib.es"\n', elsewhere).files
    set_library_paths([folder])
    try:
        assert expand_includes('#include "lib.es"\n', elsewhere).files == (folder / "lib.es", folder / "more.es")
    finally:
        set_library_paths([])


def test_scripts_without_includes_are_untouched() -> None:
    assert not expand_includes("box // #include in a comment\n").active
