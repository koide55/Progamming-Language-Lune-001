from __future__ import annotations

from . import nodes as ast
from .layout import apply_layout
from .lexer import lex
from .tokens import LuneSyntaxError, Token, TokenKind
from .messages import t


ASSIGNMENT_OPS = {
    TokenKind.ASSIGN,
    TokenKind.PLUS_ASSIGN,
    TokenKind.MINUS_ASSIGN,
    TokenKind.STAR_ASSIGN,
    TokenKind.SLASH_ASSIGN,
    TokenKind.PERCENT_ASSIGN,
}

INFIX = {
    TokenKind.PIPE_FORWARD: (20, "left"),
    TokenKind.QQ: (25, "right"),
    TokenKind.OROR: (30, "left"),
    TokenKind.ANDAND: (40, "left"),
    TokenKind.EQEQ: (50, "none"),
    TokenKind.BANGEQ: (50, "none"),
    TokenKind.LT: (50, "none"),
    TokenKind.LTEQ: (50, "none"),
    TokenKind.GT: (50, "none"),
    TokenKind.GTEQ: (50, "none"),
    TokenKind.COLON_COLON: (60, "right"),
    TokenKind.PLUS_PLUS: (60, "right"),
    TokenKind.PLUS: (70, "left"),
    TokenKind.MINUS: (70, "left"),
    TokenKind.STAR: (80, "left"),
    TokenKind.SLASH: (80, "left"),
    TokenKind.PERCENT: (80, "left"),
}

PREFIX_BP = 90

EXPR_END = {
    TokenKind.NEWLINE,
    TokenKind.DEDENT,
    TokenKind.EOF,
    TokenKind.RPAREN,
    TokenKind.RBRACKET,
    TokenKind.RBRACE,
    TokenKind.COMMA,
}

LISP_LIST_ITEM_START = {
    TokenKind.IF,
    TokenKind.WHILE,
    TokenKind.FOR,
    TokenKind.MATCH,
    TokenKind.FN,
    TokenKind.LET,
    TokenKind.INT_LITERAL,
    TokenKind.FLOAT_LITERAL,
    TokenKind.STRING_LITERAL,
    TokenKind.CHAR_LITERAL,
    TokenKind.TRUE,
    TokenKind.FALSE,
    TokenKind.NULL,
    TokenKind.THIS,
    TokenKind.SUPER,
    TokenKind.IDENT,
    TokenKind.IO_KW,
    TokenKind.BANG,
    TokenKind.LPAREN,
    TokenKind.LBRACKET,
    TokenKind.LAZY,
    TokenKind.FORCE,
    TokenKind.SEQ,
    TokenKind.DEEP_FORCE,
    TokenKind.RAISE,
    TokenKind.THROW,
    TokenKind.NEW,
}


def parse_source(source: str, filename: str = "<input>") -> ast.ModuleFile:
    return Parser(apply_layout(lex(source, filename))).parse_file()


