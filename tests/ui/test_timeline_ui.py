"""The Timeline dock: keying parameters and the camera, scrubbing, playback (docs/16 §2)."""

from __future__ import annotations

from dataclasses import replace

from pytestqt.qtbot import QtBot

from structura.core.scene.camera import Camera
from structura.ui.app_window import MainWindow

SCRIPT = "#version 2\n#param k float = 1 range 0..10\n{ x k } box\n"


def _ready(qtbot: QtBot, window: MainWindow):  # type: ignore[no-untyped-def]
    tab = window.docs.new_script()
    tab.editor.setPlainText(SCRIPT)
    window.workbench.build(tab)
    qtbot.waitUntil(lambda: tab.outcome is not None, timeout=20000)
    return tab


def test_keyed_parameters_interpolate_while_scrubbing(qtbot: QtBot, window: MainWindow) -> None:
    tab = _ready(qtbot, window)
    tl = window.timeline
    window.parameters.key_toggled.emit("k")  # key k = 1 at frame 0
    tl.set_frame(10)
    tab.params["k"] = 5.0
    window.parameters.key_toggled.emit("k")  # key k = 5 at frame 10
    assert [k.frame for k in tab.timeline.track("param:k").keys] == [0, 10]  # type: ignore[union-attr]
    tl.set_frame(5)
    assert tab.params["k"] == 3.0  # smooth interpolation is symmetric at the midpoint
    qtbot.waitUntil(lambda: tab.outcome is not None and abs(float(tab.outcome.scene.xform[0, 0, 3]) - 3.0) < 1e-5,
                    timeout=20000)  # fmt: skip
    window.parameters.key_toggled.emit("k")  # no key at frame 5: adds one
    window.timeline_panel.key_action.emit("param:k", 5, "delete")
    assert len(tab.timeline.track("param:k").keys) == 2  # type: ignore[union-attr]


def test_camera_keys_move_the_viewport(qtbot: QtBot, window: MainWindow) -> None:
    tab = _ready(qtbot, window)
    window.viewport.set_camera(Camera((0.0, 0.0, 10.0), (0.0, 0.0, 0.0)))
    window.timeline.key_camera()
    window.timeline.set_frame(20)
    window.viewport.set_camera(replace(window.viewport.camera(), eye=(10.0, 0.0, 10.0)))
    window.timeline.key_camera()
    window.timeline.set_frame(10)
    assert 4.0 < window.viewport.camera().eye[0] < 6.0 and tab.frame == 10


def test_playback_advances_and_wraps(qtbot: QtBot, window: MainWindow) -> None:
    tab = _ready(qtbot, window)
    tab.timeline = replace(tab.timeline, start=0, end=2, fps=100.0)
    window.timeline.play(True)
    qtbot.waitUntil(lambda: tab.frame == 2, timeout=3000)
    qtbot.waitUntil(lambda: tab.frame == 0, timeout=3000)
    window.timeline.play(False)
    assert not window.timeline.timer.isActive() and window.timeline_panel.play.text() == "▶"


def test_colour_switch_and_choice_parameters_get_their_own_controls(qtbot: QtBot, window: MainWindow) -> None:
    from PySide6.QtWidgets import QComboBox  # noqa: PLC0415

    from structura.ui.widgets.param_choice import ParamChoice  # noqa: PLC0415

    tab = window.docs.new_script()
    tab.editor.setPlainText("#version 2\n#param style enum = tree of ball|tree\nstyle\nrule tree { box }\n"
                            "rule ball { sphere }\n")  # fmt: skip
    qtbot.waitUntil(
        lambda: tab.outcome is not None and bool(window.parameters.findChildren(ParamChoice)), timeout=30000
    )
    choice = window.parameters.findChildren(ParamChoice)[0]
    assert isinstance(choice.control, QComboBox) and choice.control.currentText() == "tree"
    choice.control.setCurrentIndex(0)
    qtbot.waitUntil(lambda: tab.outcome is not None and int(tab.outcome.scene.kind[0]) == 1, timeout=30000)
    assert tab.params["style"] == 0.0
