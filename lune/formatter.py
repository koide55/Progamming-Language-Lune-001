"""Canonical source formatter for Lune (`lune fmt`).

Strategy: parse to AST, pretty-print the AST back to canonical source, then
re-parse the result and check the AST is unchanged (spans aside) so formatting
can never alter a program's meaning. `#` line comments are preserved; a file
containing `###` block comments is refused rather than risk dropping them.
"""

from __future__ import annotations

import dataclasses
import json

from . import nodes as ast
from .lexer import scan_comments
from .parser import parse_source

INDENT = "    "
MAX_WIDTH = 88


class FormatError(Exception):
    pass


# Operator precedence for parenthesization (higher binds tighter), mirroring
# the parser's INFIX table.
_PREC = {
    "|>": 20,
    "??": 25,
    "||": 30,
    "&&": 40,
    "==": 50, "!=": 50, "<": 50, "<=": 50, ">": 50, ">=": 50,
    "::": 60, "++": 60,
    "+": 70, "-": 70,
    "*": 80, "/": 80, "%": 80,
}
_RIGHT_ASSOC = {"??", "::", "++"}
_NON_ASSOC = {"==", "!=", "<", "<=", ">", ">="}
_UNARY_PREC = 90
_POSTFIX_PREC = 100
_ATOM_PREC = 1000


def format_source(source: str, filename: str = "<input>") -> str:
    comments = scan_comments(source, filename)
    if any(c.kind == "block" for c in comments):
        raise FormatError("lune fmt does not support `###` block comments yet")
    module = parse_source(source, filename)
    line_comments = [c for c in comments if c.kind == "line"]
    result = Formatter(line_comments, source.splitlines()).format_module(module)
    _verify(module, result, filename)
    return result


def is_formatted(source: str, filename: str = "<input>") -> bool:
    return format_source(source, filename) == source


def _verify(original: ast.ModuleFile, formatted: str, filename: str) -> None:
    try:
        reparsed = parse_source(formatted, filename)
    except Exception as exc:  # pragma: no cover - defensive
        raise FormatError(f"formatter produced invalid source: {exc}") from exc
    if _strip_spans(original) != _strip_spans(reparsed):
        raise FormatError("formatter changed the program's meaning (internal bug)")


def _strip_spans(node):
    """Recursively rebuild a node/value with all `span` fields dropped.

    A block with no statements is normalized to its result expression: the two
    are semantically identical, but the parser produces a bare expression for an
    inline body (`= e`) and a `BlockExpr` for an indented one (`=` then `e`), and
    the formatter canonicalizes to the indented form. Treating them as equal lets
    the meaning-preservation check accept that reshaping.
    """
    if isinstance(node, ast.BlockExpr) and not node.statements and node.result is not None:
        return _strip_spans(node.result)
    if isinstance(node, ast.Node):
        values = {}
        for f in dataclasses.fields(node):
            if f.name == "span":
                continue
            values[f.name] = _strip_spans(getattr(node, f.name))
        return (type(node).__name__, tuple(sorted(values.items())))
    if isinstance(node, (list, tuple)):
        return tuple(_strip_spans(item) for item in node)
    return node


