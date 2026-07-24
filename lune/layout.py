from __future__ import annotations

from .tokens import LuneSyntaxError, Token, TokenKind
from .messages import t


OPENERS = {TokenKind.LPAREN, TokenKind.LBRACKET, TokenKind.LBRACE}
CLOSERS = {TokenKind.RPAREN, TokenKind.RBRACKET, TokenKind.RBRACE}


def apply_layout(raw_tokens: list[Token]) -> list[Token]:
    output: list[Token] = []
    indent_stack = [0]
    depth = 0
    last_line_start: Token | None = None

    for token in raw_tokens:
        if token.kind == TokenKind.LINE_START:
            last_line_start = token
            if depth == 0:
                indent = int(token.value)
                current = indent_stack[-1]
                if indent > current:
                    indent_stack.append(indent)
                    output.append(Token(TokenKind.INDENT, "", token.span, indent))
                elif indent < current:
                    while len(indent_stack) > 1 and indent < indent_stack[-1]:
                        indent_stack.pop()
                        output.append(Token(TokenKind.DEDENT, "", token.span, indent))
                    if indent_stack[-1] != indent:
                        raise LuneSyntaxError(
                            t("lay.bad-indentation"),
                            token,
                            code="LAY0001",
                            label=t("label.bad-indentation"),
                        )
            continue

        if token.kind == TokenKind.NEWLINE_RAW:
            if depth == 0:
                output.append(Token(TokenKind.NEWLINE, "", token.span))
            continue

        if token.kind == TokenKind.EOF:
            while len(indent_stack) > 1:
                indent_stack.pop()
                span = last_line_start.span if last_line_start else token.span
                output.append(Token(TokenKind.DEDENT, "", span))
            output.append(token)
            break

        if token.kind in OPENERS:
            depth += 1
        elif token.kind in CLOSERS:
            depth -= 1
            if depth < 0:
                raise LuneSyntaxError(t("lay.unmatched-delimiter"), token, code="LAY0002", label=t("label.unmatched-delimiter"))

        output.append(token)

    return output
