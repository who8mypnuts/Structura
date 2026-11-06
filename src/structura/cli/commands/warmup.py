"""`structura warmup [--device cpu]` — compile the kernels ahead of time (run by installers; docs/16 §5)."""

from __future__ import annotations

import argparse
import sys

from ...compute.base import BackendUnavailableError
from ...compute.select import NAMES, select_backend
from ...render.warmup import warm_up
from .common import EXIT_OK

HELP = "precompile the Numba kernels (and the chosen device's pipelines)"
EXIT_DEVICE = 3


def register(p: argparse.ArgumentParser) -> None:
    p.add_argument("--device", choices=NAMES, default="cpu", help="also warm this device (default: cpu)")


def run(args: argparse.Namespace) -> int:
    devices = ["cpu"] if args.device == "cpu" else ["cpu", args.device]
    for device in devices:
        try:
            backend = select_backend(device)
        except BackendUnavailableError as exc:
            print(f"{device}: unavailable ({exc})", file=sys.stderr)
            return EXIT_DEVICE
        for step, seconds in warm_up(backend):
            print(f"  {step:<28} {seconds:6.2f} s", file=sys.stderr)
    print("kernels ready")
    return EXIT_OK
