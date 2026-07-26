from __future__ import annotations

import ast as python_ast
import io
import os
import re
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

from lune.cli import main
from lune.messages import LANGUAGES, MESSAGES, get_language, set_language, t
from lune.repl import ReplSession
from lune.typechecker import LuneTypeError, name_suggestion, required_type

KEY_RE = re.compile(r"""\bt\(\s*['"]([a-z0-9.\-]+)['"]""")
LUNE_DIR = Path(__file__).resolve().parent.parent / "lune"

# Text-carrying argument slots of the diagnostic constructors:
# name -> (positional indices, keyword names). Slots not listed (codes,
# severities, spans, replacement text) may legitimately be literals.
DIAGNOSTIC_TEXT_ARGS: dict[str, tuple[tuple[int, ...], tuple[str, ...]]] = {
    "Diagnostic": ((2,), ("message", "notes", "hints")),
    "Label": ((1,), ("message",)),
    "Fix": ((2,), ("description",)),
    "LuneTypeError": ((0, 3, 4), ("message", "label", "hints")),
    "LuneRuntimeError": ((0,), ("message", "hints")),
    "LuneSyntaxError": ((0, 3, 4), ("message", "label", "hints")),
    "ModuleLoadError": ((0, 3, 4), ("message", "label", "hints")),
}


