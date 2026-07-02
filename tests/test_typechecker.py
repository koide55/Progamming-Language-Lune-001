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
        self.assertEqual(repr(env.lookup_value("add")), "Int -> Int -> Int")

    def test_checks_curried_function_type_annotations(self) -> None:
        source = """
let addA: Int -> Int -> Int = fn x y -> x + y
let addB: (Int, Int) -> Int = fn x y -> x + y
let nested: Int -> Int -> Int = fn x -> fn y -> x + y
let inc = addA(1)
let answer = nested(20, 22)
"""
        env = check_source(source)
        expected = FunctionType((INT, INT), INT)
        self.assertEqual(env.lookup_value("addA"), expected)
        self.assertEqual(env.lookup_value("addB"), expected)
        self.assertEqual(env.lookup_value("nested"), expected)
        self.assertEqual(env.lookup_value("inc"), FunctionType((INT,), INT))
        self.assertEqual(env.lookup_value("answer"), INT)

    def test_checks_higher_order_curried_function_annotation(self) -> None:
        source = """
def applyTwice(f: Int -> Int, x: Int): Int =
    f(f(x))

let answer = applyTwice(fn x -> x + 1, 40)
"""
        env = check_source(source)
        self.assertEqual(env.lookup_value("applyTwice"), FunctionType((FunctionType((INT,), INT), INT), INT))
        self.assertEqual(env.lookup_value("answer"), INT)

    def test_checks_zero_arg_function_type_annotation(self) -> None:
        source = """
let thunk: () -> Int = fn -> 42
let answer = thunk()
"""
        env = check_source(source)
        self.assertEqual(env.lookup_value("thunk"), FunctionType((), INT))
        self.assertEqual(env.lookup_value("answer"), INT)

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
let more = (4 5 6)
let empty: List[Int] = []
"""
        )
        self.assertEqual(env.lookup_value("numbers"), Type("List", (INT,)))
        self.assertEqual(env.lookup_value("more"), Type("List", (INT,)))
        self.assertEqual(env.lookup_value("empty"), Type("List", (INT,)))

    def test_rejects_mixed_list_literal_type(self) -> None:
        with self.assertRaises(LuneTypeError):
            check_source("let bad = [1, true]\n")
        with self.assertRaises(LuneTypeError):
            check_source("let bad = (1 true)\n")

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


class MatchExhaustivenessTests(unittest.TestCase):
    def assert_missing(self, source: str, witness: str) -> None:
        with self.assertRaises(LuneTypeError) as ctx:
            check_source(source)
        diagnostic = ctx.exception.diagnostic
        self.assertEqual(diagnostic.code, "TYP0007")
        self.assertIn(f"missing case {witness}", diagnostic.message)

    def test_accepts_full_option_match(self) -> None:
        check_source(
            """
def f(o: Option[Int]): Int =
    match o:
        | Some(x) -> x
        | None -> 0
"""
        )

    def test_accepts_wildcard_case(self) -> None:
        check_source(
            """
def f(o: Option[Int]): Int =
    match o:
        | Some(x) -> x
        | _ -> 0
"""
        )

    def test_accepts_name_case(self) -> None:
        check_source(
            """
def f(o: Option[Int]): Int =
    match o:
        | other -> 0
"""
        )

    def test_accepts_bool_literal_match(self) -> None:
        check_source(
            """
def f(b: Bool): Int =
    match b:
        | true -> 1
        | false -> 0
"""
        )

    def test_accepts_guarded_case_with_unguarded_fallbacks(self) -> None:
        check_source(
            """
def f(o: Option[Int]): Int =
    match o:
        | Some(x) if x > 0 -> x
        | Some(x) -> 0 - x
        | None -> 0
"""
        )

    def test_accepts_or_pattern_covering_all_constructors(self) -> None:
        check_source(
            """
def f(o: Option[Int]): Int =
    match o:
        | (Some(_) | None) -> 0
"""
        )

    def test_accepts_tuple_of_bools(self) -> None:
        check_source(
            """
def f(p: Tuple[Bool, Bool]): Int =
    match p:
        | (true, true) -> 3
        | (true, false) -> 2
        | (false, true) -> 1
        | (false, false) -> 0
"""
        )

    def test_accepts_int_literals_with_wildcard(self) -> None:
        check_source(
            """
def f(n: Int): Int =
    match n:
        | 0 -> 0
        | _ -> 1
"""
        )

    def test_accepts_nested_option_match(self) -> None:
        check_source(
            """
def f(o: Option[Option[Int]]): Int =
    match o:
        | Some(Some(x)) -> x
        | Some(None) -> 0
        | None -> 0
"""
        )

    def test_accepts_any_scrutinee(self) -> None:
        check_source(
            """
import java.time.LocalDate

def f(): Int =
    match LocalDate:
        | 1 -> 1
"""
        )

    def test_accepts_user_defined_adt_match(self) -> None:
        check_source(
            """
type Color =
    | Red
    | Green
    | Blue

def f(c: Color): Int =
    match c:
        | Red -> 0
        | Green -> 1
        | Blue -> 2
"""
        )

    def test_rejects_missing_none_case(self) -> None:
        self.assert_missing(
            """
def f(o: Option[Int]): Int =
    match o:
        | Some(x) -> x
""",
            "None",
        )

    def test_rejects_missing_some_case(self) -> None:
        self.assert_missing(
            """
def f(o: Option[Int]): Int =
    match o:
        | None -> 0
""",
            "Some(_)",
        )

    def test_rejects_missing_bool_literal(self) -> None:
        self.assert_missing(
            """
def f(b: Bool): Int =
    match b:
        | true -> 1
""",
            "false",
        )

    def test_rejects_int_literals_without_wildcard(self) -> None:
        self.assert_missing(
            """
def f(n: Int): Int =
    match n:
        | 0 -> 0
        | 1 -> 1
""",
            "_",
        )

    def test_rejects_guard_only_coverage(self) -> None:
        self.assert_missing(
            """
def f(o: Option[Int]): Int =
    match o:
        | Some(x) if x > 0 -> x
        | None -> 0
""",
            "Some(_)",
        )

    def test_rejects_missing_nested_list_case(self) -> None:
        self.assert_missing(
            """
def f(xs: List[Int]): Int =
    match xs:
        | Nil -> 0
        | Cons(x, Nil) -> x
""",
            "Cons(_, Cons(_, _))",
        )

    def test_rejects_missing_tuple_combination(self) -> None:
        self.assert_missing(
            """
def f(p: Tuple[Bool, Bool]): Int =
    match p:
        | (true, true) -> 2
        | (true, false) -> 1
        | (false, true) -> 0
""",
            "(false, false)",
        )

    def test_rejects_missing_user_defined_constructor(self) -> None:
        self.assert_missing(
            """
type Color =
    | Red
    | Green
    | Blue

def f(c: Color): Int =
    match c:
        | Red -> 0
        | Blue -> 2
""",
            "Green",
        )

    def test_rejects_missing_result_case(self) -> None:
        self.assert_missing(
            """
def f(r: Result[Int, String]): Int =
    match r:
        | Ok(value) -> value
""",
            "Err(_)",
        )


if __name__ == "__main__":
    unittest.main()
