from __future__ import annotations

import io
import re
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from lune.cli import main
from lune.messages import LANGUAGES, MESSAGES, get_language, set_language, t
from lune.repl import ReplSession
from lune.typechecker import LuneTypeError, name_suggestion

KEY_RE = re.compile(r"""\bt\(\s*['"]([a-z0-9.\-]+)['"]""")
LUNE_DIR = Path(__file__).resolve().parent.parent / "lune"


class MessageCatalogTests(unittest.TestCase):
    def tearDown(self) -> None:
        set_language("en")

    def test_every_used_key_is_in_the_catalog(self) -> None:
        """A `t("...")` call with an unknown key must not ship."""
        used: set[str] = set()
        for path in LUNE_DIR.glob("*.py"):
            if path.name == "messages.py":
                continue
            used.update(KEY_RE.findall(path.read_text(encoding="utf-8")))
        self.assertTrue(used)
        missing = sorted(used - set(MESSAGES))
        self.assertEqual(missing, [], f"keys used but not in catalog: {missing}")
        unused = sorted(set(MESSAGES) - used)
        self.assertEqual(unused, [], f"catalog keys never used: {unused}")

    def test_every_key_is_translated(self) -> None:
        for key, (en, ja) in MESSAGES.items():
            self.assertTrue(en, key)
            self.assertTrue(ja, key)
            self.assertTrue(any(ord(ch) > 0x3000 for ch in ja), f"{key}: Japanese text looks untranslated")
            # both templates must accept the same parameters
            self.assertEqual(sorted(re.findall(r"{(\w+)}", en)), sorted(re.findall(r"{(\w+)}", ja)), key)

    def test_set_language_falls_back_to_english(self) -> None:
        set_language("de")
        self.assertEqual(get_language(), "en")
        set_language("ja")
        self.assertEqual(get_language(), "ja")

    def test_japanese_type_error(self) -> None:
        set_language("ja")
        session = ReplSession()
        with self.assertRaises(LuneTypeError) as ctx:
            session.submit("let x: Int = true")
        self.assertIn("が必要ですが", ctx.exception.diagnostic.message)

    def test_japanese_caret_labels(self) -> None:
        """The label under the source caret must follow the active language."""
        set_language("ja")
        cases = [
            ('let x: Int = "hello"', "この式の型は String"),
            ('def f(n: Int): Int = "no"', "関数本体の型は String"),
            ('let xs: List[Int] = [1, "two"]', "この要素の型は String"),
            ("let f: Int -> Int = fn x -> true", "ラムダ本体の型は Bool"),
            ("let g: Int -> Int = fn x: Bool -> 1", "注釈 Bool は期待される型 Int を受け付けない"),
        ]
        for source, expected_label in cases:
            with self.subTest(source=source):
                session = ReplSession()
                with self.assertRaises(LuneTypeError) as ctx:
                    session.submit(source)
                primary = ctx.exception.diagnostic.primary
                assert primary is not None
                self.assertEqual(primary.message, expected_label)

    def test_japanese_did_you_mean(self) -> None:
        set_language("ja")
        hints, fixes = name_suggestion("cont", ["count"], None)
        self.assertEqual(hints, ["もしかして `count` ですか?"])

    def test_recursive_function_detection_survives_language_switch(self) -> None:
        """TYP0011 relies on comparing a message; it must work in Japanese too."""
        set_language("ja")
        session = ReplSession()
        with self.assertRaises(LuneTypeError) as ctx:
            session.submit("def fact(n: Int) =\n    if n <= 1 then 1 else n * fact(n - 1)\n")
        self.assertEqual(ctx.exception.diagnostic.code, "TYP0011")
        self.assertIn("再帰関数", ctx.exception.diagnostic.message)

    def test_cli_lang_flag_localizes_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.lune"
            path.write_text("let x: Int = true\n", encoding="utf-8")
            err = io.StringIO()
            with redirect_stderr(err):
                code = main([str(path), "--check", "--lang", "ja"])
        self.assertEqual(code, 1)
        self.assertIn("が必要ですが", err.getvalue())
        self.assertIn("--lang ja", err.getvalue())  # localized explain footer
        self.assertIn("^^^^ この式の型は Bool", err.getvalue())  # localized caret label
        self.assertNotIn("this expression has type", err.getvalue())

    def test_repl_lang_command(self) -> None:
        session = ReplSession()
        self.assertEqual(session.submit(":lang").message, "language is en")
        self.assertEqual(session.submit(":lang ja").message, "language: ja")
        with self.assertRaises(LuneTypeError) as ctx:
            session.submit("nosuch")
        self.assertIn("未定義の名前", ctx.exception.diagnostic.message)
        # :explain follows the session language
        self.assertIn("直し方:", session.submit(":explain TYP0001").message)
        self.assertEqual(session.submit(":lang fr").kind, "error")
        session.submit(":lang en")


if __name__ == "__main__":
    unittest.main()
