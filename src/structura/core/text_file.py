"""Reading and writing script files (docs/12 §2.1): UTF-8 first, Windows-1252 for legacy files written on
Windows, and the file's line-ending style kept on save. The editor, the CLI and the Python API all read
scripts through this module."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

UTF8, CP1252 = "utf-8", "cp1252"
BOM = "\ufeff"


@dataclass(frozen=True)
class TextFile:
    text: str  # with '\n' line endings
    encoding: str = UTF8  # "utf-8" | "utf-8-sig" | "cp1252"
    newline: str = "\n"  # "\n" | "\r\n" | "\r"

    @property
    def label(self) -> str:
        """Status-bar label: 'UTF-8', 'UTF-8 BOM' or 'Windows-1252', plus the line endings."""
        names = {UTF8: "UTF-8", "utf-8-sig": "UTF-8 BOM", CP1252: "Windows-1252"}
        endings = {"\n": "LF", "\r\n": "CRLF", "\r": "CR"}
        return f"{names.get(self.encoding, self.encoding)} · {endings[self.newline]}"


def _newline_style(text: str) -> str:
    crlf = text.count("\r\n")
    lf = text.count("\n") - crlf
    cr = text.count("\r") - crlf
    return max((("\n", lf), ("\r\n", crlf), ("\r", cr)), key=lambda item: item[1])[0] if (lf or crlf or cr) else "\n"


def decode(data: bytes) -> TextFile:
    try:
        text, encoding = data.decode(UTF8), UTF8
    except UnicodeDecodeError:
        text, encoding = data.decode(CP1252, errors="replace"), CP1252
    if text.startswith(BOM):
        text, encoding = text[1:], "utf-8-sig"
    newline = _newline_style(text)
    return TextFile(text.replace("\r\n", "\n").replace("\r", "\n"), encoding, newline)


def encode(file: TextFile) -> tuple[bytes, str]:
    """The bytes to write and the encoding actually used (UTF-8 when the text no longer fits cp1252)."""
    text = file.text.replace("\n", file.newline)
    try:
        return text.encode(file.encoding), file.encoding
    except UnicodeEncodeError:
        return text.encode(UTF8), UTF8


def read(path: Path) -> TextFile:
    return decode(path.read_bytes())


def read_script(path: Path) -> str:
    return read(path).text


def write(path: Path, file: TextFile) -> TextFile:
    """Write ``file`` to ``path``; returns the file as written (its encoding may have become UTF-8)."""
    data, encoding = encode(file)
    path.write_bytes(data)
    return TextFile(file.text, encoding, file.newline)
