from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from lune.cli import fix_command
from lune.fixer import FixError, apply_fixes
from lune.typechecker import LuneTypeError, check_source


class FixerTests(unittest.TestCase):
    def test_typ0001_diagnostic_carries_a_fix(self) -> None:
        with self.assertRaises(LuneTypeError) as ctx:
            check_source("let total = 1\nlet x = totl\n")
        fixes = ctx.exception.diagnostic.fixes
        self.assertEqual(len(fixes), 1)
        self.assertEqual(fixes[0].replacement, "total")

    def test_fixes_local_typo(self) -> None:
        fixed, applied = apply_fixes("let total = 10\nlet x = totl\n")
        self.assertEqual(applied, 1)
        self.assertEqual(fixed, "let total = 10\nlet x = total\n")

    def test_fixes_prelude_typo(self) -> None:
        fixed, applied = apply_fixes("let xs = rang(1, 5)\n")
        self.assertEqual(applied, 1)
        self.assertIn("range(1, 5)", fixed)

    def test_fixes_multiple_typos_iteratively(self) -> None:
        fixed, applied = apply_fixes("let total = 10\nlet a = totl + 1\nlet b = totl * 2\n")
        self.assertEqual(applied, 2)
        self.assertNotIn("totl", fixed)

    def test_no_fix_without_close_match(self) -> None:
        source = "let x = zzzzz + 1\n"
        fixed, applied = apply_fixes(source)
        self.assertEqual(applied, 0)
        self.assertEqual(fixed, source)

    def test_clean_source_unchanged(self) -> None:
        source = "let x = 1\n"
        self.assertEqual(apply_fixes(source), (source, 0))

    def test_refuses_files_with_imports(self) -> None:
        with self.assertRaises(FixError):
            apply_fixes("module main\nimport math\nlet a = totl\n")

    # --- CLI ---

    def test_cli_check_reports_and_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.lune"
            path.write_text("let total = 1\nlet x = totl\n", encoding="utf-8")
            err = io.StringIO()
            with redirect_stderr(err):
                code = fix_command(["--check", str(path)])
        self.assertEqual(code, 1)
        self.assertIn("auto-fixable", err.getvalue())

    def test_cli_write_applies_fixes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.lune"
            path.write_text("let total = 1\nlet x = totl\n", encoding="utf-8")
            with redirect_stderr(io.StringIO()):
                code = fix_command(["--write", str(path)])
            self.assertEqual(code, 0)
            self.assertEqual(path.read_text(encoding="utf-8"), "let total = 1\nlet x = total\n")

    def test_cli_stdout_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.lune"
            path.write_text("let total = 1\nlet x = totl\n", encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out):
                code = fix_command([str(path)])
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue(), "let total = 1\nlet x = total\n")


if __name__ == "__main__":
    unittest.main()
