from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from lune.cli import main
from lune.repl import ReplSession


EMPTY_FOLD_SOURCE = """module repro

record Stats:
    count: Int

let empty = Stats(count = 0)

let emptySummary = fold([], empty, fn a x -> a)
let twice = fold([], fold([], empty, fn a x -> a), fn a x -> a)
"""


class EvalDisplayTests(unittest.TestCase):
    def eval_binding(self, source: str, name: str) -> tuple[int, str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.lune"
            path.write_text(source, encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = main([str(path), "--eval", name])
        return code, out.getvalue()

    def test_eval_prints_record_returned_by_fold_over_empty_list(self) -> None:
        # fold over [] hands back the initial value untouched, so the binding
        # is a thunk whose value is *another* thunk (the one bound to `empty`).
        # Display forces what it needs (VALUE_DISPLAY_SPEC.md §5), which means
        # forcing the whole chain to WHNF -- stopping after one step used to
        # print the Python repr of the inner thunk.
        code, output = self.eval_binding(EMPTY_FOLD_SOURCE, "emptySummary")
        self.assertEqual(code, 0)
        self.assertEqual(output, "{ count = 0 }\n")

    def test_eval_prints_value_behind_a_longer_thunk_chain(self) -> None:
        code, output = self.eval_binding(EMPTY_FOLD_SOURCE, "twice")
        self.assertEqual(code, 0)
        self.assertEqual(output, "{ count = 0 }\n")

    def test_eval_never_prints_internal_representations(self) -> None:
        # VALUE_DISPLAY_SPEC.md §4: display shows Lune surface syntax, never
        # the evaluator's own objects.
        _, output = self.eval_binding(EMPTY_FOLD_SOURCE, "emptySummary")
        for internal in ("Thunk(", "LazyValue(", "NameExpr(", "<lune."):
            self.assertNotIn(internal, output)

    def test_eval_and_repl_render_the_same_value_identically(self) -> None:
        # VALUE_DISPLAY_SPEC.md §1: the REPL and CLI displays agree. The REPL
        # forced the binding once before formatting it, so it survived the
        # shallow-force bug that `--eval` exposed.
        _, output = self.eval_binding(EMPTY_FOLD_SOURCE, "emptySummary")
        session = ReplSession()
        session.submit("record Stats:\n    count: Int\n")
        session.submit("let empty = Stats(count = 0)\n")
        result = session.submit("fold([], empty, fn a x -> a)\n")
        self.assertEqual(result.message, f"{output.rstrip()} : Stats")


if __name__ == "__main__":
    unittest.main()
