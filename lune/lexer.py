from __future__ import annotations

from dataclasses import dataclass

from .tokens import KEYWORDS, LuneSyntaxError, Span, Token, TokenKind
from .messages import t


@dataclass(frozen=True)
class Comment:
    line: int
    own_line: bool  # True if only whitespace precedes the comment on its line
    kind: str  # "line" | "block"
    text: str  # the comment text including its `#` / `###` marker


def scan_comments(source: str, filename: str = "<input>") -> list[Comment]:
    """Collect comments (with positions) from source, for tooling like the formatter."""
    comments: list[Comment] = []
    in_block_comment = False
    for line_number, raw_line in enumerate(source.splitlines(), start=1):
        line = raw_line.rstrip("\r\n")
        _, in_block_comment = _strip_comments(line, in_block_comment, filename, line_number, comments)
    return comments


SINGLE_CHAR_TOKENS = {
    "(": TokenKind.LPAREN,
    ")": TokenKind.RPAREN,
    "[": TokenKind.LBRACKET,
    "]": TokenKind.RBRACKET,
    "{": TokenKind.LBRACE,
    "}": TokenKind.RBRACE,
    ",": TokenKind.COMMA,
    ":": TokenKind.COLON,
    ".": TokenKind.DOT,
    "=": TokenKind.ASSIGN,
    "|": TokenKind.BAR,
    "!": TokenKind.BANG,
    "?": TokenKind.QUESTION,
    "+": TokenKind.PLUS,
    "-": TokenKind.MINUS,
    "*": TokenKind.STAR,
    "/": TokenKind.SLASH,
    "%": TokenKind.PERCENT,
    "<": TokenKind.LT,
    ">": TokenKind.GT,
    "@": TokenKind.AT,
}

MULTI_CHAR_TOKENS = {
    "...": TokenKind.ELLIPSIS,
    "->": TokenKind.ARROW,
    "=>": TokenKind.FAT_ARROW,
    "==": TokenKind.EQEQ,
    "!=": TokenKind.BANGEQ,
    "<=": TokenKind.LTEQ,
    ">=": TokenKind.GTEQ,
    "&&": TokenKind.ANDAND,
    "||": TokenKind.OROR,
    "??": TokenKind.QQ,
    "?.": TokenKind.QUESTION_DOT,
    "|>": TokenKind.PIPE_FORWARD,
    "::": TokenKind.COLON_COLON,
    "++": TokenKind.PLUS_PLUS,
    "+=": TokenKind.PLUS_ASSIGN,
    "-=": TokenKind.MINUS_ASSIGN,
    "*=": TokenKind.STAR_ASSIGN,
    "/=": TokenKind.SLASH_ASSIGN,
    "%=": TokenKind.PERCENT_ASSIGN,
}


def lex(source: str, filename: str = "<input>") -> list[Token]:
    tokens: list[Token] = []
    in_block_comment = False

    for line_number, raw_line in enumerate(source.splitlines(), start=1):
        line = raw_line.rstrip("\r\n")
        processed, in_block_comment = _strip_comments(line, in_block_comment, filename, line_number)
        if not processed.strip():
            continue
        indent = len(processed) - len(processed.lstrip(" "))
        if processed[:indent].find("\t") != -1:
            raise LuneSyntaxError(
                t("lex.tabs-in-indentation"),
                Span(filename, line_number, 1),
                code="LXL0004",
                label=t("lex.use-spaces"),
                hints=[t("lex.replace-tabs")],
            )
        tokens.append(Token(TokenKind.LINE_START, "", Span(filename, line_number, 1), indent))
        _lex_code(processed[indent:], filename, line_number, indent + 1, tokens)
        tokens.append(Token(TokenKind.NEWLINE_RAW, "", Span(filename, line_number, len(line) + 1)))

    if in_block_comment:
        raise LuneSyntaxError(t("lex.unterminated-block-comment"), Span(filename, source.count("\n") + 1, 1), code="LXL0003")
    tokens.append(Token(TokenKind.EOF, "", Span(filename, source.count("\n") + 1, 1)))
    return tokens


def _strip_comments(
    line: str,
    in_block_comment: bool,
    filename: str,
    line_number: int,
    comments: list[Comment] | None = None,
) -> tuple[str, bool]:
    out: list[str] = []
    i = 0
    in_string: str | None = None
    while i < len(line):
        if in_block_comment:
            end = line.find("###", i)
            if end == -1:
                return "".join(out), True
            i = end + 3
            in_block_comment = False
            continue

        ch = line[i]
        if in_string:
            out.append(ch)
            if ch == "\\":
                if i + 1 < len(line):
                    out.append(line[i + 1])
                    i += 2
                    continue
            elif ch == in_string:
                in_string = None
            i += 1
            continue

        if line.startswith("###", i):
            if comments is not None:
                comments.append(Comment(line_number, not "".join(out).strip(), "block", line[i:]))
            in_block_comment = True
            i += 3
            continue
        if ch == "#":
            if comments is not None:
                comments.append(Comment(line_number, not "".join(out).strip(), "line", line[i:].rstrip()))
            break
        if ch in ('"', "'"):
            in_string = ch
        out.append(ch)
        i += 1

    if in_string:
        raise LuneSyntaxError(t("lex.unterminated-string"), Span(filename, line_number, len(line)), code="LXL0002")
    return "".join(out), in_block_comment


