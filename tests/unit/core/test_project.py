"""Project files (.structura, docs/07 §8): embedded and linked scripts, migrations, reserved sections."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from structura.core.project import migrations, model
from structura.core.project.migrations import NewerProjectError
from structura.core.project.model import Project
from structura.core.scene.camera import Camera

CAMERA = Camera((1.0, 2.0, 30.0), (0.0, 0.5, 0.0), (0.0, 1.0, 0.0), 30.0, 0.1, 25.0)


def test_embedded_round_trip(tmp_path: Path) -> None:
    project = Project("box\n", seed=4, params={"angle": 20.0}, camera=CAMERA, render={"max_bounces": 9},
                      reserved={"environment": {"type": "hdri"}})  # fmt: skip
    model.save(tmp_path / "a.structura", project)
    assert model.load(tmp_path / "a.structura") == project
    data = json.loads((tmp_path / "a.structura").read_text())
    assert data["format"] == "structura-project" and data["script"] == {"mode": "embedded", "text": "box\n",
                                                                         "dialect": 1}  # fmt: skip


def test_linked_script_is_read_relative_to_the_project(tmp_path: Path) -> None:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "tree.es").write_bytes("// café\r\nbox\r\n".encode("cp1252"))
    model.save(tmp_path / "tree.structura", Project("ignored", linked="scripts/tree.es"))
    loaded = model.load(tmp_path / "tree.structura")
    assert loaded.linked == "scripts/tree.es" and loaded.text == "// café\nbox\n"


def test_newer_formats_are_refused_and_older_ones_migrated(monkeypatch: pytest.MonkeyPatch) -> None:
    newer = json.dumps({"format": "structura-project", "format_version": 99, "script": {"text": ""}})
    with pytest.raises(NewerProjectError):
        model.from_json(newer, Path())
    monkeypatch.setattr(migrations, "CURRENT_VERSION", 2)
    monkeypatch.setitem(migrations.MIGRATIONS, 1, lambda d: d | {"seed": d["old_seed"]})
    old = {"format": "structura-project", "format_version": 1, "old_seed": 8, "script": {"text": "box"}}
    assert migrations.migrate(old)["seed"] == 8 and migrations.migrate(old)["format_version"] == 2


def test_not_a_project() -> None:
    with pytest.raises(ValueError, match="not a Structura project"):
        model.from_json('{"format": "something else"}', Path())


def test_the_timeline_round_trips_and_unknown_sections_survive(tmp_path: Path) -> None:
    from structura.core.animation.timeline import Timeline  # noqa: PLC0415

    timeline = Timeline(30.0, 1, 60).set_key("param:k", 1, 0.5).set_key("camera:fov", 60, 40.0)
    project = Project("box", timeline=timeline, reserved={"lights": [{"name": "key"}]})
    model.save(tmp_path / "p.structura", project)
    loaded = model.load(tmp_path / "p.structura")
    assert loaded.timeline == timeline and loaded.reserved == {"lights": [{"name": "key"}]}
    assert Project("box").timeline is None


def test_camera_bookmarks_round_trip(tmp_path: Path) -> None:
    from structura.core.project.model import Project, from_json, to_json  # noqa: PLC0415
    from structura.core.scene.camera import Camera  # noqa: PLC0415

    views = {"hero": Camera((1.0, 2.0, 3.0), (0.0, 0.0, 0.0), fov_y_deg=30.0)}
    project = from_json(to_json(Project("box\n", bookmarks=views)), tmp_path)
    assert project.bookmarks == views