class Formatter:
    def __init__(self, comments, source_lines):
        self.lines: list[str] = []
        self.comments = sorted(comments, key=lambda c: c.line)
        self.ci = 0
        self.source_lines = source_lines

    def _had_blank_between(self, after: int, before: int | None) -> bool:
        """True if the original source has a blank line strictly between two lines."""
        if before is None:
            return False
        for line_no in range(after + 1, before):
            if 1 <= line_no <= len(self.source_lines) and not self.source_lines[line_no - 1].strip():
                return True
        return False

    # -- output helpers -------------------------------------------------
    def emit(self, indent: int, text: str) -> None:
        self.lines.append(f"{INDENT * indent}{text}" if text else "")

    def blank(self) -> None:
        if self.lines and self.lines[-1] != "":
            self.lines.append("")

    # -- comment interleaving -------------------------------------------
    def flush_leading(self, indent: int, before_line: int | None) -> None:
        if before_line is None:
            return
        while self.ci < len(self.comments) and self.comments[self.ci].line < before_line:
            self.emit(indent, self.comments[self.ci].text)
            self.ci += 1

    def attach_trailing(self, line_index: int, at_line: int | None) -> None:
        if at_line is None:
            return
        if self.ci < len(self.comments) and self.comments[self.ci].line == at_line and not self.comments[self.ci].own_line:
            self.lines[line_index] = f"{self.lines[line_index]}  {self.comments[self.ci].text}"
            self.ci += 1

    def flush_remaining(self, indent: int) -> None:
        while self.ci < len(self.comments):
            self.emit(indent, self.comments[self.ci].text)
            self.ci += 1

    # -- module ---------------------------------------------------------
    def format_module(self, module: ast.ModuleFile) -> str:
        if module.module_name is not None:
            self.emit(0, f"module {module.module_name}")
        for imp in module.imports:
            self.flush_leading(0, _line(imp))
            idx = len(self.lines)
            alias = f" as {imp.alias}" if imp.alias else ""
            self.emit(0, f"import {imp.path}{alias}")
            self.attach_trailing(idx, _line(imp))
        if (module.module_name is not None or module.imports) and module.declarations:
            self.blank()
        for i, decl in enumerate(module.declarations):
            if i > 0 and self._had_blank_between(_max_line(module.declarations[i - 1]), _line(decl)):
                self.blank()
            self.emit_decl(decl, 0)
        self.flush_remaining(0)
        text = "\n".join(self.lines).rstrip("\n")
        return text + "\n" if text else ""

    # -- declarations ---------------------------------------------------
    def emit_decl(self, decl: ast.Decl, indent: int) -> None:
        self.flush_leading(indent, _line(decl))
        idx = len(self.lines)
        if isinstance(decl, ast.FunctionDecl):
            self._emit_function(decl, indent)
        elif isinstance(decl, ast.LetDecl):
            self._emit_let(decl, indent)
        elif isinstance(decl, ast.VarDecl):
            self._emit_var(decl, indent)
        elif isinstance(decl, ast.TypeDecl):
            self._emit_type(decl, indent)
        elif isinstance(decl, ast.RecordDecl):
            self._emit_record(decl, indent)
        else:
            raise FormatError(f"cannot format declaration {type(decl).__name__}")
        self.attach_trailing(idx, _line(decl))

    def _type_params(self, params: list[str]) -> str:
        return f"[{', '.join(params)}]" if params else ""

    def _emit_function(self, decl: ast.FunctionDecl, indent: int) -> None:
        params = ", ".join(self._param(p) for p in decl.params)
        ret = f": {self.render_type(decl.return_type)}" if decl.return_type is not None else ""
        self.emit(indent, f"def {decl.name}{self._type_params(decl.type_params)}({params}){ret} =")
        self.emit_body(decl.body, indent + 1)

    def _emit_let(self, decl: ast.LetDecl, indent: int) -> None:
        head = "strict let " if decl.is_strict else "let "
        pat = self.render_pattern(decl.pattern)
        annot = f": {self.render_type(decl.type)}" if decl.type is not None else ""
        self.emit_binding(f"{head}{pat}{annot}", decl.value, indent)

    def _emit_var(self, decl: ast.VarDecl, indent: int) -> None:
        annot = f": {self.render_type(decl.type)}" if decl.type is not None else ""
        self.emit_binding(f"var {decl.name}{annot}", decl.value, indent)

    def emit_binding(self, prefix: str, value: ast.Expr, indent: int) -> None:
        if _is_block(value):
            self.emit(indent, f"{prefix} =")
            self.emit_body(value, indent + 1)
            return
        inline = f"{prefix} = {self.render(value)}"
        if isinstance(value, ast.ListExpr) and value.items and len(INDENT * indent + inline) > MAX_WIDTH:
            self.emit_list_multiline(value, indent, f"{prefix} = ")
        else:
            self.emit(indent, inline)

    def emit_list_multiline(self, value: ast.ListExpr, indent: int, prefix: str = "") -> None:
        self.emit(indent, f"{prefix}[")
        for item in value.items:
            self.emit(indent + 1, f"{self.render(item)},")
        self.emit(indent, "]")

    def _emit_type(self, decl: ast.TypeDecl, indent: int) -> None:
        self.emit(indent, f"type {decl.name}{self._type_params(decl.type_params)} =")
        for ctor in decl.constructors:
            if ctor.fields:
                fields = ", ".join(self._param(f) for f in ctor.fields)
                self.emit(indent + 1, f"| {ctor.name}({fields})")
            else:
                self.emit(indent + 1, f"| {ctor.name}")

    def _emit_record(self, decl: ast.RecordDecl, indent: int) -> None:
        self.emit(indent, f"record {decl.name}{self._type_params(decl.type_params)}:")
        for f in decl.fields:
            strict = "strict " if f.is_strict else ""
            self.emit(indent + 1, f"{strict}{f.name}: {self.render_type(f.type)}")

    def _param(self, p: ast.Param) -> str:
        strict = "strict " if p.is_strict else ""
        annot = f": {self.render_type(p.type)}" if p.type is not None else ""
        return f"{strict}{p.name}{annot}"

    # -- statement / body emission --------------------------------------
    def emit_body(self, expr: ast.Expr, indent: int) -> None:
        """Emit an expression in body/statement position (may be multi-line)."""
        if isinstance(expr, ast.BlockExpr):
            self.emit_block_body(expr, indent)
        elif isinstance(expr, ast.MatchExpr):
            self.emit_match(expr, indent)
        elif isinstance(expr, ast.IfExpr) and _if_is_block(expr):
            self.emit_if(expr, indent)
        elif isinstance(expr, ast.WhileExpr):
            self.emit_while(expr, indent)
        elif isinstance(expr, ast.ForExpr):
            self.emit_for(expr, indent)
        elif isinstance(expr, ast.IOBlockExpr):
            self.emit(indent, "IO:")
            self.emit_block_body(expr.body, indent + 1)
        elif isinstance(expr, ast.LazyExpr) and _is_block(expr.body):
            self.emit(indent, "lazy:")
            self.emit_body(expr.body, indent + 1)
        elif isinstance(expr, ast.ListExpr) and expr.items and len(INDENT * indent + self.render(expr)) > MAX_WIDTH:
            self.emit_list_multiline(expr, indent)
        else:
            self.emit(indent, self.render(expr))

    def emit_block_body(self, block: ast.BlockExpr, indent: int) -> None:
        prev = None
        for stmt in block.statements:
            if prev is not None and self._had_blank_between(_max_line(prev), _line(stmt)):
                self.blank()
            if isinstance(stmt, ast.Decl):
                self.emit_decl(stmt, indent)
            else:
                self.emit_stmt_expr(stmt, indent)
            prev = stmt
        if block.result is not None:
            if prev is not None and self._had_blank_between(_max_line(prev), _line(block.result)):
                self.blank()
            self.emit_stmt_expr(block.result, indent)

    def emit_stmt_expr(self, expr: ast.Expr, indent: int) -> None:
        self.flush_leading(indent, _line(expr))
        idx = len(self.lines)
        self.emit_body(expr, indent)
        self.attach_trailing(idx, _line(expr))

    def emit_match(self, expr: ast.MatchExpr, indent: int) -> None:
        self.emit(indent, f"match {self.render(expr.scrutinee)}:")
        for case in expr.cases:
            self.flush_leading(indent + 1, _line(case))
            guard = f" if {self.render(case.guard)}" if case.guard is not None else ""
            head = f"| {self.render_pattern(case.pattern)}{guard} ->"
            if _is_block(case.body):
                self.emit(indent + 1, head)
                self.emit_body(case.body, indent + 2)
            else:
                idx = len(self.lines)
                self.emit(indent + 1, f"{head} {self.render(case.body)}")
                self.attach_trailing(idx, _line(case))

    def emit_if(self, expr: ast.IfExpr, indent: int) -> None:
        self.emit(indent, f"if {self.render(expr.condition)}:")
        self.emit_body(expr.then_branch, indent + 1)
        for cond, branch in expr.elif_branches:
            self.emit(indent, f"elif {self.render(cond)}:")
            self.emit_body(branch, indent + 1)
        if expr.else_branch is not None:
            self.emit(indent, "else:")
            self.emit_body(expr.else_branch, indent + 1)

    def emit_while(self, expr: ast.WhileExpr, indent: int) -> None:
        self.emit(indent, f"while {self.render(expr.condition)}:")
        self.emit_block_body(expr.body, indent + 1)

    def emit_for(self, expr: ast.ForExpr, indent: int) -> None:
        self.emit(indent, f"for {self.render_pattern(expr.pattern)} in {self.render(expr.iterable)}:")
        self.emit_block_body(expr.body, indent + 1)

    # -- inline expression rendering ------------------------------------
    def render(self, expr: ast.Expr, min_prec: int = 0) -> str:
        text, prec = self._render(expr)
        return f"({text})" if prec < min_prec else text

    def _render(self, expr: ast.Expr) -> tuple[str, int]:
        if isinstance(expr, ast.LiteralExpr):
            return _render_literal(expr.value), _ATOM_PREC
        if isinstance(expr, ast.NameExpr):
            return expr.name, _ATOM_PREC
        if isinstance(expr, ast.NullExpr):
            return "null", _ATOM_PREC
        if isinstance(expr, ast.ThisExpr):
            return "this", _ATOM_PREC
        if isinstance(expr, ast.SuperExpr):
            return "super", _ATOM_PREC
        if isinstance(expr, ast.ListExpr):
            return "[" + ", ".join(self.render(item) for item in expr.items) + "]", _ATOM_PREC
        if isinstance(expr, ast.CallExpr):
            if isinstance(expr.callee, ast.NameExpr) and expr.callee.name == "__tuple__":
                return "(" + ", ".join(self.render(a.value) for a in expr.args) + ")", _ATOM_PREC
            args = ", ".join(self._argument(a) for a in expr.args)
            return f"{self.render(expr.callee, _POSTFIX_PREC)}({args})", _POSTFIX_PREC
        if isinstance(expr, ast.MemberExpr):
            return f"{self.render(expr.receiver, _POSTFIX_PREC)}.{expr.name}", _POSTFIX_PREC
        if isinstance(expr, ast.SafeMemberExpr):
            return f"{self.render(expr.receiver, _POSTFIX_PREC)}?.{expr.name}", _POSTFIX_PREC
        if isinstance(expr, ast.IndexExpr):
            args = ", ".join(self.render(a) for a in expr.args)
            return f"{self.render(expr.receiver, _POSTFIX_PREC)}[{args}]", _POSTFIX_PREC
        if isinstance(expr, ast.UnaryExpr):
            return f"{expr.op}{self.render(expr.expr, _UNARY_PREC)}", _UNARY_PREC
        if isinstance(expr, ast.BinaryExpr):
            return self._render_binary(expr), _PREC[expr.op]
        if isinstance(expr, ast.AssignExpr):
            return f"{self.render(expr.target)} {expr.op} {self.render(expr.value)}", 5
        if isinstance(expr, ast.LambdaExpr):
            params = " ".join(self._param(p) for p in expr.params)
            head = f"fn {params} ->" if params else "fn ->"
            return f"{head} {self.render(expr.body)}", 5
        if isinstance(expr, ast.IfExpr) and not _if_is_block(expr):
            else_branch = self.render(expr.else_branch) if expr.else_branch is not None else "()"
            return f"if {self.render(expr.condition)} then {self.render(expr.then_branch)} else {else_branch}", 5
        if isinstance(expr, ast.ForceExpr):
            return f"force {self.render(expr.expr, _UNARY_PREC)}", _UNARY_PREC
        if isinstance(expr, ast.DeepForceExpr):
            return f"deepForce {self.render(expr.expr, _UNARY_PREC)}", _UNARY_PREC
        if isinstance(expr, ast.SeqExpr):
            return f"seq {self.render(expr.first, _UNARY_PREC)} {self.render(expr.second, _UNARY_PREC)}", _UNARY_PREC
        if isinstance(expr, ast.RaiseExpr):
            return f"raise {self.render(expr.expr)}", 5
        if isinstance(expr, ast.LazyExpr) and not _is_block(expr.body):
            return f"lazy {self.render(expr.body, _UNARY_PREC)}", _UNARY_PREC
        if isinstance(expr, ast.NewExpr):
            args = ", ".join(self._argument(a) for a in expr.args)
            return f"new {self.render_type(expr.type)}({args})", _POSTFIX_PREC
        raise FormatError(f"cannot inline-render {type(expr).__name__}")

    def _render_binary(self, expr: ast.BinaryExpr) -> str:
        prec = _PREC[expr.op]
        left_bump = 1 if (expr.op in _RIGHT_ASSOC or expr.op in _NON_ASSOC) else 0
        right_bump = 0 if (expr.op in _RIGHT_ASSOC) else 1
        left = self.render(expr.left, prec + left_bump)
        right = self.render(expr.right, prec + right_bump)
        return f"{left} {expr.op} {right}"

    def _argument(self, arg: ast.Argument) -> str:
        if arg.name is not None:
            return f"{arg.name} = {self.render(arg.value)}"
        return self.render(arg.value)

    # -- types ----------------------------------------------------------
    def render_type(self, t: ast.TypeNode) -> str:
        if isinstance(t, ast.TypeName):
            return t.name
        if isinstance(t, ast.TypeApply):
            args = ", ".join(self.render_type(a) for a in t.args)
            return f"{self.render_type(t.base)}[{args}]"
        if isinstance(t, ast.TupleType):
            return "(" + ", ".join(self.render_type(i) for i in t.items) + ")"
        if isinstance(t, ast.NullableType):
            return f"{self._type_atom(t.inner)}?"
        if isinstance(t, ast.FunctionType):
            if len(t.params) == 1:
                return f"{self._type_atom(t.params[0])} -> {self.render_type(t.result)}"
            params = ", ".join(self.render_type(p) for p in t.params)
            return f"({params}) -> {self.render_type(t.result)}"
        raise FormatError(f"cannot format type {type(t).__name__}")

    def _type_atom(self, t: ast.TypeNode) -> str:
        if isinstance(t, ast.FunctionType):
            return f"({self.render_type(t)})"
        return self.render_type(t)

    # -- patterns -------------------------------------------------------
    def render_pattern(self, p: ast.Pattern) -> str:
        if isinstance(p, ast.WildcardPattern):
            return "_"
        if isinstance(p, ast.NullPattern):
            return "null"
        if isinstance(p, ast.NamePattern):
            return p.name
        if isinstance(p, ast.LiteralPattern):
            return _render_literal(p.value)
        if isinstance(p, ast.TuplePattern):
            return "(" + ", ".join(self.render_pattern(i) for i in p.items) + ")"
        if isinstance(p, ast.ConstructorPattern):
            if not p.args:
                return p.name
            return f"{p.name}({', '.join(self.render_pattern(a) for a in p.args)})"
        if isinstance(p, ast.OrPattern):
            return " | ".join(self.render_pattern(i) for i in p.patterns)
        if isinstance(p, ast.TypedPattern):
            return f"{self.render_pattern(p.pattern)}: {self.render_type(p.type)}"
        raise FormatError(f"cannot format pattern {type(p).__name__}")


