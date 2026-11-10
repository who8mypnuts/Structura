"""Fetch the bundled fonts (Inter, JetBrains Mono; SIL OFL 1.1) into src/structura/resources/fonts.

    python tools/fetch_fonts.py            # upstream GitHub releases, else the official npm builds
    python tools/fetch_fonts.py --npm      # the npm builds only (WOFF2, converted losslessly to TTF)

The npm route needs fontTools with Brotli (``uv pip install fonttools brotli``). Every file written is listed
with its SHA-256 in resources/fonts/SOURCES.md.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import sys
import tarfile
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

FONTS = Path(__file__).resolve().parents[1] / "src" / "structura" / "resources" / "fonts"
TIMEOUT = 60


@dataclass(frozen=True)
class Source:
    """Where one bundled font comes from.

    Attributes:
        name: The file written into FONTS.
        release: (zip URL, member path) of the upstream release.
        npm: (tarball URL, WOFF2 member path) of the official npm build.
    """

    name: str
    release: tuple[str, str]
    npm: tuple[str, str]


INTER_ZIP = "https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip"
INTER_NPM = "https://registry.npmjs.org/inter-ui/-/inter-ui-4.1.1.tgz"
MONO_ZIP = "https://github.com/JetBrains/JetBrainsMono/releases/download/v2.304/JetBrainsMono-2.304.zip"
MONO_NPM = "https://registry.npmjs.org/typeface-jetbrains-mono/-/typeface-jetbrains-mono-2.0.1.tgz"

SOURCES = (
    Source("Inter-Variable.ttf", (INTER_ZIP, "InterVariable.ttf"), (INTER_NPM, "package/variable/InterVariable.woff2")),
    Source("Inter-Variable-Italic.ttf", (INTER_ZIP, "InterVariable-Italic.ttf"),
           (INTER_NPM, "package/variable/InterVariable-Italic.woff2")),
    *(Source(f"JetBrainsMono-{style}.ttf", (MONO_ZIP, f"fonts/ttf/JetBrainsMono-{style}.ttf"),
             (MONO_NPM, f"package/dist/JetBrainsMono-{style}.woff2"))
      for style in ("Regular", "Italic", "Bold", "BoldItalic")),
)  # fmt: skip


def _download(url: str, cache: dict[str, bytes]) -> bytes:
    """Downloads a URL once (later calls read the cache)."""
    if url not in cache:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
            cache[url] = response.read()
    return cache[url]


def from_release(source: Source, cache: dict[str, bytes]) -> bytes:
    """Returns a font from the upstream release archive.

    Args:
        source: The font.
        cache: Downloads by URL (an archive holds several fonts).

    Raises:
        OSError: The download failed.
        StopIteration: The archive has no such member.
    """
    url, member = source.release
    with zipfile.ZipFile(io.BytesIO(_download(url, cache))) as archive:
        path = next(n for n in archive.namelist() if n.endswith(member))
        return archive.read(path)


def from_npm(source: Source, cache: dict[str, bytes]) -> bytes:
    """Returns a font from the npm build, converted from WOFF2 to TrueType (glyph data unchanged).

    Args:
        source: The font.
        cache: Downloads by URL.

    Raises:
        OSError: The download failed.
        KeyError: The tarball has no such member.
    """
    from fontTools.ttLib import TTFont  # noqa: PLC0415 - a tool dependency, only for this route

    url, member = source.npm
    with tarfile.open(fileobj=io.BytesIO(_download(url, cache))) as archive:
        extracted = archive.extractfile(member)
        assert extracted is not None, member
        font = TTFont(io.BytesIO(extracted.read()))
    font.flavor = None  # WOFF2 → plain TrueType; glyph data is unchanged
    out = io.BytesIO()
    font.save(out)
    return out.getvalue()


def _version(data: bytes) -> str:
    from fontTools.ttLib import TTFont  # noqa: PLC0415

    return str(TTFont(io.BytesIO(data))["name"].getDebugName(5) or "?")


def fetch(npm_only: bool) -> list[tuple[str, str, str, str]]:
    """Writes every bundled font, trying the routes in order.

    Args:
        npm_only: Skip the upstream releases.

    Returns:
        (file, version, origin URL, SHA-256) of every font written.

    Raises:
        SystemExit: A font could not be fetched by any route.
    """
    cache: dict[str, bytes] = {}
    routes: list[tuple[str, Callable[[Source, dict[str, bytes]], bytes]]] = [("npm", from_npm)]
    if not npm_only:
        routes.insert(0, ("release", from_release))
    written = []
    for source in SOURCES:
        for route, getter in routes:
            try:
                data = getter(source, cache)
            except (OSError, KeyError, StopIteration, zipfile.BadZipFile, tarfile.TarError) as exc:
                print(f"{source.name}: {route} unavailable ({exc})", file=sys.stderr)
                continue
            (FONTS / source.name).write_bytes(data)
            origin = source.release[0] if route == "release" else source.npm[0]
            written.append((source.name, _version(data), origin, hashlib.sha256(data).hexdigest()))
            break
        else:
            raise SystemExit(f"could not fetch {source.name}")
    return written


def write_sources(rows: list[tuple[str, str, str, str]]) -> None:
    """Writes resources/fonts/SOURCES.md: every file with its version, origin and SHA-256.

    Args:
        rows: What ``fetch`` returned.
    """
    lines = ["# Bundled fonts", "", "Written by `tools/fetch_fonts.py`. Both families are under the SIL Open Font",
             "License 1.1 (`OFL-Inter.txt`, `OFL-JetBrainsMono.txt`).", "",
             "| File | Version | Source | SHA-256 |", "|------|---------|--------|---------|"]  # fmt: skip
    lines += [f"| {name} | {version} | {origin} | `{digest}` |" for name, version, origin, digest in rows]
    (FONTS / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    """Fetches the fonts and writes SOURCES.md.

    Returns:
        The exit code (0).
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--npm", action="store_true", help="use the npm builds only")
    rows = fetch(parser.parse_args().npm)
    write_sources(rows)
    for name, version, origin, _ in rows:
        print(f"{name}: {version} ({origin})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
