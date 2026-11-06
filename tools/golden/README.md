# Golden generator (test-only)

Builds the **original Structure Synth 1.5** model/parser code against Qt 5 and dumps what it generates for
every corpus script. Structura's compatibility tests compare against these dumps
([docs/18](../../docs/18-testing-and-quality.md) §3).

- The legacy sources are copied from `sample_source/structuresynth-code-r312-trunk` into `build/` at build
  time. They are **never** committed or distributed with Structura.
- The harness links LGPL-2.1/GPL-3 code, so this folder is test tooling only. It is not part of the MIT
  Structura distribution ([ADR-0010](../../docs/adr/0010-licensing.md)).
- Qt 5.15 headers come from Ubuntu's `qtbase5-dev` (extracted into `qt/`, which is git-ignored). They match the
  installed Qt 5.15.13 runtime.

```bash
python tools/golden/build_harness.py          # compile build/golden_dump
python tools/golden/generate.py               # write tests/golden/data/*.jsonl.gz + manifest.json
```
