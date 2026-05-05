from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lune.diagnostics import SourceMap, format_exception
from lune.evaluator import force_value
from lune.module_loader import ModuleLoadError, check_file, eval_file
from lune.typechecker import INT


class ModuleLoaderTests(unittest.TestCase):
    def test_check_and_eval_imported_module(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "math.lune").write_text(
                """
module math

def add(x: Int, y: Int): Int =
    x + y

let base = 40
""",
                encoding="utf-8",
            )
            main = root / "main.lune"
            main.write_text(
                """
module main
import math

let answer = add(base, 2)
""",
                encoding="utf-8",
            )

            type_env = check_file(main)
            self.assertEqual(type_env.lookup_value("answer"), INT)

            env = eval_file(main)
            self.assertEqual(force_value(env.lookup_raw("answer")), 42)

    def test_nested_module_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "util").mkdir()
            (root / "util" / "numbers.lune").write_text(
                """
module util.numbers

def inc(x: Int): Int =
    x + 1
""",
                encoding="utf-8",
            )
            main = root / "main.lune"
            main.write_text(
                """
module main
import util.numbers

let answer = inc(41)
""",
                encoding="utf-8",
            )

            env = eval_file(main)
            self.assertEqual(force_value(env.lookup_raw("answer")), 42)

    def test_module_path_option_adds_search_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lib = root / "lib"
            app = root / "app"
            lib.mkdir()
            app.mkdir()
            (lib / "math.lune").write_text(
                """
module math

def add(x: Int, y: Int): Int =
    x + y
""",
                encoding="utf-8",
            )
            main = app / "main.lune"
            main.write_text(
                """
module main
import math

let answer = add(20, 22)
""",
                encoding="utf-8",
            )

            env = eval_file(main, [lib])
            self.assertEqual(force_value(env.lookup_raw("answer")), 42)

    def test_external_import_is_not_file_resolved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            main = Path(tmp) / "main.lune"
            main.write_text(
                """
import java.time.LocalDate

def today(): IO[String] =
    IO:
        LocalDate.now().toString()
""",
                encoding="utf-8",
            )

            check_file(main)

    def test_missing_module_reports_diagnostic_with_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            main = Path(tmp) / "main.lune"
            main.write_text(
                """
module main
import missing.pkg

let answer = 42
""",
                encoding="utf-8",
            )
            source_map = SourceMap()

            with self.assertRaises(ModuleLoadError) as context:
                check_file(main, source_map=source_map)

            self.assertEqual(context.exception.diagnostic.code, "MOD0001")
            message = format_exception(context.exception, source_map)
            self.assertIn("module not found: missing.pkg", message)
            self.assertIn("import missing.pkg", message)
            self.assertIn("^", message)

    def test_cycle_reports_diagnostic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.lune").write_text(
                """
module a
import b

let aValue = 1
""",
                encoding="utf-8",
            )
            (root / "b.lune").write_text(
                """
module b
import a

let bValue = 2
""",
                encoding="utf-8",
            )

            with self.assertRaises(ModuleLoadError) as context:
                check_file(root / "a.lune")

            self.assertEqual(context.exception.diagnostic.code, "MOD0002")

    def test_module_name_mismatch_reports_diagnostic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "foo.lune").write_text(
                """
module bar

let value = 1
""",
                encoding="utf-8",
            )
            main = root / "main.lune"
            main.write_text(
                """
module main
import foo

let answer = value
""",
                encoding="utf-8",
            )

            with self.assertRaises(ModuleLoadError) as context:
                check_file(main)

            self.assertEqual(context.exception.diagnostic.code, "MOD0003")


if __name__ == "__main__":
    unittest.main()
