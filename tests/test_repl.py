from __future__ import annotations

import io
import unittest

from lune.repl import ReplSession, repl_main
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

    def test_interactive_loop_smoke(self) -> None:
        stdin = io.StringIO("1 + 2\n:q\n")
        stdout = io.StringIO()
        stderr = io.StringIO()
        code = repl_main(stdin, stdout, stderr)
        self.assertEqual(code, 0)
        self.assertIn("3 : Int", stdout.getvalue())
        self.assertEqual(stderr.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
