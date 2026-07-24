from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .explanations import has_explanation
from .messages import t


def display_filename(filename: str) -> str:
    """Absolute paths under the current directory render relative (rustc-style).

    Paths outside the cwd, and virtual names like `<repl:1>`, pass through.
    """
    path = Path(filename)
    if not path.is_absolute():
        return filename
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return filename


@dataclass(frozen=True)
class SourceSpan:
    filename: str
    start_line: int
    start_column: int
    end_line: int
    end_column: int

    @classmethod
    def point(cls, filename: str, line: int, column: int, width: int = 1) -> SourceSpan:
        return cls(filename, line, column, line, max(column + width, column + 1))

    def format(self) -> str:
        return f"{display_filename(self.filename)}:{self.start_line}:{self.start_column}"


@dataclass(frozen=True)
class Label:
    span: SourceSpan
    message: str | None = None


@dataclass(frozen=True)
class Fix:
    """A machine-applicable edit: replace the text at `span` with `replacement`."""

    span: SourceSpan
    replacement: str
    description: str


@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: str
    message: str
    primary: Label | None = None
    notes: list[str] = field(default_factory=list)
    hints: list[str] = field(default_factory=list)
    fixes: list[Fix] = field(default_factory=list)


class DiagnosticError(Exception):
    def __init__(self, diagnostic: Diagnostic):
        super().__init__(diagnostic.message)
        self.diagnostic = diagnostic


class SourceMap:
    def __init__(self):
        self._sources: dict[str, list[str]] = {}

    def add(self, filename: str, source: str) -> None:
        self._sources[filename] = source.splitlines()

    def get_line(self, filename: str, line: int) -> str | None:
        lines = self._sources.get(filename)
        if lines is None or line < 1 or line > len(lines):
            return None
        return lines[line - 1]


def format_exception(exc: Exception, source_map: SourceMap | None = None, *, explain_hint: bool = False) -> str:
    if isinstance(exc, DiagnosticError):
        return format_diagnostic(exc.diagnostic, source_map, explain_hint=explain_hint)
    return f"error: {exc}"


def format_diagnostic(
    diagnostic: Diagnostic, source_map: SourceMap | None = None, *, explain_hint: bool = False
) -> str:
    lines = [f"{diagnostic.severity}[{diagnostic.code}]: {diagnostic.message}"]
    primary = diagnostic.primary
    if primary is not None:
        span = primary.span
        lines.append(f"  --> {span.format()}")
        source_line = source_map.get_line(span.filename, span.start_line) if source_map is not None else None
        if source_line is not None:
            line_number = str(span.start_line)
            gutter_width = max(len(line_number), 1)
            lines.append(f"{' ' * gutter_width} |")
            lines.append(f"{line_number} | {source_line}")
            caret_width = _caret_width(span)
            caret_prefix = " " * max(span.start_column - 1, 0)
            label = f" {primary.message}" if primary.message else ""
            lines.append(f"{' ' * gutter_width} | {caret_prefix}{'^' * caret_width}{label}")
        elif primary.message:
            lines.append(f"   = note: {primary.message}")
    for note in diagnostic.notes:
        lines.append(f"   = note: {note}")
    for hint in diagnostic.hints:
        lines.append(f"   = hint: {hint}")
    if explain_hint and has_explanation(diagnostic.code):
        lines.append(f"   = help: {t('diag.explain-footer', code=diagnostic.code)}")
    return "\n".join(lines)


def _caret_width(span: SourceSpan) -> int:
    if span.start_line != span.end_line:
        return 1
    return max(span.end_column - span.start_column, 1)
