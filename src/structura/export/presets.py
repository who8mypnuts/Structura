"""Export presets (docs/15 §7): named option sets per exporter, saved as TOML in the user's config folder and
shared by the export sheet and `structura export --preset`. A few built-in presets (BUILTIN) come with the
program; a user preset of the same name takes their place."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

import platformdirs
import tomli_w

BUILTIN: dict[str, dict[str, dict[str, Any]]] = {  # exporter → preset name → options (PLAN Q4: MeshLab)
    "ply": {"MeshLab": {"cleanup": "clean", "lod": "high"}},
    "obj": {"MeshLab": {"cleanup": "clean", "grouping": "material", "lod": "high"}},
    "stl": {"Print-ready (MeshLab)": {"cleanup": "print-ready", "watertight": True, "lod": "high"}},
    "3mf": {"Print-ready (MeshLab)": {"cleanup": "print-ready", "lod": "high"}},
    "meshlab": {"Layers by material": {"grouping": "material", "cleanup": "clean"}},
}


def preset_dir(exporter: str) -> Path:
    return Path(platformdirs.user_config_dir("structura")) / "export-presets" / exporter


def _file(exporter: str, name: str) -> Path:
    return preset_dir(exporter) / (re.sub(r"[^\w .-]+", "_", name).strip() + ".toml")


def preset_names(exporter: str) -> list[str]:
    folder = preset_dir(exporter)
    saved = {p.stem for p in folder.glob("*.toml")} if folder.is_dir() else set()
    return sorted(saved | set(BUILTIN.get(exporter, {})))


def save_preset(exporter: str, name: str, options: dict[str, Any]) -> Path:
    path = _file(exporter, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(tomli_w.dumps({k: v for k, v in options.items() if v is not None}), encoding="utf-8")
    return path


def load_preset(exporter: str, name: str) -> dict[str, Any]:
    path = _file(exporter, name)
    if not path.exists() and name in BUILTIN.get(exporter, {}):
        return dict(BUILTIN[exporter][name])
    if not path.exists():
        known = ", ".join(preset_names(exporter)) or "none saved"
        raise ValueError(f"no '{name}' preset for the {exporter} exporter ({known})")
    return tomllib.loads(path.read_text(encoding="utf-8"))
