from __future__ import annotations

import io
import os
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

from lune.cli import main
from lune.diagnostics import SourceMap, format_diagnostic, format_exception
from lune.messages import set_language
from lune.repl import ReplSession, repl_main, wants_more
from lune.typechecker import LuneTypeError


class ReplTests(unittest.TestCase):
    def test_expression_result(self) -> None:
        session = ReplSession()
        result = session.submit("1 + 2")
        self.assertEqual(result.kind, "value")
        self.assertEqual(result.message, "3 : Int")

    def test_list_result_uses_lisp_style_display(self) -> None:
        session = ReplSession()
        result = session.submit("(1 2)")
        self.assertEqual(result.message, "(1 2) : List[Int]")

    def test_string_result_uses_lune_display(self) -> None:
        session = ReplSession()
        result = session.submit('"Ada"')
        self.assertEqual(result.message, '"Ada" : String')

    def test_session_keeps_let_binding(self) -> None:
        session = ReplSession()
        self.assertEqual(session.submit("let x = 40").message, "ok")
        self.assertEqual(session.submit("x + 2").message, "42 : Int")
        self.assertEqual(session.submit(":type x").message, "x : Int")

    def test_session_keeps_function_binding(self) -> None:
        session = ReplSession()
        source = """
def add(x: Int, y: Int): Int =
    x + y
"""
        self.assertEqual(session.submit(source).message, "ok")
        self.assertEqual(session.submit("add(20, 22)").message, "42 : Int")

    def test_session_keeps_type_binding_and_match(self) -> None:
        session = ReplSession()
        session.submit("""
type Option[T] =
    | Some(value: T)
    | None
""")
        session.submit("""
def getOrElse[T](option: Option[T], defaultValue: T): T =
    match option:
        | Some(value) -> value
        | None -> defaultValue
""")
        self.assertEqual(session.submit("getOrElse(Some(42), 0)").message, "42 : Int")

    def test_function_values_display_short_form(self) -> None:
        session = ReplSession()
        session.submit("""
def add(x: Int, y: Int): Int =
    x + y
""")
        self.assertEqual(session.submit("add").message, "<fn add> : Int -> Int -> Int")
        self.assertEqual(session.submit("add(1)").message, "<fn add> : Int -> Int")
        self.assertEqual(session.submit("fn x: Int -> x").message, "<fn> : Int -> Int")
        self.assertEqual(session.submit("println").message, "<fn println> : Any -> Unit")
        self.assertEqual(session.submit("Some").message, "<fn Some> : [T] T -> Option[T]")

    def test_type_error_does_not_bind_name(self) -> None:
        session = ReplSession()
        with self.assertRaises(LuneTypeError):
            session.submit("let bad: Int = true")
        env_message = session.submit(":env").message
        self.assertNotIn("bad :", env_message)
        self.assertIn("Some : [T] T -> Option[T]", env_message)
        self.assertIn("range : Int -> Int -> List[Int]", env_message)

    def test_commands(self) -> None:
        session = ReplSession()
        self.assertIn(":help", session.submit(":help").message)
        self.assertEqual(session.submit(":q").kind, "quit")

    def test_explain_command_supports_japanese(self) -> None:
        session = ReplSession()
        self.assertIn("未定義の名前", session.submit(":explain TYP0001 ja").message)
        self.assertIn("undefined name", session.submit(":explain TYP0001").message)
        self.assertEqual(session.submit(":explain TYP0001 de").kind, "error")

    def test_thunks_reports_states_without_forcing(self) -> None:
        session = ReplSession()
        session.submit("let x = 1 + 1")
        self.assertEqual(session.submit(":thunks").message, "x : unevaluated")
        # listing must not evaluate anything
        self.assertEqual(session.submit(":thunks").message, "x : unevaluated")
        session.submit("x")
        self.assertEqual(session.submit(":thunks").message, "x : evaluated = 2")

    def test_thunks_previews_infinite_stream_without_hanging(self) -> None:
        session = ReplSession()
        session.submit("let nat = naturalsFrom(1)")
        self.assertEqual(session.submit(":thunks nat").message, "nat : unevaluated")
        session.submit("head(nat)")
        self.assertEqual(session.submit(":thunks nat").message, "nat : evaluated = Cons(1, <thunk>)")

    def test_thunks_shows_memoized_failure(self) -> None:
        session = ReplSession()
        session.submit("let bad = 1 / 0")
        with self.assertRaises(Exception):
            session.submit("bad")
        message = session.submit(":thunks bad").message
        self.assertTrue(message.startswith("bad : failed = "), message)
        self.assertIn("division by zero", message)

    def test_thunks_failed_diagnostic_shows_its_code(self) -> None:
        from lune.evaluator import LuneRuntimeError, Thunk, ThunkState
        from lune.repl import _describe_binding

        thunk = Thunk(expr=None, env=None, state=ThunkState.FAILED, error=LuneRuntimeError("boom", code="RUN0005"))
        self.assertEqual(_describe_binding("z", thunk), "z : failed = error[RUN0005] boom")

    def test_thunks_name_lookup_and_edge_cases(self) -> None:
        session = ReplSession()
        self.assertIn("no thunks", session.submit(":thunks").message)
        session.submit("var v = 7")
        self.assertEqual(session.submit(":thunks v").message, "v : value = 7")
        self.assertIn("no thunks", session.submit(":thunks").message)
        self.assertEqual(session.submit(":thunks nosuch").kind, "error")
        self.assertEqual(session.submit(":thunks a b").message, "usage: :thunks [NAME]")

    def test_help_mentions_thunks(self) -> None:
        session = ReplSession()
        self.assertIn(":thunks", session.submit(":help").message)
        self.assertIn(":trace", session.submit(":help").message)

    def test_wants_more_detects_an_open_block(self) -> None:
        # the continuation rule is shared with the browser playground, which
        # drives ReplSession without going through repl_main
        for line in ("let f =", "if x > 0:", "let g = fn x ->", "let h =   "):
            with self.subTest(line=line):
                self.assertTrue(wants_more(line))
        for line in ("1 + 2", "let a = 1", ":help", ""):
            with self.subTest(line=line):
                self.assertFalse(wants_more(line))

    def test_trace_command_shows_forcing_and_memoization(self) -> None:
        session = ReplSession()
        self.assertEqual(session.submit(":trace").message, "trace is off")
        self.assertEqual(session.submit(":trace on").message, "trace on")
        # declarations are lazy: nothing is forced, so nothing is traced
        self.assertEqual(session.submit("let x = 1 + 1").message, "ok")
        message = session.submit("x + 1").message
        self.assertTrue(message.startswith("force x + 1"), message)
        self.assertIn("  force 1 + 1", message)
        self.assertTrue(message.endswith("3 : Int"), message)
        self.assertIn("memo 1 + 1 => 2", session.submit("x").message)
        self.assertEqual(session.submit(":trace off").message, "trace off")
        self.assertEqual(session.submit("x").message, "2 : Int")
        self.assertEqual(session.submit(":trace bogus").kind, "error")

    def test_interactive_loop_smoke(self) -> None:
        stdin = io.StringIO("1 + 2\n:q\n")
        stdout = io.StringIO()
        stderr = io.StringIO()
        code = repl_main(stdin, stdout, stderr)
        self.assertEqual(code, 0)
        self.assertIn("3 : Int", stdout.getvalue())
        self.assertEqual(stderr.getvalue(), "")


