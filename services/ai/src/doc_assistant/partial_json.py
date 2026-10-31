"""Extract one top-level string field from a JSON object that arrives in pieces."""

from __future__ import annotations

_ESCAPES = {'"': '"', "\\": "\\", "/": "/", "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t"}


class FieldStreamer:
    """Feed raw JSON deltas; get back newly decoded characters of `field`.

    Tracks depth and string state, so the key only counts at the top level and
    a quote that merely contains the field name is ignored.
    """

    def __init__(self, field: str) -> None:
        self.field = field
        self.depth = 0
        self.in_string = False
        self.escape = False
        self.unicode: str | None = None
        self.token = ""
        self.last_key: str | None = None
        self.expect_value = False
        self.capturing = False
        self.done = False

    def feed(self, delta: str) -> str:
        out: list[str] = []
        for ch in delta:
            if self.in_string:
                if self.unicode is not None:
                    self.unicode += ch
                    if len(self.unicode) == 4:
                        try:
                            decoded = chr(int(self.unicode, 16))
                        except ValueError:
                            decoded = ""
                        self.unicode = None
                        self._emit(decoded, out)
                    continue
                if self.escape:
                    self.escape = False
                    if ch == "u":
                        self.unicode = ""
                    else:
                        self._emit(_ESCAPES.get(ch, ch), out)
                    continue
                if ch == "\\":
                    self.escape = True
                    continue
                if ch == '"':
                    self.in_string = False
                    if self.capturing:
                        self.capturing = False
                        self.done = True
                    elif self.depth == 1 and not self.expect_value:
                        self.last_key = self.token
                    self.expect_value = False
                    continue
                self._emit(ch, out)
                continue
            if ch == '"':
                self.in_string = True
                self.token = ""
                self.capturing = (
                    self.depth == 1 and self.expect_value and self.last_key == self.field
                )
            elif ch in "{[":
                self.depth += 1
                self.expect_value = False
            elif ch in "}]":
                self.depth -= 1
            elif ch == ":" and self.depth == 1:
                self.expect_value = True
            elif ch == ",":
                self.expect_value = False
                self.last_key = None
            elif not ch.isspace():
                self.expect_value = False
        return "".join(out)

    def _emit(self, ch: str, out: list[str]) -> None:
        if self.capturing:
            out.append(ch)
        else:
            self.token += ch
