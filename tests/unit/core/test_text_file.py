"""Script files keep their encoding and line endings (docs/12 §2.1)."""

from __future__ import annotations

from pathlib import Path

from structura.core import text_file
from structura.core.text_file import TextFile, decode, encode


def test_utf8_cp1252_and_bom_are_detected() -> None:
    assert decode("rule é { box }".encode()).encoding == "utf-8"
    legacy = decode("// café\r\nbox\r\n".encode("cp1252"))
    assert (legacy.encoding, legacy.newline, legacy.text) == ("cp1252", "\r\n", "// café\nbox\n")
    assert decode(b"\xef\xbb\xbfbox\n").encoding == "utf-8-sig"
    assert decode(b"\xef\xbb\xbfbox\n").text == "box\n"


def test_encode_round_trips_bytes_exactly() -> None:
    for raw in ("// café\r\nbox\r\n".encode("cp1252"), b"\xef\xbb\xbfbox\nsphere\n", b"a\rb\r"):
        assert encode(decode(raw))[0] == raw


def test_text_that_no_longer_fits_cp1252_is_saved_as_utf8(tmp_path: Path) -> None:
    written = text_file.write(tmp_path / "a.es", TextFile("// ★ star\n", "cp1252", "\r\n"))
    assert written.encoding == "utf-8"
    assert (tmp_path / "a.es").read_bytes() == "// ★ star\r\n".encode()


def test_labels() -> None:
    assert TextFile("", "cp1252", "\r\n").label == "Windows-1252 · CRLF"
    assert TextFile("").label == "UTF-8 · LF"
