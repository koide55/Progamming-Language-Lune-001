from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

from lune.cli import main
from lune.diagnostics import SourceMap, SourceSpan, format_exception
from lune.lexer import lex
from lune.repl import repl_main
from lune.typechecker import LuneTypeError


class DiagnosticTests(unittest.TestCase):
    def test_syntax_error_formats_with_source_excerpt(self) -> None:
        source = "let x = $1\n"
        source_map = SourceMap()
        source_map.add("sample.lune", source)
        with self.assertRaises(Exception) as raised:
            lex(source, "sample.lune")
        rendered = format_exception(raised.exception, source_map)
        self.assertIn("error[LXL0001]: unexpected character '$'", rendered)
        self.assertIn("--> sample.lune:1:9", rendered)
        self.assertIn("1 | let x = $1", rendered)
        self.assertIn("^ unexpected character", rendered)

    def test_type_error_formats_as_diagnostic(self) -> None:
        rendered = format_exception(LuneTypeError("let annotation: expected Int, got Bool"))
        self.assertEqual(rendered, "error[TYP0003]: let annotation: expected Int, got Bool")

    def test_cli_returns_error_status_and_diagnostic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.lune"
            path.write_text("let x = $1\n", encoding="utf-8")
            stderr = io.StringIO()
            old_stderr = __import__("sys").stderr
            try:
                __import__("sys").stderr = stderr
                code = main([str(path), "--check"])
            finally:
                __import__("sys").stderr = old_stderr
        self.assertEqual(code, 1)
        self.assertIn("error[LXL0001]", stderr.getvalue())
        self.assertIn("let x = $1", stderr.getvalue())

    def test_cli_type_error_uses_ast_span(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad_type.lune"
            path.write_text("let answer: Int = true\n", encoding="utf-8")
            stderr = io.StringIO()
            old_stderr = __import__("sys").stderr
            try:
                __import__("sys").stderr = stderr
                code = main([str(path), "--check"])
            finally:
                __import__("sys").stderr = old_stderr
        self.assertEqual(code, 1)
        rendered = stderr.getvalue()
        self.assertIn("error[TYP0003]: let annotation: expected Int, got Bool", rendered)
        self.assertIn("1 | let answer: Int = true", rendered)
        self.assertIn("^", rendered)
        self.assertIn("this expression has type Bool", rendered)

    def test_span_under_cwd_formats_relative(self) -> None:
        absolute = str(Path.cwd() / "examples" / "bad.lune")
        span = SourceSpan.point(absolute, 2, 5)
        self.assertEqual(span.format(), f"{Path('examples') / 'bad.lune'}:2:5")

    def test_span_outside_cwd_stays_absolute(self) -> None:
        span = SourceSpan.point(f"{os.sep}nonexistent-root{os.sep}bad.lune", 1, 1)
        self.assertEqual(span.format(), f"{os.sep}nonexistent-root{os.sep}bad.lune:1:1")

    def test_span_virtual_filename_passes_through(self) -> None:
        span = SourceSpan.point("<repl:3>", 1, 19)
        self.assertEqual(span.format(), "<repl:3>:1:19")

    def test_cli_check_renders_relative_path_for_file_under_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.lune"
            path.write_text("let x = $1\n", encoding="utf-8")
            stderr = io.StringIO()
            old_stderr = sys.stderr
            old_cwd = os.getcwd()
            try:
                os.chdir(tmp)
                sys.stderr = stderr
                code = main(["bad.lune", "--check"])
            finally:
                sys.stderr = old_stderr
                os.chdir(old_cwd)
        self.assertEqual(code, 1)
        self.assertIn("--> bad.lune:1:9", stderr.getvalue())

    def test_repl_formats_error_and_continues(self) -> None:
        stdin = io.StringIO("let x = $1\n1 + 2\n:q\n")
        stdout = io.StringIO()
        stderr = io.StringIO()
        code = repl_main(stdin, stdout, stderr)
        self.assertEqual(code, 0)
        self.assertIn("3 : Int", stdout.getvalue())
        self.assertIn("error[LXL0001]", stderr.getvalue())
        self.assertIn("<repl:1>", stderr.getvalue())
        self.assertIn("  |         ^ unexpected character", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
