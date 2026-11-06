"""The XWayland fallback for the GPU preview (docs/08 §9)."""

from __future__ import annotations

import sys
from typing import Any

import pytest

from structura.ui.viewport import xwayland


class _Settings:
    def __init__(self) -> None:
        self.values: dict[str, object] = {}

    def value(self, key: str, default: object = None) -> object:
        return self.values.get(key, default)

    def set_value(self, key: str, value: object) -> None:
        self.values[key] = value


@pytest.fixture
def wayland(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    monkeypatch.setenv("DISPLAY", ":0")
    for name in ("QT_QPA_PLATFORM", xwayland.RETRY_ENV, "STRUCTURA_PREVIEW"):
        monkeypatch.setenv(name, "")  # recorded, so whatever the code under test sets is undone afterwards
        monkeypatch.delenv(name)
    monkeypatch.setattr(xwayland, "_qt_version", lambda: "6.12.0")
    return monkeypatch


def test_the_hint_applies_only_for_the_qt_version_that_needed_it(wayland: pytest.MonkeyPatch) -> None:
    settings = _Settings()
    xwayland.apply_hint(settings)
    assert "QT_QPA_PLATFORM" not in xwayland.os.environ
    settings.set_value(xwayland.HINT_KEY, "6.11.0")  # a Qt update may have fixed native Wayland
    xwayland.apply_hint(settings)
    assert "QT_QPA_PLATFORM" not in xwayland.os.environ
    settings.set_value(xwayland.HINT_KEY, "6.12.0")
    xwayland.apply_hint(settings)
    assert xwayland.os.environ["QT_QPA_PLATFORM"] == "xcb"


def test_an_explicit_platform_is_never_overridden(wayland: pytest.MonkeyPatch) -> None:
    wayland.setenv("QT_QPA_PLATFORM", "wayland")
    settings = _Settings()
    settings.set_value(xwayland.HINT_KEY, "6.12.0")
    xwayland.apply_hint(settings)
    assert xwayland.os.environ["QT_QPA_PLATFORM"] == "wayland"


def _capture_exec(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    calls: list[list[str]] = []
    monkeypatch.setattr(xwayland.os, "execv", lambda path, args: calls.append(list(args)))
    return calls


def test_a_failed_wayland_probe_restarts_once_on_xwayland(wayland: pytest.MonkeyPatch) -> None:
    calls = _capture_exec(wayland)
    wayland.setattr(sys, "argv", ["/usr/bin/structura-gui", "scene.es"])
    xwayland.retry_on_xwayland("wayland")
    assert calls == [[sys.executable, "/usr/bin/structura-gui", "scene.es"]]
    assert xwayland.os.environ["QT_QPA_PLATFORM"] == "xcb"
    xwayland.retry_on_xwayland("wayland")  # the retried process: no second restart
    assert len(calls) == 1


@pytest.mark.parametrize(("platform", "env"), [("xcb", {}), ("wayland", {"STRUCTURA_PREVIEW": "cpu"})])
def test_no_restart_off_wayland_or_with_an_explicit_preview(
    wayland: pytest.MonkeyPatch, platform: str, env: dict[str, str]
) -> None:
    calls = _capture_exec(wayland)
    for key, value in env.items():
        wayland.setenv(key, value)
    xwayland.retry_on_xwayland(platform)
    assert calls == []


def test_no_restart_without_an_x_display(wayland: pytest.MonkeyPatch) -> None:
    calls = _capture_exec(wayland)
    wayland.delenv("DISPLAY")
    xwayland.retry_on_xwayland("wayland")
    assert calls == []


@pytest.mark.parametrize(
    ("argv", "frozen", "expected"),
    [(["/x/structura/__main__.py", "a.es"], False, ["-m", "structura", "a.es"]),
     (["/bin/Structura", "a.es"], True, ["a.es"]),
     (["/bin/structura-gui"], False, ["/bin/structura-gui"])],
)  # fmt: skip
def test_restart_command(monkeypatch: pytest.MonkeyPatch, argv: list[str], frozen: bool, expected: list[str]) -> None:
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(sys, "frozen", frozen, raising=False)
    assert xwayland.restart_command() == [sys.executable, *expected]


@pytest.mark.parametrize(("gl_ok", "stored"), [(True, "6.12.0"), (False, None)])
def test_the_choice_is_remembered_only_if_xwayland_had_opengl(
    wayland: pytest.MonkeyPatch, gl_ok: bool, stored: Any
) -> None:
    settings = _Settings()
    xwayland.remember(settings, gl_ok)  # not a retried process: nothing to remember
    assert settings.values == {}
    wayland.setenv(xwayland.RETRY_ENV, "1")
    xwayland.remember(settings, gl_ok)
    assert settings.values.get(xwayland.HINT_KEY) == stored and xwayland.RETRY_ENV not in xwayland.os.environ
