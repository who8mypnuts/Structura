"""`structura run SCRIPT.es [--limit N]`: run a Structure Synth '#javascript' script (docs/16 §3)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from PySide6.QtCore import QCoreApplication

from ...compute.select import select_backend
from ...core.build.api import build_scene
from ...core.lang.api import compile_script
from ...core.scene.ir import SceneIR
from ...export.templates.engine import TemplateExport
from ...export.templates.template_file import bundled_templates, load_template
from ...render.api import render, script_settings
from ...render.output import save_image
from ...scripting.js_bridge import run_javascript
from .common import EXIT_OK, EXIT_SCRIPT_ERROR, read_script

HELP = "run a Structure Synth '#javascript' script (Builder.load / define / build / raytraceToFile …)"


class CliHost:
    def __init__(self, device: str, samples: int | None, allow_execute: bool) -> None:
        self.backend = select_backend(device)
        self.samples, self.execute = samples, allow_execute

    def build(self, text: str, script_dir: Path) -> SceneIR:
        return build_scene(compile_script(text, 0, None, script_dir).program).scene

    def raytrace(self, scene: Any, path: Path, width: int, height: int) -> None:
        from dataclasses import replace  # noqa: PLC0415

        settings = replace(script_settings(scene), integrator="classic")
        if width or height:
            w, h = width or round(height * 4 / 3), height or round(width * 3 / 4)
            settings = replace(settings, width=w, height=h)
        if self.samples:
            settings = replace(settings, samples=self.samples)
        result = render(scene, replace(settings, samples_per_pass=max(1, min(8, settings.samples))), self.backend)
        save_image(result.image, path, 0.0, "standard")
        print(f"  raytraced {path.name}", file=sys.stderr)

    def render_template(self, scene: Any, template: str, path: Path) -> None:
        name = Path(template).stem
        path.write_text(TemplateExport(load_template(bundled_templates()[name])).render(scene), encoding="utf-8")

    def allow_execute(self, command: str, arguments: str) -> bool:
        return self.execute


def register(p: argparse.ArgumentParser) -> None:
    p.add_argument("script", type=Path)
    p.add_argument("--limit", type=int, help="stop after this many output files")
    p.add_argument("--samples", type=int, help="override the samples of each raytrace")
    p.add_argument("--device", default="auto")
    p.add_argument("--allow-execute", action="store_true", help="let Builder.execute run external programs")


def run(args: argparse.Namespace) -> int:
    app = QCoreApplication.instance() or QCoreApplication(sys.argv[:1])
    host = CliHost(args.device, args.samples, args.allow_execute)
    try:
        written = run_javascript(read_script(args.script), args.script.parent, host, args.limit)
    except (RuntimeError, ValueError, OSError) as exc:
        print(f"{args.script}: {exc}", file=sys.stderr)
        return EXIT_SCRIPT_ERROR
    del app
    print(f"wrote {written} file{'s' if written != 1 else ''}")
    return EXIT_OK
