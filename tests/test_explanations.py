from __future__ import annotations

import io
import re
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from lune.cli import explain_command, main
from lune.diagnostics import Diagnostic, format_diagnostic
from lune.explanations import (
    EXPLANATIONS,
    available_codes,
    has_explanation,
    render_error_index,
    render_explanation,
)

CODE_RE = re.compile(r"\b([A-Z]{2,4}[0-9]{4})\b")
LUNE_DIR = Path(__file__).resolve().parent.parent / "lune"


class ExplanationTests(unittest.TestCase):
    def test_every_emitted_code_has_an_explanation(self) -> None:
        """Every diagnostic code the compiler can emit must be explained."""
        emitted: set[str] = set()
        for path in LUNE_DIR.glob("*.py"):
            if path.name == "explanations.py":
                continue
            for match in CODE_RE.finditer(path.read_text(encoding="utf-8")):
                emitted.add(match.group(1))
        missing = sorted(emitted - set(EXPLANATIONS))
        self.assertEqual(missing, [], f"diagnostic codes without an explanation: {missing}")

    def test_render_explanation_contains_sections(self) -> None:
        text = render_explanation("TYP0007")
        assert text is not None
        self.assertIn("error[TYP0007]", text)
        self.assertIn("How to fix:", text)

    def test_render_explanation_is_case_insensitive(self) -> None:
        self.assertIsNotNone(render_explanation("typ0007"))

    def test_render_explanation_unknown_returns_none(self) -> None:
        self.assertIsNone(render_explanation("ZZZ9999"))

    def test_has_explanation(self) -> None:
        self.assertTrue(has_explanation("TYP0001"))
        self.assertFalse(has_explanation("NOPE0000"))

    def test_available_codes_are_sorted_and_nonempty(self) -> None:
        codes = available_codes()
        self.assertTrue(codes)
        self.assertEqual(codes, sorted(codes))

    def test_japanese_catalog_has_every_code(self) -> None:
        """Language parity: every explained code must also be explained in Japanese."""
        from lune.explanations_ja import EXPLANATIONS_JA

        self.assertEqual(sorted(EXPLANATIONS_JA), sorted(EXPLANATIONS))
        for code, entry in EXPLANATIONS_JA.items():
            self.assertTrue(entry.title and entry.summary and entry.fix, code)
            has_japanese = any(ord(ch) > 0x3000 for ch in entry.title + entry.summary)
            self.assertTrue(has_japanese, f"{code}: Japanese entry looks untranslated")

    def test_render_explanation_japanese(self) -> None:
        text = render_explanation("TYP0007", lang="ja")
        assert text is not None
        self.assertIn("error[TYP0007]", text)
        self.assertIn("直し方:", text)
        self.assertIn("witness", text)
        self.assertIsNone(render_explanation("ZZZ9999", lang="ja"))
        # unknown languages fall back to English labels/catalog
        self.assertIn("How to fix:", render_explanation("TYP0007", lang="fr"))

    def test_explain_command_lang_flag(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            code = explain_command(["TYP0001", "--lang", "ja"])
        self.assertEqual(code, 0)
        self.assertIn("未定義の名前", out.getvalue())
        err = io.StringIO()
        with redirect_stderr(err):
            code = explain_command(["TYP0001", "--lang", "de"])
        self.assertEqual(code, 2)
        self.assertIn("unsupported language", err.getvalue())

    def test_japanese_error_index_document_is_in_sync(self) -> None:
        doc_path = LUNE_DIR.parent / "documents" / "ERROR_INDEX_JA.md"
        self.assertEqual(
            doc_path.read_text(encoding="utf-8"),
            render_error_index(lang="ja"),
            "documents/ERROR_INDEX_JA.md is stale — regenerate with "
            "`./bin/lune explain --index --lang ja > documents/ERROR_INDEX_JA.md`",
        )

    def test_error_index_lists_every_code(self) -> None:
        text = render_error_index()
        for code in EXPLANATIONS:
            self.assertIn(f"## {code}", text)
            self.assertIn(f"[`{code}`](#{code.lower()})", text)

    def test_error_index_document_is_in_sync(self) -> None:
        doc_path = LUNE_DIR.parent / "documents" / "ERROR_INDEX.md"
        self.assertEqual(
            doc_path.read_text(encoding="utf-8"),
            render_error_index(),
            "documents/ERROR_INDEX.md is stale — regenerate with "
            "`./bin/lune explain --index > documents/ERROR_INDEX.md`",
        )

    def test_explain_index_flag_prints_catalog(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            code = explain_command(["--index"])
        self.assertEqual(code, 0)
        self.assertIn("## TYP0007", out.getvalue())

    def test_explain_command_prints_and_succeeds(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            code = explain_command(["TYP0007"])
        self.assertEqual(code, 0)
        self.assertIn("error[TYP0007]", out.getvalue())

    def test_explain_command_unknown_code_fails(self) -> None:
        err = io.StringIO()
        with redirect_stderr(err):
            code = explain_command(["BOGUS"])
        self.assertEqual(code, 1)
        self.assertIn("available codes", err.getvalue())

    def test_explain_command_requires_one_argument(self) -> None:
        err = io.StringIO()
        with redirect_stderr(err):
            code = explain_command([])
        self.assertEqual(code, 2)

    def test_main_routes_explain_subcommand(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(["explain", "TYP0001"])
        self.assertEqual(code, 0)
        self.assertIn("undefined name", out.getvalue())

    def test_diagnostic_footer_is_opt_in(self) -> None:
        diag = Diagnostic(code="TYP0007", severity="error", message="boom")
        self.assertNotIn("lune explain", format_diagnostic(diag))
        self.assertIn("lune explain TYP0007", format_diagnostic(diag, explain_hint=True))

    def test_diagnostic_footer_only_for_known_codes(self) -> None:
        diag = Diagnostic(code="ZZZ9999", severity="error", message="boom")
        self.assertNotIn("lune explain", format_diagnostic(diag, explain_hint=True))

    def test_check_error_shows_explain_hint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.lune"
            path.write_text("let x: Int = true\n", encoding="utf-8")
            err = io.StringIO()
            with redirect_stderr(err):
                code = main([str(path), "--check"])
        self.assertEqual(code, 1)
        self.assertIn("lune explain TYP0003", err.getvalue())


if __name__ == "__main__":
    unittest.main()