class ReplSpanTests(unittest.TestCase):
    """Expression input is parsed wrapped in `let __repl_value = `, but rendered unwrapped.

    Spans must be mapped back onto the line the user typed, or every caret sits
    len("let __repl_value = ") columns too far right.
    """

    def _render_diagnostic(self, inputs: list[str]) -> str:
        """Feed `inputs` to one session and render the first diagnostic they produce."""
        session = ReplSession()
        source_map = SourceMap()
        for index, source in enumerate(inputs, 1):
            filename = f"<repl:{index}>"
            source_map.add(filename, source)
            try:
                result = session.submit(source, filename)
            except Exception as exc:
                return format_exception(exc, source_map)
            if result.warnings:
                return format_diagnostic(result.warnings[0], source_map)
        self.fail(f"expected a diagnostic from {inputs[-1]!r}")

    def _caret_column(self, rendered: str) -> int:
        """1-based column of the first caret, relative to the quoted source line."""
        for line in rendered.splitlines():
            if line.lstrip().startswith("| ") and "^" in line:
                gutter = line.index("| ") + len("| ")
                return line.index("^") - gutter + 1
        self.fail(f"no caret line in:\n{rendered}")

    def test_expression_caret_points_at_the_offending_token(self) -> None:
        source = 'User("a")'
        rendered = self._render_diagnostic(["record User:\n    name: String", source])
        self.assertIn("error[REC0006]", rendered)
        column = source.index('"a"') + 1
        self.assertEqual(self._caret_column(rendered), column)
        self.assertIn(f"--> <repl:2>:1:{column}", rendered)

    def test_expression_caret_points_at_undefined_name(self) -> None:
        source = "1 + nosuch"
        rendered = self._render_diagnostic([source])
        self.assertIn("error[TYP0001]", rendered)
        column = source.index("nosuch") + 1
        self.assertEqual(self._caret_column(rendered), column)
        self.assertIn(f"--> <repl:1>:1:{column}", rendered)

    def test_unparsable_expression_caret_points_at_the_offending_token(self) -> None:
        # the wrapped re-parse fails too, so its span needs the same treatment
        source = "40 + $2"
        rendered = self._render_diagnostic([source])
        self.assertIn("error[LXL0001]", rendered)
        column = source.index("$") + 1
        self.assertEqual(self._caret_column(rendered), column)
        self.assertIn(f"--> <repl:1>:1:{column}", rendered)

    def test_multiline_expression_shifts_only_the_first_line(self) -> None:
        # the wrapper adds no newline, so lines after the first keep their columns
        source = "match Some(1):\n    | Some(v) -> nosuch\n    | None -> 0"
        rendered = self._render_diagnostic([source])
        self.assertIn("error[TYP0001]", rendered)
        column = source.splitlines()[1].index("nosuch") + 1
        self.assertEqual(self._caret_column(rendered), column)
        self.assertIn(f"--> <repl:1>:2:{column}", rendered)

    def test_declaration_input_spans_are_untouched(self) -> None:
        source = "let bad: Int = true"
        rendered = self._render_diagnostic([source])
        column = source.index("true") + 1
        self.assertEqual(self._caret_column(rendered), column)


