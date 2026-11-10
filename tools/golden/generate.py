"""Run the legacy harness over the corpus and write compressed golden data to tests/golden/data/.

Per script and seed: one xz-compressed JSONL file whose first line is a header (meta, record count, kinds histogram,
sampling), followed by the (possibly sampled) primitive/event records, each tagged with its index "i".
Small scripts also get template (3 templates) and OBJ outputs for seed 0.
"""

from __future__ import annotations

import json
import lzma
import subprocess
import sys
import tempfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from corpus import ROOT, CorpusScript, collect

EXE = Path(__file__).resolve().parent / "build/golden_dump"
LABEL = EXE.with_name("SOURCE")  # written by build_harness.py
OUT = ROOT / "tests/golden/data"
SEEDS = (0, 1, 42, 1234)
TEMPLATES = ("Sunflow-Colored", "povray", "renderman")
TEMPLATE_DIR = ROOT / "src/structura/resources/legacy/templates"
FULL_LIMIT, HEAD, TAIL, MIDDLE = 2000, 200, 200, 600
OBJ_MAX_BYTES = 256 * 1024
TIMEOUT = 120
SMALL_FOR_TEXT = 3000


def run(mode: str, script: Path, seed: int, extra: list[str]) -> tuple[dict, str]:
    with tempfile.NamedTemporaryFile(suffix=".out", delete=False) as tmp:
        out_path = Path(tmp.name)
    try:
        proc = subprocess.run(
            [str(EXE), mode, str(script), str(seed), str(out_path), *extra],
            check=False,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
        )
        meta = json.loads(proc.stdout.strip().splitlines()[-1]) if proc.stdout.strip() else {"crash": proc.returncode}
        return meta, out_path.read_text(encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return {"timeout": TIMEOUT}, ""
    finally:
        out_path.unlink(missing_ok=True)


def sample(records: list[str]) -> tuple[list[tuple[int, str]], int]:
    n = len(records)
    if n <= FULL_LIMIT:
        return list(enumerate(records)), 1
    stride = max(1, (n - HEAD - TAIL) // MIDDLE)
    keep = set(range(HEAD)) | set(range(n - TAIL, n)) | set(range(HEAD, n - TAIL, stride))
    return [(i, records[i]) for i in sorted(keep)], stride


def write_dump(script: CorpusScript, seed: int) -> dict:
    meta, text = run("dump", script.path, seed, [])
    records = [line for line in text.splitlines() if line.strip()]
    kinds = Counter(json.loads(r).get("t", "ev:" + json.loads(r).get("ev", "?")) for r in records)
    kept, stride = sample(records)
    header = {
        "script": script.rel,
        "seed": seed,
        "count": len(records),
        "kinds": dict(kinds),
        "stride": stride,
        "full": stride == 1,
        "meta": meta,
    }
    path = OUT / script.id / f"seed{seed}.jsonl.xz"
    path.parent.mkdir(parents=True, exist_ok=True)
    with lzma.open(path, "wt", encoding="utf-8", preset=9) as fh:
        fh.write(json.dumps(header) + "\n")
        for i, rec in kept:
            fh.write(f'{{"i":{i},' + rec[1:] + "\n")
    return {"seed": seed, "count": len(records), "error": meta.get("error"), "timeout": "timeout" in meta}


def write_texts(script: CorpusScript) -> None:
    for name in TEMPLATES:
        _, text = run("template", script.path, 0, [str(TEMPLATE_DIR / f"{name}.rendertemplate")])
        (OUT / script.id / f"template_{name}.txt.xz").write_bytes(lzma.compress(text.encode("utf-8"), preset=9))
    _, obj = run("obj", script.path, 0, [])
    packed = lzma.compress(obj.encode("utf-8"), preset=9)
    if len(packed) <= OBJ_MAX_BYTES:
        (OUT / script.id / "obj.txt.xz").write_bytes(packed)


def process(script: CorpusScript) -> dict:
    entry = {"id": script.id, "path": script.rel, "sha1": script.sha1, "javascript": script.is_javascript}
    if script.is_javascript:
        return entry
    entry["runs"] = [write_dump(script, seed) for seed in SEEDS]
    first = entry["runs"][0]
    if not first["error"] and not first["timeout"] and first["count"] <= SMALL_FOR_TEXT:
        write_texts(script)
        entry["texts"] = True
    return entry


def _label() -> str:
    return LABEL.read_text(encoding="utf-8").strip() if LABEL.exists() else "r312"


def main() -> int:
    """Runs the harness over the corpus and writes the golden data and manifest.

    Returns:
        The exit code (1 when the harness is not built).
    """
    if not EXE.exists():
        print("build the harness first: python tools/golden/build_harness.py", file=sys.stderr)
        return 1
    scripts = collect()
    with ThreadPoolExecutor(max_workers=4) as pool:
        entries = list(pool.map(process, scripts))
    manifest = {
        "harness": f"Structure Synth {_label()} model/parser + Qt 5.15.13",
        "seeds": SEEDS,
        "templates": TEMPLATES,
        "scripts": entries,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    errors = sum(1 for e in entries for r in e.get("runs", []) if r["error"] or r["timeout"])
    print(f"{len(entries)} scripts, {errors} runs with errors/timeouts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
