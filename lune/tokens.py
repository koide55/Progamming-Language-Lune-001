from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

from .diagnostics import Diagnostic, DiagnosticError, Label, SourceSpan


class TokenKind(Enum):
    EOF = auto()
    LINE_START = auto()
    NEWLINE_RAW = auto()
    NEWLINE = auto()
    INDENT = auto()
    DEDENT = auto()

    IDENT = auto()
    INT_LITERAL = auto()
    FLOAT_LITERAL = auto()
    STRING_LITERAL = auto()
    CHAR_LITERAL = auto()

    MODULE = auto()
    IMPORT = auto()
    AS = auto()
    LET = auto()
    STRICT = auto()
    VAR = auto()
    DEF = auto()
    FN = auto()
    TYPE = auto()
    RECORD = auto()
    CLASS = auto()
    INTERFACE = auto()
    EXTENDS = auto()
    IMPLEMENTS = auto()
    IF = auto()
    ELIF = auto()
    ELSE = auto()
    THEN = auto()
    MATCH = auto()
    WHILE = auto()
    FOR = auto()
    IN = auto()
    TRY = auto()
    CATCH = auto()
    FINALLY = auto()
    RAISE = auto()
    THROW = auto()
    LAZY = auto()
    FORCE = auto()
    SEQ = auto()
    DEEP_FORCE = auto()
    IO_KW = auto()
    PUBLIC = auto()
    PRIVATE = auto()
    PROTECTED = auto()
    INTERNAL = auto()
    STATIC = auto()
    ABSTRACT = auto()
    FINAL = auto()
    OVERRIDE = auto()
    NEW = auto()
    THIS = auto()
    SUPER = auto()
    INIT = auto()
    TRUE = auto()
    FALSE = auto()
    NULL = auto()
    THROWS = auto()

    LPAREN = auto()
    RPAREN = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    LBRACE = auto()
    RBRACE = auto()
    COMMA = auto()
    COLON = auto()
    DOT = auto()
    ASSIGN = auto()
    BAR = auto()
    BANG = auto()
    QUESTION = auto()
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    LT = auto()
    GT = auto()
    AT = auto()
    UNDERSCORE = auto()

    ARROW = auto()
    FAT_ARROW = auto()
    SLASH_SLASH = auto()
    EQEQ = auto()
    BANGEQ = auto()
    LTEQ = auto()
    GTEQ = auto()
    ANDAND = auto()
    OROR = auto()
    QQ = auto()
    QUESTION_DOT = auto()
    PIPE_FORWARD = auto()
    COLON_COLON = auto()
    PLUS_PLUS = auto()
    PLUS_ASSIGN = auto()
    MINUS_ASSIGN = auto()
    STAR_ASSIGN = auto()
    SLASH_ASSIGN = auto()
    SLASH_SLASH_ASSIGN = auto()
    PERCENT_ASSIGN = auto()
    ELLIPSIS = auto()


KEYWORDS = {
    "module": TokenKind.MODULE,
    "import": TokenKind.IMPORT,
    "as": TokenKind.AS,
    "let": TokenKind.LET,
    "strict": TokenKind.STRICT,
    "var": TokenKind.VAR,
    "def": TokenKind.DEF,
    "fn": TokenKind.FN,
    "type": TokenKind.TYPE,
    "record": TokenKind.RECORD,
    "class": TokenKind.CLASS,
    "interface": TokenKind.INTERFACE,
    "extends": TokenKind.EXTENDS,
    "implements": TokenKind.IMPLEMENTS,
    "if": TokenKind.IF,
    "elif": TokenKind.ELIF,
    "else": TokenKind.ELSE,
    "then": TokenKind.THEN,
    "match": TokenKind.MATCH,
    "while": TokenKind.WHILE,
    "for": TokenKind.FOR,
    "in": TokenKind.IN,
    "try": TokenKind.TRY,
    "catch": TokenKind.CATCH,
    "finally": TokenKind.FINALLY,
    "raise": TokenKind.RAISE,
    "throw": TokenKind.THROW,
    "lazy": TokenKind.LAZY,
    "force": TokenKind.FORCE,
    "seq": TokenKind.SEQ,
    "deepForce": TokenKind.DEEP_FORCE,
    "IO": TokenKind.IO_KW,
    "public": TokenKind.PUBLIC,
    "private": TokenKind.PRIVATE,
    "protected": TokenKind.PROTECTED,
    "internal": TokenKind.INTERNAL,
    "static": TokenKind.STATIC,
    "abstract": TokenKind.ABSTRACT,
    "final": TokenKind.FINAL,
    "override": TokenKind.OVERRIDE,
    "new": TokenKind.NEW,
    "this": TokenKind.THIS,
    "super": TokenKind.SUPER,
    "init": TokenKind.INIT,
    "true": TokenKind.TRUE,
    "false": TokenKind.FALSE,
    "null": TokenKind.NULL,
    "throws": TokenKind.THROWS,
}


@dataclass(frozen=True)
class Span:
    filename: str
    line: int
    column: int

    def format(self) -> str:
        return f"{self.filename}:{self.line}:{self.column}"

    def to_source_span(self, width: int = 1) -> SourceSpan:
        return SourceSpan.point(self.filename, self.line, self.column, width)


@dataclass(frozen=True)
class Token:
    kind: TokenKind
    lexeme: str
    span: Span
    value: Any = None

    def is_kind(self, *kinds: TokenKind) -> bool:
        return self.kind in kinds


class LuneSyntaxError(DiagnosticError):
    def __init__(
        self,
        message: str,
        token: Token | Span,
        code: str = "PRS0001",
        label: str | None = None,
        hints: list[str] | None = None,
    ):
        span = token.span if isinstance(token, Token) else token
        width = len(token.lexeme) if isinstance(token, Token) and token.lexeme else 1
        self.span = span
        diagnostic = Diagnostic(
            code=code,
            severity="error",
            message=message,
            primary=Label(span.to_source_span(width), label),
            hints=hints or [],
        )
        super().__init__(diagnostic)