def token_span(token: Token):
    return token.span.to_source_span(len(token.lexeme) if token.lexeme else 1)


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    def parse_file(self) -> ast.ModuleFile:
        self.skip_newlines()
        start = self.peek()
        module_name = None
        if self.match(TokenKind.MODULE):
            module_name = self.parse_qualified_name()
            self.require_newline()
            self.skip_newlines()

        imports: list[ast.ImportDecl] = []
        while self.peek().kind == TokenKind.IMPORT:
            imports.append(self.parse_import())
            self.skip_newlines()

        declarations: list[ast.Decl] = []
        while self.peek().kind != TokenKind.EOF:
            declarations.append(self.parse_top_decl())
            self.skip_newlines()
        self.expect(TokenKind.EOF)
        return ast.ModuleFile(module_name, imports, declarations, span=token_span(start))

    def parse_import(self) -> ast.ImportDecl:
        start = self.expect(TokenKind.IMPORT)
        path = self.parse_qualified_name()
        alias = None
        if self.match(TokenKind.AS):
            alias = self.expect(TokenKind.IDENT).lexeme
        self.require_newline()
        return ast.ImportDecl(path, alias, span=token_span(start))

    def parse_top_decl(self) -> ast.Decl:
        if self.peek().kind in {TokenKind.PUBLIC, TokenKind.PRIVATE, TokenKind.PROTECTED, TokenKind.INTERNAL, TokenKind.STATIC, TokenKind.ABSTRACT, TokenKind.FINAL, TokenKind.OVERRIDE}:
            self.parse_modifiers()
        if self.peek().kind == TokenKind.DEF:
            return self.parse_function_decl()
        if self.peek().kind in {TokenKind.STRICT, TokenKind.LET}:
            return self.parse_let_decl()
        if self.peek().kind == TokenKind.VAR:
            return self.parse_var_decl()
        if self.peek().kind == TokenKind.TYPE:
            return self.parse_type_decl()
        if self.peek().kind == TokenKind.RECORD:
            return self.parse_record_decl()
        raise self.error(t("prs.expected-top-level", got=self.peek().kind.name))

    def parse_modifiers(self) -> list[str]:
        values = []
        while self.peek().kind in {TokenKind.PUBLIC, TokenKind.PRIVATE, TokenKind.PROTECTED, TokenKind.INTERNAL, TokenKind.STATIC, TokenKind.ABSTRACT, TokenKind.FINAL, TokenKind.OVERRIDE}:
            values.append(self.advance().lexeme)
        return values

    def parse_function_decl(self) -> ast.FunctionDecl:
        start = self.expect(TokenKind.DEF)
        name = self.expect(TokenKind.IDENT).lexeme
        type_params = self.parse_type_params()
        params = self.parse_param_list(require_types=True)
        return_type = self.parse_return_type()
        self.expect(TokenKind.ASSIGN)
        body = self.parse_decl_body()
        return ast.FunctionDecl(name, type_params, params, return_type, body, span=token_span(start))

    def parse_let_decl(self) -> ast.LetDecl:
        start = self.peek()
        is_strict = self.match(TokenKind.STRICT) or self.match(TokenKind.BANG)
        self.expect(TokenKind.LET)
        pattern = self.parse_pattern(stop={TokenKind.COLON, TokenKind.ASSIGN})
        type_node = self.parse_type_annotation()
        self.expect(TokenKind.ASSIGN)
        value = self.parse_decl_body()
        return ast.LetDecl(pattern, type_node, value, is_strict, span=token_span(start))

    def parse_var_decl(self) -> ast.VarDecl:
        start = self.expect(TokenKind.VAR)
        name = self.expect(TokenKind.IDENT).lexeme
        type_node = self.parse_type_annotation()
        self.expect(TokenKind.ASSIGN)
        value = self.parse_decl_body()
        return ast.VarDecl(name, type_node, value, span=token_span(start))

    def parse_type_decl(self) -> ast.TypeDecl:
        start = self.expect(TokenKind.TYPE)
        name = self.expect(TokenKind.IDENT).lexeme
        type_params = self.parse_type_params()
        self.expect(TokenKind.ASSIGN)
        self.expect(TokenKind.NEWLINE)
        self.expect(TokenKind.INDENT)
        constructors: list[ast.Constructor] = []
        self.skip_newlines()
        while self.peek().kind == TokenKind.BAR:
            ctor_start = self.advance()
            ctor_name = self.expect(TokenKind.IDENT).lexeme
            fields = []
            if self.peek().kind == TokenKind.LPAREN:
                fields = self.parse_param_list(require_types=True)
            constructors.append(ast.Constructor(ctor_name, fields, span=token_span(ctor_start)))
            self.require_newline()
            self.skip_newlines()
        self.expect(TokenKind.DEDENT)
        return ast.TypeDecl(name, type_params, constructors, span=token_span(start))

    def parse_record_decl(self) -> ast.RecordDecl:
        start = self.expect(TokenKind.RECORD)
        name = self.expect(TokenKind.IDENT).lexeme
        type_params = self.parse_type_params()
        self.expect(TokenKind.COLON)
        self.expect(TokenKind.NEWLINE)
        self.expect(TokenKind.INDENT)
        fields: list[ast.RecordField] = []
        self.skip_newlines()
        while self.peek().kind not in {TokenKind.DEDENT, TokenKind.EOF}:
            field_start = self.peek()
            is_strict = self.match(TokenKind.BANG) or self.match(TokenKind.STRICT)
            field_name = self.expect(TokenKind.IDENT).lexeme
            self.expect(TokenKind.COLON)
            field_type = self.parse_type()
            fields.append(ast.RecordField(field_name, field_type, is_strict, span=token_span(field_start)))
            self.require_newline()
            self.skip_newlines()
        self.expect(TokenKind.DEDENT)
        return ast.RecordDecl(name, type_params, fields, span=token_span(start))

    def parse_decl_body(self) -> ast.Expr:
        if self.match(TokenKind.NEWLINE):
            self.expect(TokenKind.INDENT)
            block = self.parse_block()
            self.expect(TokenKind.DEDENT)
            return block
        return self.parse_expr()

    def parse_block(self) -> ast.BlockExpr:
        start = self.peek()
        block_column = start.span.column
        items: list[ast.Decl | ast.Expr] = []
        self.skip_newlines()
        while self.peek().kind not in {TokenKind.DEDENT, TokenKind.EOF}:
            if self.peek().kind in {TokenKind.STRICT, TokenKind.LET}:
                item = self.parse_let_decl()
            elif self.peek().kind == TokenKind.VAR:
                item = self.parse_var_decl()
            else:
                item = self.parse_expr()
            items.append(item)
            if self.peek().kind == TokenKind.NEWLINE:
                self.skip_newlines()
            elif self.peek().kind != TokenKind.DEDENT:
                # A nested suite ends with DEDENT, and the layout processor may
                # place the next outer-block token immediately after it.
                if self.peek().span.column != block_column:
                    raise self.error(t("prs.expected-newline"))

        result = items[-1] if items and isinstance(items[-1], ast.Expr) else None
        statements = items[:-1] if result is not None else items
        return ast.BlockExpr(statements, result, span=token_span(start))

    def parse_expr(self, min_bp: int = 0, stop: set[TokenKind] | None = None) -> ast.Expr:
        stop = stop or set()
        left = self.parse_prefix(stop)

        while True:
            token = self.peek()
            if token.kind in stop or token.kind in EXPR_END:
                break

            if token.kind == TokenKind.DOT:
                dot = self.advance()
                name = self.expect(TokenKind.IDENT).lexeme
                left = ast.MemberExpr(left, name, span=getattr(left, "span", None) or token_span(dot))
                continue

            if token.kind == TokenKind.QUESTION_DOT:
                dot = self.advance()
                name = self.expect(TokenKind.IDENT).lexeme
                left = ast.SafeMemberExpr(left, name, span=getattr(left, "span", None) or token_span(dot))
                continue

            if token.kind == TokenKind.LPAREN:
                if not self.is_adjacent_to_previous(token):
                    break
                args = self.parse_argument_list_parens()
                left = ast.CallExpr(left, args, span=getattr(left, "span", None) or token_span(token))
                continue

            if token.kind == TokenKind.LBRACKET:
                if not self.is_adjacent_to_previous(token):
                    break
                bracket = self.advance()
                args = []
                if self.peek().kind != TokenKind.RBRACKET:
                    args.append(self.parse_expr(stop={TokenKind.COMMA, TokenKind.RBRACKET}))
                    while self.match(TokenKind.COMMA):
                        if self.peek().kind == TokenKind.RBRACKET:
                            break
                        args.append(self.parse_expr(stop={TokenKind.COMMA, TokenKind.RBRACKET}))
                self.expect(TokenKind.RBRACKET)
                left = ast.IndexExpr(left, args, span=getattr(left, "span", None) or token_span(bracket))
                continue

            if token.kind in ASSIGNMENT_OPS:
                bp = 10
                if bp < min_bp:
                    break
                op_token = self.advance()
                right = self.parse_expr(bp, stop)
                left = ast.AssignExpr(left, op_token.lexeme, right, span=getattr(left, "span", None) or token_span(op_token))
                continue

            infix = INFIX.get(token.kind)
            if infix is None:
                break
            bp, assoc = infix
            if bp < min_bp:
                break
            op_token = self.advance()
            next_min = bp + 1 if assoc == "left" or assoc == "none" else bp
            right = self.parse_expr(next_min, stop)
            left = ast.BinaryExpr(op_token.lexeme, left, right, span=getattr(left, "span", None) or token_span(op_token))

        return left

    def parse_prefix(self, stop: set[TokenKind]) -> ast.Expr:
        token = self.peek()
        if token.kind == TokenKind.IF:
            return self.parse_if_expr()
        if token.kind == TokenKind.WHILE:
            return self.parse_while_expr()
        if token.kind == TokenKind.FOR:
            return self.parse_for_expr()
        if token.kind == TokenKind.MATCH:
            return self.parse_match_expr()
        if token.kind == TokenKind.FN:
            return self.parse_lambda_expr()
        if token.kind == TokenKind.IO_KW and self.peek(1).kind == TokenKind.COLON:
            return self.parse_io_block_expr()
        if token.kind == TokenKind.LET:
            return self.parse_let_in_expr()

        if token.kind == TokenKind.INT_LITERAL:
            actual = self.advance()
            return ast.LiteralExpr(actual.value, span=token_span(actual))
        if token.kind == TokenKind.FLOAT_LITERAL:
            actual = self.advance()
            return ast.LiteralExpr(actual.value, span=token_span(actual))
        if token.kind == TokenKind.STRING_LITERAL:
            actual = self.advance()
            return ast.LiteralExpr(actual.value, span=token_span(actual))
        if token.kind == TokenKind.CHAR_LITERAL:
            actual = self.advance()
            return ast.LiteralExpr(actual.value, span=token_span(actual))
        if token.kind == TokenKind.TRUE:
            actual = self.advance()
            return ast.LiteralExpr(True, span=token_span(actual))
        if token.kind == TokenKind.FALSE:
            actual = self.advance()
            return ast.LiteralExpr(False, span=token_span(actual))
        if token.kind == TokenKind.NULL:
            actual = self.advance()
            return ast.NullExpr(span=token_span(actual))
        if token.kind == TokenKind.THIS:
            actual = self.advance()
            return ast.ThisExpr(span=token_span(actual))
        if token.kind == TokenKind.SUPER:
            actual = self.advance()
            return ast.SuperExpr(span=token_span(actual))
        if token.kind in {TokenKind.IDENT, TokenKind.IO_KW}:
            actual = self.advance()
            return ast.NameExpr(actual.lexeme, span=token_span(actual))
        if token.kind in {TokenKind.BANG, TokenKind.MINUS}:
            op_token = self.advance()
            return ast.UnaryExpr(op_token.lexeme, self.parse_expr(PREFIX_BP, stop), span=token_span(op_token))
        if token.kind == TokenKind.LPAREN:
            return self.parse_tuple_or_group()
        if token.kind == TokenKind.LBRACKET:
            return self.parse_list_expr()
        if token.kind == TokenKind.LAZY:
            return self.parse_lazy_expr()
        if token.kind == TokenKind.FORCE:
            start = self.advance()
            return ast.ForceExpr(self.parse_expr(PREFIX_BP, stop), span=token_span(start))
        if token.kind == TokenKind.SEQ:
            start = self.advance()
            return ast.SeqExpr(self.parse_expr(PREFIX_BP, stop), self.parse_expr(PREFIX_BP, stop), span=token_span(start))
        if token.kind == TokenKind.DEEP_FORCE:
            start = self.advance()
            return ast.DeepForceExpr(self.parse_expr(PREFIX_BP, stop), span=token_span(start))
        if token.kind in {TokenKind.RAISE, TokenKind.THROW}:
            start = self.advance()
            return ast.RaiseExpr(self.parse_expr(stop=stop), span=token_span(start))
        if token.kind == TokenKind.NEW:
            start = self.advance()
            type_node = self.parse_type()
            args = self.parse_argument_list_parens()
            return ast.NewExpr(type_node, args, span=token_span(start))
        raise self.error(t("prs.expected-expression", got=token.kind.name))

    def parse_if_expr(self) -> ast.IfExpr:
        start = self.expect(TokenKind.IF)
        condition = self.parse_expr(stop={TokenKind.COLON, TokenKind.THEN})
        if self.match(TokenKind.THEN):
            then_branch = self.parse_expr(stop={TokenKind.ELSE})
            self.expect(TokenKind.ELSE)
            else_branch = self.parse_expr()
            return ast.IfExpr(condition, then_branch, [], else_branch, span=token_span(start))
        self.expect(TokenKind.COLON)
        then_branch = self.parse_suite()
        elifs: list[tuple[ast.Expr, ast.Expr]] = []
        while self.match(TokenKind.ELIF):
            cond = self.parse_expr(stop={TokenKind.COLON})
            self.expect(TokenKind.COLON)
            body = self.parse_suite()
            elifs.append((cond, body))
        else_branch = None
        if self.match(TokenKind.ELSE):
            self.expect(TokenKind.COLON)
            else_branch = self.parse_suite()
        return ast.IfExpr(condition, then_branch, elifs, else_branch, span=token_span(start))

    def parse_while_expr(self) -> ast.WhileExpr:
        start = self.expect(TokenKind.WHILE)
        condition = self.parse_expr(stop={TokenKind.COLON})
        self.expect(TokenKind.COLON)
        body = self.parse_suite()
        return ast.WhileExpr(condition, body, span=token_span(start))

    def parse_for_expr(self) -> ast.ForExpr:
        start = self.expect(TokenKind.FOR)
        pattern = self.parse_pattern(stop={TokenKind.IN})
        self.expect(TokenKind.IN)
        iterable = self.parse_expr(stop={TokenKind.COLON})
        self.expect(TokenKind.COLON)
        body = self.parse_suite()
        return ast.ForExpr(pattern, iterable, body, span=token_span(start))

    def parse_match_expr(self) -> ast.MatchExpr:
        start = self.expect(TokenKind.MATCH)
        scrutinee = self.parse_expr(stop={TokenKind.COLON})
        self.expect(TokenKind.COLON)
        self.expect(TokenKind.NEWLINE)
        self.expect(TokenKind.INDENT)
        cases: list[ast.MatchCase] = []
        self.skip_newlines()
        while self.peek().kind == TokenKind.BAR:
            case_start = self.advance()
            pattern = self.parse_pattern(stop={TokenKind.IF, TokenKind.ARROW, TokenKind.BAR})
            guard = None
            if self.match(TokenKind.IF):
                guard = self.parse_expr(stop={TokenKind.ARROW})
            self.expect(TokenKind.ARROW)
            if self.peek().kind == TokenKind.NEWLINE:
                body = self.parse_suite_after_arrow()
            else:
                body = self.parse_expr()
            cases.append(ast.MatchCase(pattern, guard, body, span=token_span(case_start)))
            self.require_newline()
            self.skip_newlines()
        self.expect(TokenKind.DEDENT)
        return ast.MatchExpr(scrutinee, cases, span=token_span(start))

    def parse_lambda_expr(self) -> ast.LambdaExpr:
        start = self.expect(TokenKind.FN)
        params: list[ast.Param] = []
        if self.peek().kind == TokenKind.LPAREN:
            params = self.parse_param_list(require_types=False)
        else:
            while self.peek().kind in {TokenKind.IDENT, TokenKind.BANG, TokenKind.STRICT}:
                strict = self.match(TokenKind.BANG) or self.match(TokenKind.STRICT)
                name_token = self.expect(TokenKind.IDENT)
                type_node = self.parse_lambda_param_type_annotation()
                params.append(ast.Param(name_token.lexeme, type_node, strict, span=token_span(name_token)))
        self.expect(TokenKind.ARROW)
        body = self.parse_suite_after_arrow() if self.peek().kind == TokenKind.NEWLINE else self.parse_expr()
        return ast.LambdaExpr(params, body, span=token_span(start))

    def parse_io_block_expr(self) -> ast.IOBlockExpr:
        start = self.expect(TokenKind.IO_KW)
        self.expect(TokenKind.COLON)
        return ast.IOBlockExpr(self.parse_suite(), span=token_span(start))

    def parse_let_in_expr(self) -> ast.Expr:
        start = self.expect(TokenKind.LET)
        pattern = self.parse_pattern(stop={TokenKind.COLON, TokenKind.ASSIGN})
        type_node = self.parse_type_annotation()
        self.expect(TokenKind.ASSIGN)
        value = self.parse_expr(stop={TokenKind.IN})
        self.expect(TokenKind.IN)
        body = self.parse_expr()
        return ast.BlockExpr([ast.LetDecl(pattern, type_node, value, span=token_span(start))], body, span=token_span(start))

    def parse_lazy_expr(self) -> ast.LazyExpr:
        start = self.expect(TokenKind.LAZY)
        if self.match(TokenKind.COLON):
            return ast.LazyExpr(self.parse_suite(), span=token_span(start))
        return ast.LazyExpr(self.parse_expr(PREFIX_BP), span=token_span(start))

    def parse_tuple_or_group(self) -> ast.Expr:
        start = self.expect(TokenKind.LPAREN)
        if self.match(TokenKind.RPAREN):
            return ast.LiteralExpr((), span=token_span(start))
        first = self.parse_expr(stop={TokenKind.COMMA, TokenKind.RPAREN})
        if self.peek().kind in LISP_LIST_ITEM_START:
            items = [first]
            item_stop = {TokenKind.RPAREN, *LISP_LIST_ITEM_START}
            while self.peek().kind != TokenKind.RPAREN:
                items.append(self.parse_expr(stop=item_stop))
            self.expect(TokenKind.RPAREN)
            return ast.ListExpr(items, span=token_span(start))
        if not self.match(TokenKind.COMMA):
            self.expect(TokenKind.RPAREN)
            return first
        items = [first]
        while self.peek().kind != TokenKind.RPAREN:
            items.append(self.parse_expr(stop={TokenKind.COMMA, TokenKind.RPAREN}))
            if not self.match(TokenKind.COMMA):
                break
        self.expect(TokenKind.RPAREN)
        tuple_name = ast.NameExpr("__tuple__", span=token_span(start))
        return ast.CallExpr(tuple_name, [ast.Argument(item, span=getattr(item, "span", None)) for item in items], span=token_span(start))

    def parse_list_expr(self) -> ast.ListExpr:
        start = self.expect(TokenKind.LBRACKET)
        items: list[ast.Expr] = []
        if self.peek().kind != TokenKind.RBRACKET:
            items.append(self.parse_expr(stop={TokenKind.COMMA, TokenKind.RBRACKET}))
            while self.match(TokenKind.COMMA):
                if self.peek().kind == TokenKind.RBRACKET:
                    break
                items.append(self.parse_expr(stop={TokenKind.COMMA, TokenKind.RBRACKET}))
        self.expect(TokenKind.RBRACKET)
        return ast.ListExpr(items, span=token_span(start))

    def parse_argument_list_parens(self) -> list[ast.Argument]:
        self.expect(TokenKind.LPAREN)
        args: list[ast.Argument] = []
        if self.peek().kind != TokenKind.RPAREN:
            args.append(self.parse_argument())
            while self.match(TokenKind.COMMA):
                if self.peek().kind == TokenKind.RPAREN:
                    break
                args.append(self.parse_argument())
        self.expect(TokenKind.RPAREN)
        return args

    def parse_argument(self) -> ast.Argument:
        if self.peek().kind == TokenKind.IDENT and self.peek(1).kind == TokenKind.ASSIGN:
            start = self.advance()
            self.expect(TokenKind.ASSIGN)
            return ast.Argument(self.parse_expr(stop={TokenKind.COMMA, TokenKind.RPAREN}), start.lexeme, span=token_span(start))
        value = self.parse_expr(stop={TokenKind.COMMA, TokenKind.RPAREN})
        return ast.Argument(value, span=getattr(value, "span", None))

    def parse_suite(self) -> ast.BlockExpr:
        self.expect(TokenKind.NEWLINE)
        self.expect(TokenKind.INDENT)
        block = self.parse_block()
        self.expect(TokenKind.DEDENT)
        return block

    def parse_suite_after_arrow(self) -> ast.BlockExpr:
        self.expect(TokenKind.NEWLINE)
        self.expect(TokenKind.INDENT)
        block = self.parse_block()
        self.expect(TokenKind.DEDENT)
        return block

    def parse_pattern(self, stop: set[TokenKind] | None = None) -> ast.Pattern:
        stop = stop or set()
        patterns = [self.parse_typed_pattern(stop | {TokenKind.BAR})]
        while self.peek().kind == TokenKind.BAR and TokenKind.BAR not in stop:
            self.advance()
            patterns.append(self.parse_typed_pattern(stop | {TokenKind.BAR}))
        if len(patterns) == 1:
            return patterns[0]
        return ast.OrPattern(patterns, span=getattr(patterns[0], "span", None))

    def parse_typed_pattern(self, stop: set[TokenKind]) -> ast.Pattern:
        pattern = self.parse_pattern_atom(stop)
        if self.peek().kind == TokenKind.COLON and TokenKind.COLON not in stop:
            self.advance()
            pattern = ast.TypedPattern(pattern, self.parse_type(), span=getattr(pattern, "span", None))
        return pattern

    def parse_pattern_atom(self, stop: set[TokenKind]) -> ast.Pattern:
        token = self.peek()
        if token.kind == TokenKind.UNDERSCORE:
            actual = self.advance()
            return ast.WildcardPattern(span=token_span(actual))
        if token.kind == TokenKind.NULL:
            actual = self.advance()
            return ast.NullPattern(span=token_span(actual))
        if token.kind in {TokenKind.INT_LITERAL, TokenKind.FLOAT_LITERAL, TokenKind.STRING_LITERAL, TokenKind.CHAR_LITERAL}:
            actual = self.advance()
            return ast.LiteralPattern(actual.value, span=token_span(actual))
        if token.kind == TokenKind.TRUE:
            actual = self.advance()
            return ast.LiteralPattern(True, span=token_span(actual))
        if token.kind == TokenKind.FALSE:
            actual = self.advance()
            return ast.LiteralPattern(False, span=token_span(actual))
        if token.kind == TokenKind.LPAREN:
            start = self.advance()
            first = self.parse_pattern(stop={TokenKind.COMMA, TokenKind.RPAREN})
            if not self.match(TokenKind.COMMA):
                self.expect(TokenKind.RPAREN)
                return first
            items = [first]
            while self.peek().kind != TokenKind.RPAREN:
                items.append(self.parse_pattern(stop={TokenKind.COMMA, TokenKind.RPAREN}))
                if not self.match(TokenKind.COMMA):
                    break
            self.expect(TokenKind.RPAREN)
            return ast.TuplePattern(items, span=token_span(start))
        if token.kind == TokenKind.IDENT:
            start = token
            name = self.parse_qualified_name()
            if self.peek().kind == TokenKind.LPAREN:
                self.advance()
                args: list[ast.Pattern] = []
                if self.peek().kind != TokenKind.RPAREN:
                    args.append(self.parse_pattern(stop={TokenKind.COMMA, TokenKind.RPAREN}))
                    while self.match(TokenKind.COMMA):
                        if self.peek().kind == TokenKind.RPAREN:
                            break
                        args.append(self.parse_pattern(stop={TokenKind.COMMA, TokenKind.RPAREN}))
                self.expect(TokenKind.RPAREN)
                return ast.ConstructorPattern(name, args, span=token_span(start))
            if name[:1].isupper():
                return ast.ConstructorPattern(name, [], span=token_span(start))
            return ast.NamePattern(name, span=token_span(start))
        raise self.error(t("prs.expected-pattern", got=token.kind.name))

    def parse_type(self) -> ast.TypeNode:
        left = self.parse_type_atom()
        if self.match(TokenKind.ARROW):
            return ast.FunctionType([left], self.parse_type(), span=getattr(left, "span", None))
        return left

    def parse_type_atom(self) -> ast.TypeNode:
        start = self.peek()
        if self.match(TokenKind.LPAREN):
            if self.match(TokenKind.RPAREN):
                node: ast.TypeNode = ast.TupleType([], span=token_span(start))
            else:
                first = self.parse_type()
                if self.match(TokenKind.COMMA):
                    items = [first]
                    while self.peek().kind != TokenKind.RPAREN:
                        items.append(self.parse_type())
                        if not self.match(TokenKind.COMMA):
                            break
                    self.expect(TokenKind.RPAREN)
                    node = ast.TupleType(items, span=token_span(start))
                else:
                    self.expect(TokenKind.RPAREN)
                    node = first
        else:
            node = ast.TypeName(self.parse_qualified_name(), span=token_span(start))

        while self.peek().kind in {TokenKind.LBRACKET, TokenKind.QUESTION}:
            if self.match(TokenKind.LBRACKET):
                args = [self.parse_type()]
                while self.match(TokenKind.COMMA):
                    if self.peek().kind == TokenKind.RBRACKET:
                        break
                    args.append(self.parse_type())
                self.expect(TokenKind.RBRACKET)
                node = ast.TypeApply(node, args, span=getattr(node, "span", None))
            elif self.match(TokenKind.QUESTION):
                node = ast.NullableType(node, span=getattr(node, "span", None))
        return node

    def parse_type_params(self) -> list[str]:
        if not self.match(TokenKind.LBRACKET):
            return []
        params = [self.expect(TokenKind.IDENT).lexeme]
        while self.match(TokenKind.COMMA):
            if self.peek().kind == TokenKind.RBRACKET:
                break
            params.append(self.expect(TokenKind.IDENT).lexeme)
        self.expect(TokenKind.RBRACKET)
        return params

    def parse_param_list(self, require_types: bool) -> list[ast.Param]:
        self.expect(TokenKind.LPAREN)
        params: list[ast.Param] = []
        if self.peek().kind != TokenKind.RPAREN:
            params.append(self.parse_param(require_types))
            while self.match(TokenKind.COMMA):
                if self.peek().kind == TokenKind.RPAREN:
                    break
                params.append(self.parse_param(require_types))
        self.expect(TokenKind.RPAREN)
        return params

    def parse_param(self, require_type: bool) -> ast.Param:
        strict = self.match(TokenKind.BANG) or self.match(TokenKind.STRICT)
        name_token = self.expect(TokenKind.IDENT)
        type_node = self.parse_type_annotation()
        if require_type and type_node is None:
            raise self.error(t("prs.param-annotation"))
        return ast.Param(name_token.lexeme, type_node, strict, span=token_span(name_token))

    def parse_return_type(self) -> ast.TypeNode | None:
        return self.parse_type_annotation()

    def parse_type_annotation(self) -> ast.TypeNode | None:
        if self.match(TokenKind.COLON):
            return self.parse_type()
        return None

    def parse_lambda_param_type_annotation(self) -> ast.TypeNode | None:
        if self.match(TokenKind.COLON):
            return self.parse_type_atom()
        return None

    def parse_qualified_name(self) -> str:
        if self.peek().kind == TokenKind.IO_KW:
            parts = [self.advance().lexeme]
        else:
            parts = [self.expect(TokenKind.IDENT).lexeme]
        while self.match(TokenKind.DOT):
            parts.append(self.expect(TokenKind.IDENT).lexeme)
        return ".".join(parts)

    def skip_newlines(self) -> None:
        while self.match(TokenKind.NEWLINE):
            pass

    def require_newline(self) -> None:
        if self.peek().kind in {TokenKind.EOF, TokenKind.DEDENT}:
            return
        self.expect(TokenKind.NEWLINE)

    def match(self, kind: TokenKind) -> bool:
        if self.peek().kind == kind:
            self.advance()
            return True
        return False

    def is_adjacent_to_previous(self, token: Token) -> bool:
        if self.pos == 0:
            return False
        previous = self.tokens[self.pos - 1]
        if previous.span.line != token.span.line:
            return False
        return token.span.column == previous.span.column + len(previous.lexeme)

    def expect(self, kind: TokenKind) -> Token:
        token = self.peek()
        if token.kind != kind:
            raise LuneSyntaxError(
                t("prs.expected-token", expected=kind.name, got=token.kind.name),
                token,
                code="PRS0002",
                label=t("label.expected-token", expected=kind.name),
            )
        return self.advance()

    def advance(self) -> Token:
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def peek(self, offset: int = 0) -> Token:
        idx = min(self.pos + offset, len(self.tokens) - 1)
        return self.tokens[idx]

    def error(self, message: str) -> LuneSyntaxError:
        return LuneSyntaxError(message, self.peek(), code="PRS0001", label=t("label.unexpected-token"))
