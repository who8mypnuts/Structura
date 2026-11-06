"""`python -m structura` starts the GUI; with a sub-command (lint, build, render) it runs the CLI."""

from __future__ import annotations

import sys

from .cli.main import COMMANDS

if __name__ == "__main__":
    if len(sys.argv) > 1 and (sys.argv[1] in COMMANDS or sys.argv[1].startswith("--")):
        from .cli.main import main as cli_main

        sys.exit(cli_main(sys.argv[1:]))
    from .app.main import main as gui_main

    sys.exit(gui_main(sys.argv))
