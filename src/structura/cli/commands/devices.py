"""`structura devices` — the compute devices the precision renderer can use (docs/11 §6, docs/16 §5)."""

from __future__ import annotations

import argparse

from .doctor import compute_lines

HELP = "list the compute devices (CUDA, OpenCL, wgpu, CPU) and which one 'auto' picks"


def register(p: argparse.ArgumentParser) -> None:
    del p  # no options


def run(args: argparse.Namespace) -> int:
    print("\n".join(compute_lines()))
    return 0
