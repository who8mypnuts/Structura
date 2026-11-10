"""Render reports (docs/09 §8.1): the facts they collect and every output format."""

from __future__ import annotations

import csv
import io
import json
import zipfile
from functools import cache
from pathlib import Path

import numpy as np
import pytest

from structura.compute.cpu import CpuBackend
from structura.core.build.api import build_scene
from structura.core.lang.api import compile_script
from structura.render.api import prepare_with_frame, progressive
from structura.render.details import bvh_stats, render_details
from structura.render.report.collect import ReportInputs, build_report
from structura.render.report.image_stats import histogram, palette
from structura.render.report.model import Report
from structura.render.report.text_writers import sparkline
from structura.render.report.writers import FORMATS, write_text_report
from structura.render.settings import RenderSettings
from structura.services.report_documents import write_report

SCRIPT = "set background #fff\n{ s 0.5 color #c33 } sphere\n4 * { x 1.5 color #36c } box::shiny\n"


@cache
def _inputs() -> ReportInputs:
    """A small real render of SCRIPT with everything a report describes (cached: reports are built from it)."""
    build = build_scene(compile_script(SCRIPT).program, 5)
    settings = RenderSettings(width=48, height=32, samples=4, samples_per_pass=0, frame=True, aovs=True)
    prepared, frame = prepare_with_frame(build.scene, settings)
    details = render_details(prepared, frame, 0.1, CpuBackend().details())
    results = list(progressive(prepared, settings, CpuBackend(), frame))
    return ReportInputs(build.scene, results[-1], details, "cpu Numba", len(results), script=SCRIPT,
                        script_path=Path("/scenes/demo.es"), seed=5, params={"size": 2.0}, build=build.stats,
                        outputs=(Path("/renders/demo.png"),), environment={"Qt": "6.12.0"})  # fmt: skip


@cache
def _report() -> Report:
    return build_report(_inputs())


def _values(key: str) -> dict[str, object]:
    return {r.label: r.value for r in _report().section(key).rows}


def test_the_report_describes_scene_render_and_image() -> None:
    report = _report()
    keys = [s.key for s in report.sections]
    assert keys == ["script", "geometry", "build", "camera", "settings", "lighting", "materials", "image",
                    "performance", "system", "reproduce"]  # fmt: skip
    geometry, image, perf = _values("geometry"), _values("image"), _values("performance")
    assert geometry["Objects"] == 5 and _values("script")["Seed"] == 5
    assert report.section("geometry").tables[0].rows[0][:2] == ("box", "4")  # most frequent kind first
    assert 0 < image["Visible objects"] <= 5 and 0.0 < image["Coverage"] < 1.0  # type: ignore[operator]
    assert perf["BVH nodes / leaves"][0] >= 1 and perf["Samples reached"] == 4  # type: ignore[index]
    assert {m[0] for m in report.section("materials").tables[0].rows} >= {"shiny"}
    assert "--seed 5" in str(_values("reproduce")["Command line"]) and "--size 48x32" in str(
        _values("reproduce")["Command line"]
    )
    assert dict(report.highlights)["Objects"] == "5" and report.thumbnail is not None


def test_image_statistics() -> None:
    display = np.zeros((4, 8, 3), np.uint8)
    display[:, :2] = (255, 0, 0)
    swatches = palette(display)
    assert [s.hex for s in swatches] == ["#000000", "#ff0000"] and swatches[0].share == pytest.approx(0.75)
    h = histogram(display)
    assert h.shape == (64, 4) and h.max() == 1.0 and h[0, 1] == 1.0  # green: all zero


def test_bvh_stats_count_nodes_leaves_and_depth() -> None:
    build = build_scene(compile_script("10 * { x 1 } box\n").program)
    prepared, _ = prepare_with_frame(build.scene, RenderSettings(frame=True))
    stats = bvh_stats(prepared.bvh)
    assert stats.nodes == 2 * stats.leaves - 1 and stats.depth >= 2 and stats.max_leaf_size <= 4


@pytest.mark.parametrize("suffix", [".txt", ".md", ".html", ".json", ".csv"])
def test_text_formats(tmp_path: Path, suffix: str) -> None:
    files = write_text_report(_report(), tmp_path / f"r{suffix}")
    text = files[0].read_text(encoding="utf-8")
    assert "demo.es" in text and "BVH" in text
    if suffix == ".json":
        data = json.loads(text)
        assert data["sections"]["geometry"]["values"]["Objects"] == 5
    if suffix == ".csv":
        rows = list(csv.reader(io.StringIO(text)))
        assert rows[0] == ["section", "property", "value", "raw", "note"] and len(rows) > 50
    if suffix == ".md":
        assert files[1].name == "r-preview.png" and "![Render preview](r-preview.png)" in text
    if suffix == ".html":
        assert text.startswith("<!DOCTYPE html>") and "data:image/png;base64," in text


