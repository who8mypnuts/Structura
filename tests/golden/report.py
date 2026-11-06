"""Run the full golden comparison and print a summary: python -m tests.golden.report [filter]."""

from __future__ import annotations

import json
import sys
from concurrent.futures import ProcessPoolExecutor

from tests.golden.golden_compare import DATA, compare


def _one(job: tuple[str, int]) -> tuple[str, int, bool, str]:
    script_id, seed = job
    try:
        outcome = compare(script_id, seed)
        return script_id, seed, outcome.ok, outcome.message
    except Exception as exc:
        return script_id, seed, False, f"crash: {type(exc).__name__}: {exc}"


def main() -> int:
    manifest = json.loads((DATA / "manifest.json").read_text())
    pattern = sys.argv[1] if len(sys.argv) > 1 else ""
    jobs = [
        (e["id"], s)
        for e in manifest["scripts"]
        if not e["javascript"] and pattern in e["id"]
        for s in manifest["seeds"]
    ]
    with ProcessPoolExecutor(4) as pool:
        results = list(pool.map(_one, jobs))
    failures = [r for r in results if not r[2]]
    for script_id, seed, _, message in failures:
        print(f"FAIL {script_id} seed {seed}: {message[:300]}")
    print(f"golden: {len(results) - len(failures)}/{len(results)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
