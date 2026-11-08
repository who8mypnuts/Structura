"""The command line: lint, build and render end to end (docs/16 §5)."""

from __future__ import annotations

import json
from pathlib import Path

import OpenEXR
import pytest
from PIL import Image

from structura.cli.main import main
from structura.render.metadata import read_metadata

SCRIPT = "set raytracer::samples 2\nset background #123\n{ color #f80 } sphere\n{ x 1.2 } box::glass\n"


@pytest.fixture
def script(tmp_path: Path) -> Path:
    path = tmp_path / "scene.es"
    path.write_text(SCRIPT)
    return path


def test_render_writes_an_image_with_reproducibility_metadata(script: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.png"
    argv = ["render", str(script), "-o", str(out), "--size", "32x24", "--integrator", "classic", "--device", "cpu"]
    assert main([*argv, "--seed", "7"]) == 0
    assert Image.open(out).size == (32, 24)
    meta = read_metadata(out)
    assert meta["script"] == SCRIPT and meta["seed"] == "7"
    settings = json.loads(meta["settings"])
    assert settings["samples"] == 4 and settings["integrator"] == "classic"  # 'raytracer::samples 2' → 2×2


def test_render_rejects_unknown_formats(script: Path, tmp_path: Path) -> None:
    assert main(["render", str(script), "-o", str(tmp_path / "x.gif"), "--device", "cpu"]) == 2


def test_render_exr_keeps_linear_floats(script: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.exr"
    argv = ["render", str(script), "-o", str(out), "--size", "16x12", "--samples", "1", "--device", "cpu"]
    assert main([*argv, "--no-embed-script"]) == 0
    meta = read_metadata(out)
    assert "script" not in meta and len(meta["script_sha256"]) == 64


def test_render_denoise_writes_aov_layers_only_when_asked(script: Path, tmp_path: Path) -> None:
    out = tmp_path / "den.exr"
    argv = ["render", str(script), "-o", str(out), "--size", "16x12", "--samples", "2", "--device", "cpu"]
    assert main([*argv, "--denoise", "atrous"]) == 0
    with OpenEXR.File(str(out)) as f:
        assert "albedo" not in f.channels()
    assert main([*argv, "--denoise", "atrous", "--aovs"]) == 0
    with OpenEXR.File(str(out)) as f:
        assert {"albedo", "N", "Z"} <= set(f.channels())


def test_convert_prints_notes_and_a_diff_and_writes_the_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "old.es"
    source.write_text("rule tube { box }\ntube\n")
    out = tmp_path / "new.es"
    assert main(["convert", str(source), "--to", "v2", "-o", str(out)]) == 0
    captured = capsys.readouterr()
    assert "+#version 2" in captured.out and "renamed" in captured.err
    assert out.read_text().startswith("#version 2\nrule tube_rule")


def test_render_writes_reports(script: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.png"
    argv = ["render", str(script), "-o", str(out), "--size", "24x16", "--device", "cpu"]
    assert main([*argv, "--report", str(tmp_path / "r.txt"), "--report", str(tmp_path / "r.json")]) == 0
    assert "out.png" in (tmp_path / "r.txt").read_text(encoding="utf-8")
    assert json.loads((tmp_path / "r.json").read_text(encoding="utf-8"))["highlights"]["Resolution"] == "24 × 16"
    assert main([*argv, "--report", str(tmp_path / "r.docx")]) == 2


def test_template_theme_and_devices_commands(script: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "scene.sc"
    assert main(["template", str(script), "-o", str(out), "--template", "Sunflow-Colored", "--size", "320x240"]) == 0
    assert "320" in out.read_text()
    assert main(["theme", "list"]) == 0 and "nord-light" in capsys.readouterr().out
    theme = Path(__file__).parents[3] / "src" / "structura" / "themes" / "builtin" / "nord.toml"
    assert main(["theme", "check", str(theme)]) == 0 and main(["theme", "check", str(theme), "--strict"]) == 1
    assert main(["devices"]) == 0 and "auto selects" in capsys.readouterr().out


def test_files_on_the_command_line_open_the_gui() -> None:
    from structura.cli.main import opens_gui  # noqa: PLC0415

    assert opens_gui([]) and opens_gui(["scene.es"]) and opens_gui(["a.structura", "b.es"])
    assert not opens_gui(["render", "scene.es"]) and not opens_gui(["--version"])


def test_export_presets_are_shared_with_the_export_sheet(
    script: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from structura.export import presets  # noqa: PLC0415

    monkeypatch.setattr(presets.platformdirs, "user_config_dir", lambda _name: str(tmp_path / "config"))
    presets.save_preset("stl", "Print 10x", {"unit_scale": 10.0, "watertight": False})
    assert presets.preset_names("stl") == ["Print 10x"]
    out = tmp_path / "part.stl"
    assert main(["export", str(script), "-o", str(out), "--preset", "Print 10x"]) == 0 and out.stat().st_size > 84
    assert main(["export", str(script), "-o", str(out), "--preset", "missing"]) == 2


def test_run_after_commands_expand_the_file_and_variables(tmp_path: Path) -> None:
    from structura.export.templates.run_after import expand_command, missing_variables  # noqa: PLC0415

    command = '"%SUNFLOW%\\sunflow2.bat" "$FILE" -o "${FILE}.png" $HOME'
    out = expand_command(command, tmp_path / "a.sc", {"SUNFLOW": "C:\\sf", "HOME": "/home/u"})
    assert out == f'"C:\\sf\\sunflow2.bat" "{tmp_path / "a.sc"}" -o "{tmp_path / "a.sc"}.png" /home/u'
    assert missing_variables(command, {"HOME": "/h"}) == ["SUNFLOW"]
    assert expand_command("%UNSET% x", tmp_path, {}) == "%UNSET% x"  # left visible
