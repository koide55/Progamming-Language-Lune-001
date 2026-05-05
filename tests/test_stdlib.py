from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main()