def _is_literal_text(node: python_ast.expr) -> bool:
    if isinstance(node, python_ast.Constant) and isinstance(node.value, str):
        return True
    if isinstance(node, python_ast.JoinedStr):
        return True
    if isinstance(node, (python_ast.List, python_ast.Tuple)):
        return any(_is_literal_text(element) for element in node.elts)
    return False


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

    def test_diagnostic_text_goes_through_catalog(self) -> None:
        """Diagnostic text must be built with `t(...)`, never a string literal.

        The key scan above only sees `t("...")` calls, so a literal passed
        straight to a diagnostic constructor ships untranslated without any
        test noticing (TYP0010's hint did exactly that).
        """
        violations: list[str] = []
        for path in LUNE_DIR.glob("*.py"):
            tree = python_ast.parse(path.read_text(encoding="utf-8"))
            for node in python_ast.walk(tree):
                if not isinstance(node, python_ast.Call):
                    continue
                func = node.func
                name = func.id if isinstance(func, python_ast.Name) else getattr(func, "attr", None)
                if name not in DIAGNOSTIC_TEXT_ARGS:
                    continue
                positions, keywords = DIAGNOSTIC_TEXT_ARGS[name]
                for index in positions:
                    if index < len(node.args) and _is_literal_text(node.args[index]):
                        violations.append(f"{path.name}:{node.args[index].lineno}: {name} positional arg {index}")
                for keyword in node.keywords:
                    if keyword.arg in keywords and _is_literal_text(keyword.value):
                        violations.append(f"{path.name}:{keyword.value.lineno}: {name} {keyword.arg}=")
        self.assertEqual(violations, [], f"diagnostic text bypasses the message catalog: {violations}")

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

    def test_japanese_context_in_type_errors(self) -> None:
        """The context prefix of type-error messages must follow the active language."""
        set_language("ja")
        cases = [
            ('let x: Int = "hello"', "let の型注釈: Int が必要ですが、String が見つかりました"),
            ("var x: Int = true", "var の型注釈: Int が必要ですが、Bool が見つかりました"),
            ('let xs: List[Int] = [1, "two"]', "リストの要素: Int が必要ですが、String が見つかりました"),
            ("let n = -true", "単項 -: 数値型が必要ですが、Bool が見つかりました"),
            ("let n = +true", "単項 +: 数値型が必要ですが、Bool が見つかりました"),
            ("let b = !1", "単項 !: Bool が必要ですが、Int が見つかりました"),
            ("let y = if 1 then 2 else 3", "if の条件: Bool が必要ですが、Int が見つかりました"),
            (
                'def f(n: Int): Int =\n    if n > 0:\n        1\n    elif "s":\n        2\n    else:\n        3\n',
                "elif の条件: Bool が必要ですが、String が見つかりました",
            ),
            (
                "def f(): Unit =\n    while 1:\n        ()\n",
                "while の条件: Bool が必要ですが、Int が見つかりました",
            ),
            (
                'def f(n: Int): Int =\n    match n:\n        | x if "s" -> 1\n        | _ -> 2\n',
                "match のガード: Bool が必要ですが、String が見つかりました",
            ),
            (
                'def g(): Unit =\n    var i = 0\n    i = "s"\n',
                "代入: Int が必要ですが、String が見つかりました",
            ),
            ("let f: Int -> Int = fn x -> true", "ラムダ本体: Int が必要ですが、Bool が見つかりました"),
            (
                'def f(n: Int): Int =\n    match n:\n        | "s" -> 1\n        | _ -> 2\n',
                "リテラルパターン: Int が必要ですが、String が見つかりました",
            ),
            (
                "def f(n: Int): Int =\n    match n:\n        | (x: String) -> 1\n        | _ -> 2\n",
                "型付きパターン: String が必要ですが、Int が見つかりました",
            ),
            ('def f(n: Int): Int = "no"', "f の戻り値型: Int が必要ですが、String が見つかりました"),
            (
                'def pick[T](x: T, y: T): T = x\nlet z = pick(1, "two")\n',
                "型パラメータ T: Int が必要ですが、String が見つかりました",
            ),
        ]
        for source, expected_message in cases:
            with self.subTest(source=source):
                session = ReplSession()
                with self.assertRaises(LuneTypeError) as ctx:
                    session.submit(source)
                self.assertEqual(ctx.exception.diagnostic.message, expected_message)

    def test_japanese_annotation_required_label(self) -> None:
        """typ.annotation-required's {label} slot is fed from the ctx catalog."""
        set_language("ja")
        with self.assertRaises(LuneTypeError) as ctx:
            required_type(None, t("ctx.parameter", name="x"))
        self.assertEqual(ctx.exception.diagnostic.message, "v0.1 では 引数 x に型注釈が必要です")

    def test_typ0010_hint_follows_language(self) -> None:
        """The TYP0010 hint used to be a hardcoded English f-string."""
        for lang, expected_hint in [
            ("en", "add a type annotation, e.g. `fn x: Int -> ...`"),
            ("ja", "型注釈を追加してください。例: `fn x: Int -> ...`"),
        ]:
            with self.subTest(lang=lang):
                set_language(lang)
                session = ReplSession()
                result = session.submit("let f = fn x -> x * 2")
                warning = next(w for w in result.warnings if w.code == "TYP0010")
                self.assertEqual(warning.hints, [expected_hint])

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
        self.assertIn("let の型注釈: Int が必要ですが", err.getvalue())  # localized context
        self.assertNotIn("let annotation", err.getvalue())
        self.assertIn("--lang ja", err.getvalue())  # localized explain footer
        self.assertIn("^^^^ この式の型は Bool", err.getvalue())  # localized caret label
        self.assertNotIn("this expression has type", err.getvalue())

    def _check_bad_file(self, extra_argv: list[str], lune_lang: str | None) -> tuple[int, str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.lune"
            path.write_text("let x: Int = true\n", encoding="utf-8")
            err = io.StringIO()
            with mock.patch.dict(os.environ):
                os.environ.pop("LUNE_LANG", None)
                if lune_lang is not None:
                    os.environ["LUNE_LANG"] = lune_lang
                with redirect_stderr(err):
                    code = main([str(path), "--check", *extra_argv])
        return code, err.getvalue()

    def test_lune_lang_env_sets_default_language(self) -> None:
        code, output = self._check_bad_file([], lune_lang="ja")
        self.assertEqual(code, 1)
        self.assertIn("let の型注釈: Int が必要ですが", output)
        self.assertNotIn("let annotation", output)

    def test_lang_flag_overrides_lune_lang_env(self) -> None:
        code, output = self._check_bad_file(["--lang", "en"], lune_lang="ja")
        self.assertEqual(code, 1)
        self.assertIn("let annotation: expected Int, got Bool", output)
        self.assertNotIn("が必要ですが", output)

    def test_invalid_lune_lang_falls_back_to_english(self) -> None:
        code, output = self._check_bad_file([], lune_lang="fr")
        self.assertEqual(code, 1)  # not the exit code 2 of an invalid --lang
        self.assertIn("let annotation: expected Int, got Bool", output)

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
