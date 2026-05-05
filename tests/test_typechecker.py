from __future__ import annotations

import unittest

from lune.typechecker import INT, BOOL, FunctionType, LuneTypeError, Type, check_source


class TypeCheckerTests(unittest.TestCase):
    def test_checks_let_annotation(self) -> None:
        env = check_source("let answer: Int = 42\n")
        self.assertEqual(env.lookup_value("answer"), INT)

    def test_rejects_let_annotation_mismatch(self) -> None:
        with self.assertRaises(LuneTypeError):
            check_source("let answer: Int = true\n")

    def test_checks_function_return_type(self) -> None:
        source = """
def add(x: Int, y: Int): Int =
    x + y
"""
        env = check_source(source)
        self.assertEqual(env.lookup_value("add"), FunctionType((INT, INT), INT))

    def test_infers_lambda_partial_application_type(self) -> None:
        source = """
let add = fn x: Int y: Int -> x + y
let inc = add(1)
let answer = inc(41)
"""
        env = check_source(source)
        self.assertEqual(env.lookup_value("inc"), FunctionType((INT,), INT))
        self.assertEqual(env.lookup_value("answer"), INT)

    def test_infers_function_decl_partial_application_type(self) -> None:
        source = """
def add(x: Int, y: Int): Int =
    x + y

let inc = add(1)
let answer = inc(41)
"""
        env = check_source(source)
        self.assertEqual(env.lookup_value("inc"), FunctionType((INT,), INT))
        self.assertEqual(env.lookup_value("answer"), INT)

    def test_rejects_function_return_mismatch(self) -> None:
        source = """
def bad(x: Int): Bool =
    x + 1
"""
        with self.assertRaises(LuneTypeError):
            check_source(source)

    def test_rejects_call_argument_mismatch(self) -> None:
        source = """
def add(x: Int, y: Int): Int =
    x + y

let answer = add(1, true)
"""
        with self.assertRaises(LuneTypeError):
            check_source(source)

    def test_rejects_builtin_partial_application(self) -> None:
        with self.assertRaises(LuneTypeError):
            check_source("let startsAtOne = range(1)\n")

    def test_checks_tuple_literal_as_variadic_builtin(self) -> None:
        check_source("let pair = (1, true)\n")

    def test_checks_generic_adt_and_match(self) -> None:
        source = """
type Option[T] =
    | Some(value: T)
    | None

def getOrElse[T](option: Option[T], defaultValue: T): T =
    match option:
        | Some(value) -> value
        | None -> defaultValue

let answer = getOrElse(Some(42), 0)
"""
        env = check_source(source)
        self.assertEqual(env.lookup_value("answer"), INT)

    def test_infers_constructor_partial_application_type(self) -> None:
        source = """
type Pair =
    | Pair(left: Int, right: Int)

let withOne = Pair(1)
let pair = withOne(41)
"""
        env = check_source(source)
        self.assertEqual(env.lookup_value("withOne"), FunctionType((INT,), Type("Pair")))
        self.assertEqual(env.lookup_value("pair"), Type("Pair"))

    def test_checks_record_construction_and_field_access(self) -> None:
        source = """
record User:
    name: String
    age: Int

let ada = User(name = "Ada", age = 36)
let name = ada.name
let age = ada.age
"""
        env = check_source(source)
        self.assertEqual(env.lookup_value("ada"), Type("User"))
        self.assertEqual(env.lookup_value("name"), Type("String"))
        self.assertEqual(env.lookup_value("age"), INT)

    def test_checks_generic_record_field_access(self) -> None:
        source = """
record Box[T]:
    value: T

let box = Box(value = 42)
let value = box.value
"""
        env = check_source(source)
        self.assertEqual(env.lookup_value("box"), Type("Box", (INT,)))
        self.assertEqual(env.lookup_value("value"), INT)

    def test_rejects_missing_record_field(self) -> None:
        source = """
record User:
    name: String
    age: Int

let ada = User(name = "Ada")
"""
        with self.assertRaises(LuneTypeError) as context:
            check_source(source)
        self.assertEqual(context.exception.diagnostic.code, "REC0003")

    def test_rejects_unknown_record_field_access(self) -> None:
        source = """
record User:
    name: String

let ada = User(name = "Ada")
let age = ada.age
"""
        with self.assertRaises(LuneTypeError) as context:
            check_source(source)
        self.assertEqual(context.exception.diagnostic.code, "REC0002")

    def test_rejects_positional_record_construction(self) -> None:
        source = """
record User:
    name: String

let ada = User("Ada")
"""
        with self.assertRaises(LuneTypeError) as context:
            check_source(source)
        self.assertEqual(context.exception.diagnostic.code, "REC0006")

    def test_rejects_generic_adt_argument_mismatch(self) -> None:
        source = """
type Option[T] =
    | Some(value: T)
    | None

def getOrElse[T](option: Option[T], defaultValue: T): T =
    match option:
        | Some(value) -> value
        | None -> defaultValue

let answer = getOrElse(Some(42), true)
"""
        with self.assertRaises(LuneTypeError):
            check_source(source)

    def test_rejects_non_bool_if_condition(self) -> None:
        with self.assertRaises(LuneTypeError):
            check_source("let answer = if 1 then 2 else 3\n")

    def test_rejects_if_branch_mismatch(self) -> None:
        with self.assertRaises(LuneTypeError):
            check_source("let answer = if true then 1 else false\n")

    def test_checks_while_loop_as_unit(self) -> None:
        source = """
let loop =
    var i = 0
    while i < 3:
        i = i + 1
"""
        env = check_source(source)
        self.assertEqual(env.lookup_value("loop"), Type("Unit"))

    def test_rejects_non_bool_while_condition(self) -> None:
        source = """
let answer =
    while 1:
        42
"""
        with self.assertRaises(LuneTypeError):
            check_source(source)

    def test_checks_for_loop_as_unit(self) -> None:
        source = """
let loop =
    var total = 0
    for x in range(1, 4):
        total = total + x
"""
        env = check_source(source)
        self.assertEqual(env.lookup_value("loop"), Type("Unit"))

    def test_for_loop_binds_pattern_item_type(self) -> None:
        source = """
let pairs = [(1, 10), (2, 20)]
let answer =
    var total = 0
    for (left, right) in pairs:
        total = total + left + right
    total
"""
        env = check_source(source)
        self.assertEqual(env.lookup_value("answer"), INT)

    def test_rejects_for_loop_over_non_list(self) -> None:
        source = """
let answer =
    for x in 42:
        x
"""
        with self.assertRaises(LuneTypeError):
            check_source(source)

    def test_checks_list_literal_type(self) -> None:
        env = check_source(
            """
let numbers = [1, 2, 3]
let empty: List[Int] = []
"""
        )
        self.assertEqual(env.lookup_value("numbers"), Type("List", (INT,)))
        self.assertEqual(env.lookup_value("empty"), Type("List", (INT,)))

    def test_rejects_mixed_list_literal_type(self) -> None:
        with self.assertRaises(LuneTypeError):
            check_source("let bad = [1, true]\n")

    def test_checks_lazy_and_force(self) -> None:
        source = """
let delayed = lazy (1 + 2)
let answer = force delayed
"""
        env = check_source(source)
        self.assertEqual(env.lookup_value("delayed"), Type("Lazy", (INT,)))
        self.assertEqual(env.lookup_value("answer"), INT)

    def test_external_imports_are_any_in_v0_1(self) -> None:
        source = """
import java.time.LocalDate

def today(): IO[String] =
    IO:
        LocalDate.now().toString()
"""
        check_source(source)


if __name__ == "__main__":
    unittest.main()
