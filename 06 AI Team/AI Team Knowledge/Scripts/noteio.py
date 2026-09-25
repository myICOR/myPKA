#!/usr/bin/env python3
r"""noteio.py: read and write a member's file without rewriting a byte the
caller never meant to touch.

Why this exists. Python's text mode is universal-newlines on the way IN:
`Path(p).read_text()` turns every `\r\n` and every lone `\r` into `\n`
before the caller ever sees the text. Text mode on the way OUT then writes
`\n` (or, on Windows, `\r\n`). So the ordinary read-edit-write shape that
runs through a dozen scripts here quietly rewrites the line endings of
every note it touches. On macOS nothing looks wrong until the member opens
the same note on Windows, or in git, and every line reads as changed (Ian
Slattery, T15-A; the read half reproduces on macOS, where a CRLF note and
a stray CR both come back as plain LF).

The contract:

    text, eol = read_note(path)   # decoded from bytes, NOTHING translated
    ...                           # edit text, add lines using `eol`
    write_note(path, text)        # written as bytes, NOTHING translated

Because nothing is translated, a `\r\n` note keeps its `\r` characters
inside `text`. That breaks the usual `text.startswith("---\n")` and
`text.find("\n---\n", 4)` pair, so the closing fence gets one regex, here,
used by every caller:

    FM_CLOSE.search(text)         # matches "\n---\n" AND "\n---\r\n"

`eol` is the line ending the file uses most, and is what a caller appends
with when it ADDS a line to an existing file. A file created from scratch
gets plain `\n`: a new note has no line endings of its own to honour, and
LF is what the rest of the scaffold ships.
"""
import re
from pathlib import Path

__all__ = ["FM_CLOSE", "read_note", "write_note", "detect_eol"]

# The closing frontmatter fence, in either line ending. Deliberately NOT
# anchored to the start of the file: callers search from an offset past the
# opening fence.
FM_CLOSE = re.compile(r"\n---\r?\n")


def detect_eol(data: bytes) -> str:
    r"""The line ending this file uses most: "\r\n", "\r" or "\n".

    Most files use exactly one. A file that mixes them keeps every byte it
    has (nothing is translated); `eol` only answers "what should a line I
    ADD look like", and for that the majority is the honest answer. A file
    with no line ending at all gets "\n".
    """
    crlf = data.count(b"\r\n")
    lf = data.count(b"\n") - crlf
    cr = data.count(b"\r") - crlf
    best = max((crlf, "\r\n"), (lf, "\n"), (cr, "\r"), key=lambda t: t[0])
    return best[1] if best[0] else "\n"


def read_note(path) -> tuple:
    """(text, eol) for one file, decoded from its bytes with no newline
    translation at all. Raises UnicodeDecodeError on a binary, which the
    caller is expected to catch and turn into a FAIL line."""
    data = Path(path).read_bytes()
    return data.decode("utf-8"), detect_eol(data)


def write_note(path, text: str) -> None:
    """Write `text` as bytes. Whatever line endings are in `text` are the
    line endings that land on disk, byte for byte."""
    Path(path).write_bytes(text.encode("utf-8"))