def _lex_code(code: str, filename: str, line_number: int, base_column: int, tokens: list[Token]) -> None:
    i = 0
    while i < len(code):
        ch = code[i]
        col = base_column + i
        if ch.isspace():
            i += 1
            continue

        span = Span(filename, line_number, col)

        matched = False
        for text, kind in sorted(MULTI_CHAR_TOKENS.items(), key=lambda item: len(item[0]), reverse=True):
            if code.startswith(text, i):
                tokens.append(Token(kind, text, span))
                i += len(text)
                matched = True
                break
        if matched:
            continue

        if ch == "_":
            if i + 1 < len(code) and _is_ident_part(code[i + 1]):
                end = _read_identifier_end(code, i)
                text = code[i:end]
                tokens.append(Token(TokenKind.IDENT, text, span, text))
                i = end
            else:
                tokens.append(Token(TokenKind.UNDERSCORE, ch, span))
                i += 1
            continue

        if _is_ident_start(ch):
            end = _read_identifier_end(code, i)
            text = code[i:end]
            kind = KEYWORDS.get(text, TokenKind.IDENT)
            value = text if kind == TokenKind.IDENT else None
            tokens.append(Token(kind, text, span, value))
            i = end
            continue

        if ch.isdigit():
            end, is_float = _read_number(code, i)
            text = code[i:end]
            value_text = text.replace("_", "")
            value = float(value_text) if is_float else int(value_text)
            tokens.append(Token(TokenKind.FLOAT_LITERAL if is_float else TokenKind.INT_LITERAL, text, span, value))
            i = end
            continue

        if ch == '"':
            text, value, end = _read_string(code, i, filename, line_number, col)
            tokens.append(Token(TokenKind.STRING_LITERAL, text, span, value))
            i = end
            continue

        if ch == "'":
            text, value, end = _read_string(code, i, filename, line_number, col, quote="'")
            if len(value) != 1:
                raise LuneSyntaxError(t("lex.char-literal-one"), span, code="LXL0002")
            tokens.append(Token(TokenKind.CHAR_LITERAL, text, span, value))
            i = end
            continue

        kind = SINGLE_CHAR_TOKENS.get(ch)
        if kind is not None:
            tokens.append(Token(kind, ch, span))
            i += 1
            continue

        raise LuneSyntaxError(t("lex.unexpected-character", ch=repr(ch)), span, code="LXL0001", label=t("label.unexpected-character"))


def _is_ident_start(ch: str) -> bool:
    return ch.isalpha() or ch == "_"


def _is_ident_part(ch: str) -> bool:
    return ch.isalnum() or ch == "_"


def _read_identifier_end(code: str, start: int) -> int:
    i = start + 1
    while i < len(code) and _is_ident_part(code[i]):
        i += 1
    return i


def _read_number(code: str, start: int) -> tuple[int, bool]:
    i = start
    while i < len(code) and (code[i].isdigit() or code[i] == "_"):
        i += 1
    is_float = False
    if i < len(code) and code[i] == "." and i + 1 < len(code) and code[i + 1].isdigit():
        is_float = True
        i += 1
        while i < len(code) and (code[i].isdigit() or code[i] == "_"):
            i += 1
    if i < len(code) and code[i] in "eE":
        is_float = True
        i += 1
        if i < len(code) and code[i] in "+-":
            i += 1
        while i < len(code) and (code[i].isdigit() or code[i] == "_"):
            i += 1
    return i, is_float


def _read_string(
    code: str,
    start: int,
    filename: str,
    line_number: int,
    column: int,
    quote: str = '"',
) -> tuple[str, str, int]:
    i = start + 1
    value: list[str] = []
    while i < len(code):
        ch = code[i]
        if ch == quote:
            return code[start : i + 1], "".join(value), i + 1
        if ch == "\\":
            if i + 1 >= len(code):
                break
            nxt = code[i + 1]
            escapes = {"n": "\n", "r": "\r", "t": "\t", "\\": "\\", '"': '"', "'": "'", "0": "\0"}
            if nxt in escapes:
                value.append(escapes[nxt])
                i += 2
                continue
        value.append(ch)
        i += 1
    raise LuneSyntaxError(t("lex.unterminated-string"), Span(filename, line_number, column), code="LXL0002")
