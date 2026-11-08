"""A template's 'runAfter' command (docs/15 §5.2, Structure Synth 1.5): the program to run on the exported
file, e.g. '"%SUNFLOW%\\sunflow2.bat" "$FILE" -o "$FILE.png"'. $FILE is the exported file; %NAME%, $NAME and
${NAME} are environment variables (left as they are when unset, so the user sees what is missing)."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from pathlib import Path

VARIABLE = re.compile(r"%(\w+)%|\$\{(\w+)\}|\$(\w+)")


def expand_command(command: str, file: Path, env: Mapping[str, str] | None = None) -> str:
    values = dict(os.environ if env is None else env)

    def value(match: re.Match[str]) -> str:
        name = match.group(1) or match.group(2) or match.group(3)
        if name == "FILE":
            return str(file)
        return values.get(name, match.group(0))

    return VARIABLE.sub(value, command)


def missing_variables(command: str, env: Mapping[str, str] | None = None) -> list[str]:
    values = dict(os.environ if env is None else env)
    names = (m.group(1) or m.group(2) or m.group(3) for m in VARIABLE.finditer(command))
    return sorted({n for n in names if n != "FILE" and n not in values})
