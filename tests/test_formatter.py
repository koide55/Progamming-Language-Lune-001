from __future__ import annotations

import glob
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from lune.cli import fmt_command
from lune.formatter import FormatError, format_source, is_formatted

SAMPLES = sorted(glob.glob(str(Path(__file__).resolve().parent.parent / "samples" / "**" / "*.lune"), recursive=True))


def fmt(source: str) -> str:
    return format_source(source, "<test>")


class FormatterTests(unittest.TestCase):
    def test_samples_are_idempotent_and_meaning_preserving(self) -> None:
        # format_source runs the re-parse meaning-check internally and raises on
        # any change; idempotency is checked explicitly.
        self.assertTrue(SAMPLES, "expected sample files to exist")
        for path in SAMPLES:
            source = Path(path).read_text(encoding="utf-8")
            once = format_source(source, path)
            twice = format_source(once, path)
            self.assertEqual(once, twice, f"not idempotent: {path}")

    def test_normalizes_spacing(self) -> None:
        self.assertEqual(fmt("let    x=1+2\n"), "let x = 1 + 2\n")

    def test_preserves_needed_parentheses(self) -> None:
        self.assertEqual(fmt("let y = (1 + 2) * 3\n"), "let y = (1 + 2) * 3\n")

    def test_drops_redundant_parentheses(self) -> None:
        self.assertEqual(fmt("let y = 1 + (2 * 3)\n"), "let y = 1 + 2 * 3\n")

    def test_keeps_precedence_flat(self) -> None:
        self.assertEqual(fmt("let y = 1 + 2 * 3\n"), "let y = 1 + 2 * 3\n")

    def test_formats_floor_division(self) -> None:
        self.assertEqual(fmt("let y = 7//2\n"), "let y = 7 // 2\n")

    def test_keeps_parentheses_that_regroup_floor_division(self) -> None:
        self.assertEqual(fmt("let y = 8 // (4 // 2)\n"), "let y = 8 // (4 // 2)\n")

    def test_formats_compound_floor_division_assignment(self) -> None:
        self.assertEqual(
            fmt("let y =\n    var x = 7\n    x//=2\n    x\n"),
            "let y =\n    var x = 7\n    x //= 2\n    x\n",
        )

    def test_inline_def_body_becomes_canonical_block(self) -> None:
        self.assertEqual(fmt("def f(a: Int): Int = a\n"), "def f(a: Int): Int =\n    a\n")

    def test_let_in_becomes_block(self) -> None:
        self.assertEqual(
            fmt("let a = let x = 40 in x + 2\n"),
            "let a =\n    let x = 40\n    x + 2\n",
        )

    def test_nested_let_in_becomes_flat_block(self) -> None:
        self.assertEqual(
            fmt("let a = let x = 1.0 in let y = 2.0 in x + y\n"),
            "let a =\n    let x = 1.0\n    let y = 2.0\n    x + y\n",
        )

    def test_nested_let_in_with_shadowing(self) -> None:
        # Flattening keeps shadowing semantics: both forms evaluate `x` to 2.
        self.assertEqual(
            fmt("let a = let x = 1 in let x = 2 in x\n"),
            "let a =\n    let x = 1\n    let x = 2\n    x\n",
        )

    def test_preserves_leading_and_trailing_comments(self) -> None:
        out = fmt("# leading\nlet x = 1  # trailing\n")
        self.assertIn("# leading", out)
        self.assertIn("# trailing", out)

    def test_preserves_blank_line_grouping(self) -> None:
        source = "let a = 1\nlet b = 2\n\nlet c = 3\n"
        self.assertEqual(fmt(source), source)

    def test_narrow_list_stays_inline(self) -> None:
        self.assertEqual(fmt("let xs = [1, 2, 3]\n"), "let xs = [1, 2, 3]\n")

    def test_wide_list_wraps_one_item_per_line(self) -> None:
        items = ", ".join(str(i) for i in range(60))
        out = fmt(f"let xs = [{items}]\n")
        self.assertIn("let xs = [\n", out)
        self.assertTrue(out.rstrip().endswith("]"))
        self.assertEqual(fmt(out), out)  # idempotent

    def test_refuses_block_comments(self) -> None:
        with self.assertRaises(FormatError):
            fmt("### block ###\nlet x = 1\n")

    def test_is_formatted(self) -> None:
        self.assertTrue(is_formatted("let x = 1\n"))
        self.assertFalse(is_formatted("let   x=1\n"))

    def test_output_ends_with_single_newline(self) -> None:
        self.assertTrue(fmt("let x = 1").endswith("\n"))
        self.assertFalse(fmt("let x = 1\n\n\n").endswith("\n\n"))

    # --- CLI ---

    def test_cli_check_reports_unformatted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.lune"
            path.write_text("let   x=1\n", encoding="utf-8")
            err = io.StringIO()
            with redirect_stderr(err):
                code = fmt_command(["--check", str(path)])
        self.assertEqual(code, 1)
        self.assertIn("would reformat", err.getvalue())

    def test_cli_check_passes_when_formatted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.lune"
            path.write_text("let x = 1\n", encoding="utf-8")
            with redirect_stderr(io.StringIO()):
                code = fmt_command(["--check", str(path)])
        self.assertEqual(code, 0)

    def test_cli_write_rewrites_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.lune"
            path.write_text("let   x=1\n", encoding="utf-8")
            with redirect_stderr(io.StringIO()):
                code = fmt_command(["--write", str(path)])
            self.assertEqual(code, 0)
            self.assertEqual(path.read_text(encoding="utf-8"), "let x = 1\n")

    def test_cli_stdout_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.lune"
            path.write_text("let   x=1\n", encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out):
                code = fmt_command([str(path)])
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue(), "let x = 1\n")


if __name__ == "__main__":
    unittest.main()