def test_pdf_and_odt(tmp_path: Path, qapp: object) -> None:  # qapp: a QApplication, as the UI tests need
    pdf = write_report(_report(), tmp_path / "r.pdf")[0]
    assert pdf.read_bytes().startswith(b"%PDF") and pdf.stat().st_size > 10_000
    odt = write_report(_report(), tmp_path / "r.odt")[0]
    with zipfile.ZipFile(odt) as z:
        assert "demo.es" in z.read("content.xml").decode("utf-8")


def test_every_listed_format_can_be_written(tmp_path: Path, qapp: object) -> None:
    for suffix in FORMATS:
        assert write_report(_report(), tmp_path / f"all{suffix}")[0].exists()
    with pytest.raises(ValueError, match="unsupported"):
        write_text_report(_report(), tmp_path / "r.docx")


def test_sparkline_shows_tones() -> None:
    line = sparkline(_report())
    assert len(line) == 32 and line.strip()


def test_the_report_tells_the_lens_timings_device_and_how_to_reproduce() -> None:
    report = _report()
    perf = _values("performance")
    assert perf["Kernel start"] >= 0 and len(perf["Pass time (min / mean / max)"]) == 3  # type: ignore[arg-type]
    assert perf["Device: Threads"] and perf["Peak memory"] > 0  # type: ignore[operator]
    assert "--camera-from /renders/demo.png" in str(_values("reproduce")["Command line"])
    camera = _values("camera")
    assert "Focal length" in camera and camera["Depth of field"] is False and "Scene scale" in camera
    assert report.section("lighting").tables == ()  # no declared lights


def test_a_lens_shows_its_depth_of_field_in_the_report() -> None:
    from dataclasses import replace  # noqa: PLC0415

    from structura.core.scene.lens import Lens  # noqa: PLC0415
    from structura.render.report.render_sections import camera_section  # noqa: PLC0415

    details = _inputs().details
    lensed = replace(details, camera=replace(details.camera, lens=Lens(fstop=2.8, blades=6)))
    rows = {r.label: r for r in camera_section(lensed).rows}
    assert rows["Aperture"].text.startswith("f/2.8") and "6 blades" in rows["Bokeh"].text
    near, far = rows["Sharp range"].value  # type: ignore[misc]
    assert near < lensed.camera.focus < far


def test_the_look_is_reported_and_reproduced() -> None:
    from dataclasses import replace  # noqa: PLC0415

    from structura.render.output import Display  # noqa: PLC0415
    from structura.render.post import LOOKS, PostSettings  # noqa: PLC0415

    neon = build_report(replace(_inputs(), display=Display(0.5, "agx", LOOKS["Neon"])))
    rows = {r.label: r.value for r in neon.section("image").rows}
    assert rows["Post: bloom"] == LOOKS["Neon"].bloom and rows["Exposure"] == 0.5
    command = str({r.label: r.value for r in neon.section("reproduce").rows}["Command line"])
    assert "--look neon" in command and "--exposure 0.5" in command
    custom = build_report(replace(_inputs(), display=Display(0.0, "agx", PostSettings(vignette=0.3))))
    command = str({r.label: r.value for r in custom.section("reproduce").rows}["Command line"])
    assert "--look off --vignette 0.3" in command


def test_every_look_setting_survives_the_reproduce_command() -> None:
    import argparse  # noqa: PLC0415
    import shlex  # noqa: PLC0415

    from structura.cli.commands.post_args import add_post_arguments, post_override  # noqa: PLC0415
    from structura.render.post import PostSettings, look_arguments  # noqa: PLC0415

    custom = PostSettings(bloom=0.2, bloom_threshold=2.0, temperature=-0.5, saturation=1.5, contrast=0.8)
    parser = argparse.ArgumentParser()
    add_post_arguments(parser)
    args = parser.parse_args(shlex.split(shlex.join(look_arguments(custom, PostSettings()))))
    assert post_override(args, PostSettings())["post"] == custom  # nothing lost on the way
    assert look_arguments(custom, custom) == []  # the script's own look needs no options