def _render_literal(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, float):
        return repr(value)
    return str(value)


def _is_block(expr: ast.Expr) -> bool:
    """Whether an expression must be emitted as an indented block."""
    if isinstance(expr, (ast.BlockExpr, ast.MatchExpr, ast.WhileExpr, ast.ForExpr, ast.IOBlockExpr)):
        return True
    if isinstance(expr, ast.IfExpr):
        return _if_is_block(expr)
    if isinstance(expr, ast.LazyExpr):
        return _is_block(expr.body)
    return False


def _if_is_block(expr: ast.IfExpr) -> bool:
    if expr.elif_branches:
        return True
    branches = [expr.then_branch]
    if expr.else_branch is not None:
        branches.append(expr.else_branch)
    return any(_is_block(b) for b in branches)


def _line(node) -> int | None:
    span = getattr(node, "span", None)
    return span.start_line if span is not None else None


def _max_line(node) -> int:
    """The largest source line touched by a node's subtree (for blank-line gaps)."""
    best = 0

    def visit(n) -> None:
        nonlocal best
        if isinstance(n, ast.Node):
            span = getattr(n, "span", None)
            if span is not None:
                best = max(best, span.start_line, span.end_line)
            for f in dataclasses.fields(n):
                visit(getattr(n, f.name))
        elif isinstance(n, (list, tuple)):
            for item in n:
                visit(item)

    visit(node)
    return best
