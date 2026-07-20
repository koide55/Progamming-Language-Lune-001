"""Apply machine-suggested fixes to Lune source (`lune fix`).

Currently fixes undefined-name typos (TYP0001) using the "did you mean"
suggestion, which carries a structured Fix (span + replacement). The driver is
iterative: the type checker reports the first error, we apply its fix, then
re-check — so several typos in one file are corrected in one run.
"""

from __future__ import annotations

from .parser import parse_source
from .typechecker import LuneTypeError, check_source

MAX_ITERATIONS = 200


class FixError(Exception):
    pass


def apply_fixes(source: str, filename: str = "<input>") -> tuple[str, int]:
    """Return (fixed_source, number_of_fixes_applied)."""
    # Without module resolution, imported names look undefined and would be
    # "corrected" to the wrong local name, so refuse files with imports for now.
    module = parse_source(source, filename)
    if module.imports:
        raise FixError("lune fix does not support files with imports yet")

    applied = 0
    for _ in range(MAX_ITERATIONS):
        try:
            check_source(source, filename)
            break
        except LuneTypeError as exc:
            fixes = exc.diagnostic.fixes
            if not fixes:
                break
            updated = _apply_edits(source, fixes)
            if updated == source:
                break
            source = updated
            applied += 1
    return source, applied


def _apply_edits(source: str, fixes) -> str:
    lines = source.splitlines(keepends=True)
    prefix = [0]
    for line in lines:
        prefix.append(prefix[-1] + len(line))

    def offset(line: int, column: int) -> int:
        base = prefix[line - 1] if 1 <= line <= len(prefix) else len(source)
        return base + (column - 1)

    # Apply from the end backwards so earlier offsets stay valid.
    edits = sorted(
        (
            (offset(f.span.start_line, f.span.start_column), offset(f.span.end_line, f.span.end_column), f.replacement)
            for f in fixes
        ),
        reverse=True,
    )
    for start, end, replacement in edits:
        source = source[:start] + replacement + source[end:]
    return source
