from __future__ import annotations

import pathlib
import unittest

from lune import nodes as ast
from lune.lexer import lex
from lune.layout import apply_layout
from lune.parser import parse_source
from lune.tokens import TokenKind


ROOT = pathlib.Path(__file__).resolve().parents[1]


class ParserTests(unittest.TestCase):
    def test_layout_emits_indent_and_dedent(self) -> None:
        source = """def f(): Int =
    1
"""
        kinds = [token.kind for token in apply_layout(lex(source))]
        self.assertIn(TokenKind.INDENT, kinds)
        self.assertIn(TokenKind.DEDENT, kinds)

    def test_parse_basics_sample(self) -> None:
        tree = parse_source((ROOT / "samples" / "basics.lune").read_text(encoding="utf-8"))
        self.assertEqual(tree.module_name, "sample.basics")
        self.assertEqual(len(tree.imports), 1)
        self.assertEqual(tree.imports[0].path, "java.time.LocalDate")
        self.assertGreaterEqual(len(tree.declarations), 4)
        self.assertIsInstance(tree.declarations[0], ast.FunctionDecl)

    def test_parse_option_sample(self) -> None:
        tree = parse_source((ROOT / "samples" / "option.lune").read_text(encoding="utf-8"))
        type_decl = tree.declarations[0]
        self.assertIsInstance(type_decl, ast.TypeDecl)
        self.assertEqual(type_decl.name, "Option")
        self.assertEqual([ctor.name for ctor in type_decl.constructors], ["Some", "None"])
        fn = tree.declarations[1]
        self.assertIsInstance(fn, ast.FunctionDecl)
        self.assertIsInstance(fn.body, ast.BlockExpr)
        self.assertIsInstance(fn.body.result, ast.MatchExpr)

    def test_parse_record_decl(self) -> None:
        tree = parse_source(
            """
record User:
    name: String
    !age: Int
"""
        )
        decl = tree.declarations[0]
        self.assertIsInstance(decl, ast.RecordDecl)
        self.assertEqual(decl.name, "User")
        self.assertEqual([field.name for field in decl.fields], ["name", "age"])
        self.assertFalse(decl.fields[0].is_strict)
        self.assertTrue(decl.fields[1].is_strict)

    def test_parse_while_expr(self) -> None:
        tree = parse_source(
            """
let answer =
    var i = 0
    while i < 3:
        i = i + 1
    i
"""
        )
        decl = tree.declarations[0]
        self.assertIsInstance(decl, ast.LetDecl)
        self.assertIsInstance(decl.value, ast.BlockExpr)
        self.assertIsInstance(decl.value.statements[1], ast.WhileExpr)

    def test_parse_for_expr(self) -> None:
        tree = parse_source(
            """
let answer =
    var total = 0
    for x in range(1, 4):
        total = total + x
    total
"""
        )
        decl = tree.declarations[0]
        self.assertIsInstance(decl, ast.LetDecl)
        self.assertIsInstance(decl.value, ast.BlockExpr)
        self.assertIsInstance(decl.value.statements[1], ast.ForExpr)
        for_expr = decl.value.statements[1]
        self.assertIsInstance(for_expr.pattern, ast.NamePattern)
        self.assertEqual(for_expr.pattern.name, "x")

    def test_parse_list_literal(self) -> None:
        tree = parse_source("let numbers = [1, 2, 3]\n")
        decl = tree.declarations[0]
        self.assertIsInstance(decl, ast.LetDecl)
        self.assertIsInstance(decl.value, ast.ListExpr)
        self.assertEqual(len(decl.value.items), 3)

    def test_parse_lisp_style_list_literal(self) -> None:
        tree = parse_source("let numbers = (1 2 3)\n")
        decl = tree.declarations[0]
        self.assertIsInstance(decl, ast.LetDecl)
        self.assertIsInstance(decl.value, ast.ListExpr)
        self.assertEqual(len(decl.value.items), 3)

    def test_operator_precedence(self) -> None:
        tree = parse_source("let x = 1 + 2 * 3\n")
        decl = tree.declarations[0]
        self.assertIsInstance(decl, ast.LetDecl)
        self.assertIsNotNone(decl.span)
        self.assertEqual((decl.span.start_line, decl.span.start_column), (1, 1))
        self.assertIsInstance(decl.value, ast.BinaryExpr)
        self.assertIsNotNone(decl.value.span)
        self.assertEqual((decl.value.span.start_line, decl.value.span.start_column), (1, 9))
        self.assertEqual(decl.value.op, "+")
        self.assertIsInstance(decl.value.right, ast.BinaryExpr)
        self.assertEqual(decl.value.right.op, "*")

    def test_floor_division_binds_like_multiplication(self) -> None:
        tree = parse_source("let x = 1 + 7 // 2\n")
        value = tree.declarations[0].value
        self.assertEqual(value.op, "+")
        self.assertIsInstance(value.right, ast.BinaryExpr)
        self.assertEqual(value.right.op, "//")

    def test_floor_division_is_left_associative(self) -> None:
        tree = parse_source("let x = 8 // 2 // 2\n")
        value = tree.declarations[0].value
        self.assertEqual(value.op, "//")
        self.assertIsInstance(value.left, ast.BinaryExpr)
        self.assertEqual(value.left.op, "//")

    def test_floor_division_lexes_as_one_token(self) -> None:
        # `//` must not come out as two `/` tokens, and it is not a comment marker.
        tree = parse_source("let x = 7 // 2\n")
        value = tree.declarations[0].value
        self.assertEqual(value.op, "//")
        self.assertEqual(value.left.value, 7)
        self.assertEqual(value.right.value, 2)

    def test_function_and_match_nodes_have_spans(self) -> None:
        tree = parse_source((ROOT / "samples" / "option.lune").read_text(encoding="utf-8"))
        fn = tree.declarations[1]
        self.assertIsInstance(fn, ast.FunctionDecl)
        self.assertIsNotNone(fn.span)
        self.assertEqual(fn.span.start_line, 7)
        self.assertIsInstance(fn.body, ast.BlockExpr)
        self.assertIsInstance(fn.body.result, ast.MatchExpr)
        self.assertIsNotNone(fn.body.result.span)
        self.assertEqual(fn.body.result.span.start_line, 8)


if __name__ == "__main__":
    unittest.main()
