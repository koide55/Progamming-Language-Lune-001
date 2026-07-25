from __future__ import annotations

import contextlib
import io
import pathlib
import unittest

from lune.evaluator import DataValue, eval_source, force_value, format_value
from lune.typechecker import INT, STRING, Type, check_source


ROOT = pathlib.Path(__file__).resolve().parents[1]


class StdlibTests(unittest.TestCase):
    def value_of(self, source: str, name: str):
        env = eval_source(source)
        return force_value(env.lookup_raw(name))

    def assert_data(self, value, constructor: str) -> DataValue:
        value = force_value(value)
        self.assertIsInstance(value, DataValue)
        self.assertEqual(value.constructor, constructor)
        return value

    def list_to_py(self, value) -> list[object]:
        result = []
        current = force_value(value)
        while True:
            current = force_value(current)
            if current.constructor == "Nil":
                return result
            self.assertEqual(current.constructor, "Cons")
            result.append(force_value(current.fields[0]))
            current = current.fields[1]

    def test_option_is_available_without_user_definition(self) -> None:
        source = """
let someValue = getOrElse(Some(42), 0)
let noneValue = getOrElse(None, 7)
"""
        self.assertEqual(self.value_of(source, "someValue"), 42)
        self.assertEqual(self.value_of(source, "noneValue"), 7)

    def test_option_map_is_lazy_for_none(self) -> None:
        source = """
let answer = optionMap(None, fn x: Int -> crash())
"""
        value = self.value_of(source, "answer")
        self.assert_data(value, "None")

    def test_result_helpers(self) -> None:
        source = """
let ok = unwrapOr(Ok(42), 0)
let err = unwrapOr(Err("nope"), 7)
let mapped = resultMap(Ok(20), fn x: Int -> x + 22)
"""
        env = eval_source(source)
        self.assertEqual(force_value(env.lookup_raw("ok")), 42)
        self.assertEqual(force_value(env.lookup_raw("err")), 7)
        mapped = self.assert_data(force_value(env.lookup_raw("mapped")), "Ok")
        self.assertEqual(force_value(mapped.fields[0]), 42)

    def test_list_helpers(self) -> None:
        source = """
let numbers = range(1, 5)
let doubled = map(numbers, fn x: Int -> x * 2)
let evens = filter(doubled, fn x: Int -> x % 4 == 0)
let total = fold(numbers, 0, fn acc: Int x: Int -> acc + x)
let first = head(numbers)
let rest = tail(numbers)
let firstTwo = take(numbers, 2)
let afterTwo = drop(numbers, 2)
let tooMany = take(numbers, 99)
let noneLeft = drop(numbers, 99)
let size = length(numbers)
"""
        env = eval_source(source)
        self.assertEqual(self.list_to_py(env.lookup_raw("numbers")), [1, 2, 3, 4])
        self.assertEqual(self.list_to_py(env.lookup_raw("doubled")), [2, 4, 6, 8])
        self.assertEqual(self.list_to_py(env.lookup_raw("evens")), [4, 8])
        self.assertEqual(force_value(env.lookup_raw("total")), 10)
        first = self.assert_data(force_value(env.lookup_raw("first")), "Some")
        self.assertEqual(force_value(first.fields[0]), 1)
        rest = self.assert_data(force_value(env.lookup_raw("rest")), "Some")
        self.assertEqual(self.list_to_py(rest.fields[0]), [2, 3, 4])
        self.assertEqual(self.list_to_py(env.lookup_raw("firstTwo")), [1, 2])
        self.assertEqual(self.list_to_py(env.lookup_raw("afterTwo")), [3, 4])
        self.assertEqual(self.list_to_py(env.lookup_raw("tooMany")), [1, 2, 3, 4])
        self.assertEqual(self.list_to_py(env.lookup_raw("noneLeft")), [])
        self.assertEqual(force_value(env.lookup_raw("size")), 4)

    def test_fold_over_empty_list_displays_the_initial_value(self) -> None:
        # fold over [] returns the initial value untouched, so the binding is a
        # thunk wrapping another thunk. format_value must force that chain on
        # its own: the callers that pre-force (value_of, the REPL) hide the bug
        # that CLI `--eval` -- which formats the raw binding -- ran into.
        source = """
record Stats:
    count: Int
let empty = Stats(count = 0)
let emptySummary = fold([], empty, fn a x -> a)
"""
        env = eval_source(source)
        self.assertEqual(format_value(env.lookup_raw("emptySummary")), "{ count = 0 }")

    def test_take_zero_does_not_force_list(self) -> None:
        source = """
let answer = take(crash(), 0)
"""
        self.assertEqual(self.list_to_py(self.value_of(source, "answer")), [])

    def test_take_preserves_lazy_tail(self) -> None:
        source = """
let answer = head(take([1, crash()], 1))
"""
        self.assertEqual(format_value(self.value_of(source, "answer")), "Some(1)")

    def test_core_helpers(self) -> None:
        source = """
let text = show(Some(1))
let listText = show(range(1, 3))
let stringText = show("Ada")
let same = id(42)
let kept = const(1, crash())
let flipped = not(false)
"""
        env = eval_source(source)
        self.assertEqual(force_value(env.lookup_raw("text")), "Some(1)")
        self.assertEqual(force_value(env.lookup_raw("listText")), "(1 2)")
        self.assertEqual(force_value(env.lookup_raw("stringText")), '"Ada"')
        self.assertEqual(force_value(env.lookup_raw("same")), 42)
        self.assertEqual(force_value(env.lookup_raw("kept")), 1)
        self.assertEqual(force_value(env.lookup_raw("flipped")), True)

    def test_show_function_values_use_short_form(self) -> None:
        source = """
def greet(name: String): String =
    "hello, " + name

let named = show(greet)
let partial = show(greet())
let anonymous = show(fn x -> x)
let builtin = show(println)
let constructor = show(Some)
"""
        env = eval_source(source)
        self.assertEqual(force_value(env.lookup_raw("named")), "<fn greet>")
        self.assertEqual(force_value(env.lookup_raw("partial")), "<fn greet>")
        self.assertEqual(force_value(env.lookup_raw("anonymous")), "<fn>")
        self.assertEqual(force_value(env.lookup_raw("builtin")), "<fn println>")
        self.assertEqual(force_value(env.lookup_raw("constructor")), "<fn Some>")

    def test_println_prints_function_values_with_short_form(self) -> None:
        source = """
def greet(name: String): String =
    "hello, " + name

let main = println(greet(), fn x -> x, println)
"""
        env = eval_source(source)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            force_value(env.lookup_raw("main"))
        self.assertEqual(buffer.getvalue(), "<fn greet> <fn> <fn println>\n")

    def test_stdlib_sample_typechecks(self) -> None:
        env = check_source((ROOT / "samples" / "stdlib.lune").read_text(encoding="utf-8"))
        self.assertEqual(env.lookup_value("optionValue"), INT)
        self.assertEqual(env.lookup_value("noneValue"), INT)
        self.assertEqual(env.lookup_value("numbers"), Type("List", (INT,)))
        self.assertEqual(env.lookup_value("doubled"), Type("List", (INT,)))
        self.assertEqual(env.lookup_value("firstTwo"), Type("List", (INT,)))
        self.assertEqual(env.lookup_value("afterTwo"), Type("List", (INT,)))
        self.assertEqual(env.lookup_value("total"), INT)
        self.assertEqual(env.lookup_value("size"), INT)
        self.assertEqual(env.lookup_value("shown"), STRING)

    def test_list_tools_sample(self) -> None:
        source = (ROOT / "samples" / "list_tools.lune").read_text(encoding="utf-8")
        type_env = check_source(source)
        self.assertEqual(type_env.lookup_value("doubled"), Type("List", (INT,)))
        self.assertEqual(type_env.lookup_value("firstThree"), Type("List", (INT,)))
        self.assertEqual(type_env.lookup_value("afterThree"), Type("List", (INT,)))
        env = eval_source(source)
        self.assertEqual(format_value(env.lookup_raw("doubled")), "(2 4 6 8 10 12)")
        self.assertEqual(format_value(env.lookup_raw("firstThree")), "(1 2 3)")
        self.assertEqual(format_value(env.lookup_raw("afterThree")), "(4 5 6)")
        self.assertEqual(format_value(env.lookup_raw("adultNames")), '("Grace")')
        self.assertEqual(force_value(env.lookup_raw("totalAge")), 176)
        self.assertEqual(format_value(env.lookup_raw("lazySlice")), "(1)")

    # --- infinite / lazy streams ---

    def test_naturals_from_take(self) -> None:
        env = eval_source("let xs = take(naturalsFrom(1), 5)\n")
        self.assertEqual(self.list_to_py(env.lookup_raw("xs")), [1, 2, 3, 4, 5])

    def test_iterate_builds_stream(self) -> None:
        source = "def double(n: Int): Int =\n    n * 2\nlet xs = take(iterate(double, 1), 5)\n"
        self.assertEqual(self.list_to_py(self.value_of(source, "xs")), [1, 2, 4, 8, 16])

    def test_repeat_is_infinite(self) -> None:
        self.assertEqual(self.list_to_py(self.value_of("let xs = take(repeat(7), 3)\n", "xs")), [7, 7, 7])

    def test_map_and_filter_on_infinite_stream(self) -> None:
        evens = "let e = take(filter(naturalsFrom(1), fn x: Int -> x % 2 == 0), 4)\n"
        self.assertEqual(self.list_to_py(self.value_of(evens, "e")), [2, 4, 6, 8])
        mapped = "def double(n: Int): Int =\n    n * 2\nlet m = take(map(naturalsFrom(1), double), 4)\n"
        self.assertEqual(self.list_to_py(self.value_of(mapped, "m")), [2, 4, 6, 8])

    def test_head_of_infinite_stream_terminates(self) -> None:
        first = self.assert_data(self.value_of("let f = head(naturalsFrom(10))\n", "f"), "Some")
        self.assertEqual(force_value(first.fields[0]), 10)

    def test_stream_builtins_typecheck(self) -> None:
        env = check_source(
            """
def double(n: Int): Int =
    n * 2
let a: List[Int] = take(iterate(double, 1), 3)
let b: List[Int] = take(naturalsFrom(1), 3)
let c: List[Int] = take(repeat(5), 3)
"""
        )
        self.assertEqual(env.lookup_value("a"), Type("List", (INT,)))
        self.assertEqual(env.lookup_value("b"), Type("List", (INT,)))
        self.assertEqual(env.lookup_value("c"), Type("List", (INT,)))

    # --- stream combinators ---

    def test_take_while(self) -> None:
        src = "def lt5(n: Int): Bool =\n    n < 5\nlet xs = takeWhile(naturalsFrom(1), lt5)\n"
        self.assertEqual(self.list_to_py(self.value_of(src, "xs")), [1, 2, 3, 4])

    def test_drop_while(self) -> None:
        src = "def lt5(n: Int): Bool =\n    n < 5\nlet xs = take(dropWhile(naturalsFrom(1), lt5), 3)\n"
        self.assertEqual(self.list_to_py(self.value_of(src, "xs")), [5, 6, 7])

    def test_take_after_drop_on_infinite_stream(self) -> None:
        # drop returns the (still lazy) tail of the stream; take must force it
        # to WHNF instead of reading fields off the unevaluated LazyValue.
        src = "let xs = take(drop(naturalsFrom(1), 1), 3)\n"
        self.assertEqual(self.list_to_py(self.value_of(src, "xs")), [2, 3, 4])

    def test_head_after_drop_on_infinite_stream(self) -> None:
        src = "let x = head(drop(naturalsFrom(1), 1))\n"
        self.assertEqual(format_value(self.value_of(src, "x")), "Some(2)")

    def test_take_after_drop_on_finite_list(self) -> None:
        src = "let xs = take(drop([1, 2, 3, 4, 5], 2), 2)\n"
        self.assertEqual(self.list_to_py(self.value_of(src, "xs")), [3, 4])
        src = "let xs = take(drop(range(1, 10), 2), 2)\n"
        self.assertEqual(self.list_to_py(self.value_of(src, "xs")), [3, 4])

    def test_drop_does_not_force_dropped_elements(self) -> None:
        # drop walks the spine of the dropped prefix but must not force the
        # element values themselves.
        src = "let x = head(drop([crash(), 2], 1))\n"
        self.assertEqual(format_value(self.value_of(src, "x")), "Some(2)")

    def test_zip_pairs_and_stops_at_shorter(self) -> None:
        src = "let xs = zip(naturalsFrom(1), [10, 20])\n"
        self.assertEqual(format_value(self.value_of(src, "xs")), "((1, 10) (2, 20))")

    def test_zip_with_combines_elementwise(self) -> None:
        src = "def add(a: Int, b: Int): Int =\n    a + b\nlet xs = take(zipWith(naturalsFrom(1), naturalsFrom(10), add), 3)\n"
        self.assertEqual(self.list_to_py(self.value_of(src, "xs")), [11, 13, 15])

    def test_cycle_repeats_finite_list(self) -> None:
        src = "let xs = take(cycle([1, 2, 3]), 7)\n"
        self.assertEqual(self.list_to_py(self.value_of(src, "xs")), [1, 2, 3, 1, 2, 3, 1])

    def test_cycle_of_empty_is_empty(self) -> None:
        self.assertEqual(self.list_to_py(self.value_of("let xs = cycle([])\n", "xs")), [])

    def stdout_of(self, source: str, name: str) -> str:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.value_of(source, name)
        return out.getvalue()

    def test_println_prints_string_without_quotes(self) -> None:
        output = self.stdout_of('let r = println("hello, world")\n', "r")
        self.assertEqual(output, "hello, world\n")

    def test_println_resolves_escapes_in_string(self) -> None:
        output = self.stdout_of('let r = println("a\\nb")\n', "r")
        self.assertEqual(output, "a\nb\n")

    def test_print_prints_string_without_newline(self) -> None:
        output = self.stdout_of('let r = print("hi")\n', "r")
        self.assertEqual(output, "hi")

    def test_println_uses_show_for_non_strings(self) -> None:
        self.assertEqual(self.stdout_of("let r = println(42)\n", "r"), "42\n")
        self.assertEqual(self.stdout_of("let r = println([1, 2])\n", "r"), "(1 2)\n")
        self.assertEqual(self.stdout_of('let r = println(Some("ok"))\n', "r"), 'Some("ok")\n')

    def test_println_show_keeps_quoted_form(self) -> None:
        output = self.stdout_of('let r = println(show("Ada"))\n', "r")
        self.assertEqual(output, '"Ada"\n')

    def test_combinators_typecheck(self) -> None:
        env = check_source(
            """
def lt5(n: Int): Bool =
    n < 5
def add(a: Int, b: Int): Int =
    a + b
let a: List[Int] = takeWhile(naturalsFrom(1), lt5)
let b: List[Int] = take(dropWhile(naturalsFrom(1), lt5), 2)
let c: List[Int] = take(zipWith(naturalsFrom(1), naturalsFrom(1), add), 2)
let d: List[Int] = take(cycle([1, 2]), 3)
let z = zip(naturalsFrom(1), naturalsFrom(1))
"""
        )
        self.assertEqual(env.lookup_value("a"), Type("List", (INT,)))
        self.assertEqual(env.lookup_value("z"), Type("List", (Type("Tuple", (INT, INT)),)))


if __name__ == "__main__":
    unittest.main()