class CliReplFallbackTests(unittest.TestCase):
    """`lune` starts the REPL when no file/subcommand remains after global flags."""

    def tearDown(self) -> None:
        set_language("en")

    def _run_main(self, argv: list[str], input_text: str, lune_lang: str | None = None) -> tuple[int, str, str]:
        stdin = io.StringIO(input_text)
        stdout = io.StringIO()
        stderr = io.StringIO()
        with mock.patch.dict(os.environ):
            os.environ.pop("LUNE_LANG", None)
            if lune_lang is not None:
                os.environ["LUNE_LANG"] = lune_lang
            with mock.patch.object(sys, "stdin", stdin), redirect_stdout(stdout), redirect_stderr(stderr):
                code = main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_no_args_starts_repl(self) -> None:
        code, out, err = self._run_main([], "1 + 2\n:q\n")
        self.assertEqual(code, 0)
        self.assertIn("Lune v0.1 REPL", out)
        self.assertIn("3 : Int", out)
        self.assertEqual(err, "")

    def test_lang_only_starts_repl_in_japanese(self) -> None:
        code, out, err = self._run_main(["--lang", "ja"], "1 + 2\n:lang\n:q\n")
        self.assertEqual(code, 0)
        self.assertIn("3 : Int", out)
        self.assertIn("language is ja", out)
        self.assertEqual(err, "")

    def test_lune_lang_env_sets_repl_language(self) -> None:
        code, out, err = self._run_main([], ":lang\nnosuch\n:q\n", lune_lang="ja")
        self.assertEqual(code, 0)
        self.assertIn("language is ja", out)
        self.assertIn("未定義の名前: nosuch", err)


if __name__ == "__main__":
    unittest.main()
