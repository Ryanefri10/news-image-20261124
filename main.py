#!/usr/bin/env python3
"""Deliver the 24 November 2026 front page for make.fun news-image-20261124.

The entry image is a pre-rendered PNG vendored next to this script
(entry.png, 1024x1024). This program does no drawing: it loads the
vendored artwork, checks it is exactly the front page it claims to be,
and places a copy in the output directory the harness provides.

Run:  MAKEFUN_OUTPUT_DIR=<dir> python3 main.py
"""

import hashlib
import os
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARTWORK = HERE / "entry.png"
OUTPUT_NAME = "entry.png"

# sha256 of the vendored front page, as rendered for 24 November 2026.
EXPECTED_SHA256 = "3f90011e7ce5b6f4080d31b1f359e1399c0e6a0af0547b052f4bdf24fde9254d"
EXPECTED_WIDTH = 1024
EXPECTED_HEIGHT = 1024
MAX_BYTES = 1024 * 1024  # entry image must fit in 1 MiB
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


class FrontPage:
    """One vendored front page, loaded whole and checked before delivery."""

    def __init__(self, source: Path):
        self.source = source
        self.raw: bytes | None = None
        self.width: int | None = None
        self.height: int | None = None
        self.digest: str | None = None

    def load(self) -> "FrontPage":
        self.raw = self.source.read_bytes()
        if len(self.raw) < 33:
            raise ValueError(f"{self.source.name} is too short to be a PNG")
        return self

    def check_magic(self) -> "FrontPage":
        assert self.raw is not None
        if self.raw[:8] != PNG_MAGIC:
            raise ValueError("not a PNG file: bad 8-byte signature")
        return self

    def read_header(self) -> "FrontPage":
        """Pull width/height out of the IHDR chunk that opens the file."""
        assert self.raw is not None
        chunk_len = struct.unpack(">I", self.raw[8:12])[0]
        chunk_type = self.raw[12:16]
        if chunk_type != b"IHDR":
            raise ValueError(f"first chunk is {chunk_type!r}, expected IHDR")
        if chunk_len != 13:
            raise ValueError(f"IHDR length is {chunk_len}, expected 13")
        self.width, self.height = struct.unpack(">II", self.raw[16:24])
        return self

    def check_size(self) -> "FrontPage":
        if (self.width, self.height) != (EXPECTED_WIDTH, EXPECTED_HEIGHT):
            raise ValueError(
                f"page is {self.width}x{self.height}, "
                f"expected {EXPECTED_WIDTH}x{EXPECTED_HEIGHT}"
            )
        return self

    def check_format(self) -> "FrontPage":
        """IHDR must describe an 8-bit truecolour image, and the file
        must fit the 1 MiB entry limit."""
        assert self.raw is not None
        if len(self.raw) > MAX_BYTES:
            raise ValueError(
                f"artwork is {len(self.raw)} bytes, over the {MAX_BYTES} limit"
            )
        bit_depth, colour_type = self.raw[24], self.raw[25]
        if bit_depth != 8 or colour_type != 2:
            raise ValueError(
                f"IHDR says bit depth {bit_depth}, colour type {colour_type}; "
                "expected 8-bit RGB (depth 8, type 2)"
            )
        return self

    def check_digest(self) -> "FrontPage":
        assert self.raw is not None
        self.digest = hashlib.sha256(self.raw).hexdigest()
        if self.digest != EXPECTED_SHA256:
            raise ValueError(
                f"artwork digest mismatch: got {self.digest}, "
                f"expected {EXPECTED_SHA256}"
            )
        return self

    def check_trailer(self) -> "FrontPage":
        """The file must end with a well-formed IEND chunk."""
        assert self.raw is not None
        tail = self.raw[-12:]
        tail_len, tail_type = struct.unpack(">I", tail[:4])[0], tail[4:8]
        if tail_type != b"IEND" or tail_len != 0:
            raise ValueError("file does not end with an IEND chunk")
        return self

    def verify(self) -> "FrontPage":
        return (
            self.load()
            .check_magic()
            .read_header()
            .check_size()
            .check_format()
            .check_digest()
            .check_trailer()
        )

    def deliver(self, out_dir: Path) -> Path:
        assert self.raw is not None
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / OUTPUT_NAME
        target.write_bytes(self.raw)
        return target


def output_dir() -> Path:
    raw = os.environ.get("MAKEFUN_OUTPUT_DIR")
    if not raw:
        raise SystemExit("MAKEFUN_OUTPUT_DIR is not set")
    return Path(raw)


def main() -> int:
    page = FrontPage(ARTWORK).verify()
    target = page.deliver(output_dir())
    print(
        f"delivered {target} "
        f"({page.width}x{page.height}, sha256 {page.digest})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
