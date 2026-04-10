from __future__ import annotations

import re
import sys
import traceback
from io import StringIO
from types import TracebackType

try:
    import pretty_errors

    _HAS_PRETTY_ERRORS = True
except ImportError:
    pretty_errors = None  # type: ignore[assignment]
    _HAS_PRETTY_ERRORS = False


_ANSI_PATTERN = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def remove_ansi_codes(text: str) -> str:
    return _ANSI_PATTERN.sub("", text)


def format_exception_pretty(
    exc_type: type[BaseException] | None = None,
    exc_value: BaseException | None = None,
    exc_tb: TracebackType | None = None,
) -> str:
    if exc_type is None:
        exc_type, exc_value, exc_tb = sys.exc_info()
    if exc_type is None:
        return ""

    if not _HAS_PRETTY_ERRORS:
        return "".join(traceback.format_exception(exc_type, exc_value, exc_tb))

    buffer = StringIO()

    class _Writer(pretty_errors.ExceptionWriter):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()

        def output_text(self, texts: str | list | tuple) -> None:
            if not isinstance(texts, (list, tuple)):
                texts = [texts]
            count = 0
            for text in texts:
                _text = str(text)
                buffer.write(_text)
                count += self.visible_length(_text)
            line_length = self.get_line_length()
            if count == 0 or count % line_length != 0 or self.config.full_line_newline:  # type: ignore[union-attr]
                buffer.write("\n")
            buffer.write(pretty_errors.RESET_COLOR)  # type: ignore[union-attr]

    original_writer = pretty_errors.exception_writer  # type: ignore[union-attr]
    try:
        pretty_errors.exception_writer = _Writer()  # type: ignore[union-attr]
        pretty_errors.excepthook(exc_type, exc_value, exc_tb)  # type: ignore[union-attr]
        return buffer.getvalue()
    finally:
        pretty_errors.exception_writer = original_writer  # type: ignore[union-attr]
