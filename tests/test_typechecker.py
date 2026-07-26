from __future__ import annotations

import unittest

from lune.typechecker import (
    FLOAT,
    INT,
    BOOL,
    STRING,
    FunctionType,
    LuneTypeError,
    Type,
    check_source,
    suggestion_hints,
)


class TypeCheckerTests(unittest.TestCase):
    def test_checks_let_annotation(self) -> None:
        env = check_source("let answer: Int = 42\n")
        self.assertEqual(env.lookup_value("answer"), INT)

    def test_int_division_result_type_is_double(self) -> None:
        env = check_source("let ratio: Double = 7 / 2\n")
        self.assertEqual(env.lookup_value("ratio"), FLOAT)

    def test_int_division_result_cannot_be_used_as_int(self) -> None:
        with self.assertRaises(LuneTypeError):
            check_source("let ratio: Int = 7 / 2\n")

    def test_floor_division_keeps_int(self) -> None:
        env = check_source("let half: Int = 7 // 2\n")
        self.assertEqual(env.lookup_value("half"), INT)

    def test_floor_division_keeps_double(self) -> None:
        env = check_source("let half: Double = 7.0 // 2.0\n")
        self.assertEqual(env.lookup_value("half"), FLOAT)

    def test_floor_division_result_is_not_double_for_ints(self) -> None:
        with self.assertRaises(LuneTypeError):
            check_source("let half: Double = 7 // 2\n")

    def test_floor_division_rejects_non_numeric(self) -> None:
        with self.assertRaises(LuneTypeError):
            check_source('let bad = "a" // "b"\n')

    def test_floor_division_does_not_mix_int_and_double(self) -> None:
        with self.assertRaises(LuneTypeError):
            check_source("let bad = 7 // 2.0\n")

    def test_floor_division_lets_an_int_branch_typecheck(self) -> None:
        # The motivating case: a Collatz step must stay Int in both branches.
        source = """
def next(n: Int): Int =
    if n % 2 == 0 then n // 2 else 3 * n + 1
"""
        env = check_source(source)
        self.assertEqual(env.lookup_value("next"), FunctionType((INT,), INT))

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

    def test_rejects_named_adt_constructor_arguments(self) -> None:
        """`name = value` is record-only syntax; ADT constructors are positional."""
        source = """
type Entry =
    | Income(label: String, amount: Int)

let entry = Income(label = "a", amount = 1)
"""
        with self.assertRaises(LuneTypeError) as context:
            check_source(source)
        self.assertEqual(context.exception.diagnostic.code, "TYP0012")

    def test_rejects_reordered_named_adt_constructor_arguments(self) -> None:
        """Reordering by name used to fail as a confusing TYP0003 type mismatch."""
        source = """
type Entry =
    | Income(label: String, amount: Int)

let entry = Income(amount = 1, label = "a")
"""
        with self.assertRaises(LuneTypeError) as context:
            check_source(source)
        self.assertEqual(context.exception.diagnostic.code, "TYP0012")

    def test_rejects_named_arguments_that_would_swap_same_typed_fields(self) -> None:
        """The dangerous case: same-typed fields swapped with no type error at all."""
        source = """
type Point =
    | P(x: Int, y: Int)

let p = P(y = 1, x = 2)
"""
        with self.assertRaises(LuneTypeError) as context:
            check_source(source)
        diagnostic = context.exception.diagnostic
        self.assertEqual(diagnostic.code, "TYP0012")
        # the caret points at the offending label, not the whole call
        assert diagnostic.primary is not None
        self.assertEqual(diagnostic.primary.span.start_line, 5)
        self.assertEqual(diagnostic.primary.span.start_column, 11)
        # no machine-applicable fix: dropping `y = ` would keep the swapped order
        self.assertEqual(diagnostic.fixes, [])

    def test_rejects_named_function_call_arguments(self) -> None:
        """Plain functions bind positionally and curry, so labels are rejected too."""
        source = """
def sub(a: Int, b: Int): Int = a - b

let n = sub(b = 1, a = 10)
"""
        with self.assertRaises(LuneTypeError) as context:
            check_source(source)
        self.assertEqual(context.exception.diagnostic.code, "TYP0012")

    def test_accepts_positional_adt_construction_and_named_record_construction(self) -> None:
        """The asymmetry both checks enforce: ADT positional, record named."""
        source = """
type Point =
    | P(x: Int, y: Int)

record User:
    name: String
    age: Int

let p = P(2, 1)
let ada = User(age = 36, name = "Ada")
"""
        env = check_source(source)
        self.assertEqual(env.lookup_value("p"), Type("Point"))
        self.assertEqual(env.lookup_value("ada"), Type("User"))

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

    def test_compound_assignment_keeps_the_target_type(self) -> None:
        # `x op= e` is typed as `x = x op e` (SYNTAX_SPEC.md section 14.1)
        for op in ("+=", "-=", "*=", "//=", "%="):
            source = f"""
let answer =
    var x = 10
    x {op} 5
    x
"""
            with self.subTest(op=op):
                self.assertEqual(check_source(source).lookup_value("answer"), INT)

    def test_compound_assignment_is_an_expression_of_the_target_type(self) -> None:
        source = """
let answer =
    var x = 10
    let y: Int = x += 5
    y
"""
        self.assertEqual(check_source(source).lookup_value("answer"), INT)

    def test_compound_division_assignment_rejects_int_target(self) -> None:
        # `/` yields Double even for Int / Int, so `x /= 2` cannot target an Int
        source = """
let answer =
    var x = 10
    x /= 2
    x
"""
        with self.assertRaisesRegex(LuneTypeError, r"compound assignment `/=`: expected Int, got Double") as ctx:
            check_source(source)
        # the diagnostic points at the assignment
        self.assertEqual(ctx.exception.diagnostic.primary.span.start_line, 4)

    def test_compound_division_assignment_accepts_double_target(self) -> None:
        source = """
let answer =
    var x = 7.0
    x /= 2.0
    x
"""
        self.assertEqual(check_source(source).lookup_value("answer"), FLOAT)

    def test_compound_floor_division_assignment_accepts_int_target(self) -> None:
        # the `//=` counterpart of the `/=` rejection above: `//` keeps the
        # operand type, so an Int target stays Int
        source = """
let answer =
    var x = 10
    x //= 2
    x
"""
        self.assertEqual(check_source(source).lookup_value("answer"), INT)

    def test_compound_assignment_concatenates_strings(self) -> None:
        source = """
let answer =
    var s = "ab"
    s += "cd"
    s
"""
        self.assertEqual(check_source(source).lookup_value("answer"), STRING)

    def test_compound_assignment_rejects_non_numeric_target(self) -> None:
        # the diagnostic names the operator the user wrote, not the desugared one
        source = """
let answer =
    var flag = true
    flag += true
    flag
"""
        with self.assertRaisesRegex(LuneTypeError, r"\+=: expected numeric type, got Bool"):
            check_source(source)

    def test_compound_assignment_rejects_mismatched_operand(self) -> None:
        source = """
let answer =
    var x = 10
    x += 1.5
    x
"""
        with self.assertRaisesRegex(LuneTypeError, r"\+=: expected Int, got Double"):
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


class RefutablePatternTests(unittest.TestCase):
    def assert_refutable(self, source: str, context: str, rendered: str) -> None:
        with self.assertRaises(LuneTypeError) as ctx:
            check_source(source)
        diagnostic = ctx.exception.diagnostic
        self.assertEqual(diagnostic.code, "TYP0008")
        self.assertIn(f"refutable pattern in {context} binding: {rendered}", diagnostic.message)

    def test_accepts_name_and_wildcard_let(self) -> None:
        check_source("let x = 42\nlet _ = 43\n")

    def test_accepts_tuple_let(self) -> None:
        check_source(
            """
let pair = (1, "one")
let (x, name) = pair
"""
        )

    def test_accepts_single_constructor_let(self) -> None:
        check_source(
            """
type Wrap[T] =
    | Wrap(value: T)

let w = Wrap(42)
let Wrap(inner) = w
"""
        )

    def test_accepts_tuple_for_pattern(self) -> None:
        check_source(
            """
def f(pairs: List[Tuple[Int, Int]]): Unit =
    for (left, right) in pairs:
        println(left + right)
"""
        )

    def test_accepts_let_with_any_value(self) -> None:
        check_source(
            """
import java.time.LocalDate

let Some(x) = LocalDate.now()
"""
        )

    def test_rejects_option_let(self) -> None:
        self.assert_refutable(
            """
let opt = Some(42)
let Some(value) = opt
""",
            "let",
            "Some(value)",
        )

    def test_rejects_literal_in_tuple_let(self) -> None:
        self.assert_refutable(
            """
let pair = (1, 2)
let (1, y) = pair
""",
            "let",
            "(1, y)",
        )

    def test_rejects_refutable_let_in_expression(self) -> None:
        self.assert_refutable(
            """
let opt = Some(42)
let answer = let Some(x) = opt in x
""",
            "let",
            "Some(x)",
        )

    def test_rejects_refutable_for_pattern(self) -> None:
        self.assert_refutable(
            """
def f(xs: List[Option[Int]]): Unit =
    for Some(x) in xs:
        println(x)
""",
            "for",
            "Some(x)",
        )

    def test_rejects_multi_constructor_nested_in_tuple(self) -> None:
        self.assert_refutable(
            """
let pair = (Some(1), 2)
let (Some(x), y) = pair
""",
            "let",
            "(Some(x), y)",
        )


class UnreachableCaseTests(unittest.TestCase):
    def assert_unreachable(self, source: str, rendered: str) -> None:
        env = check_source(source)
        codes = [warning.code for warning in env.warnings]
        self.assertIn("TYP0009", codes)
        messages = [warning.message for warning in env.warnings]
        self.assertIn(f"unreachable match case: {rendered}", messages)

    def assert_no_warnings(self, source: str) -> None:
        env = check_source(source)
        self.assertEqual(env.warnings, [])

    def test_warns_duplicate_constructor_case(self) -> None:
        self.assert_unreachable(
            """
def f(o: Option[Int]): Int =
    match o:
        | Some(x) -> x
        | None -> 0
        | Some(y) -> y + 1
""",
            "Some(y)",
        )

    def test_warns_case_after_wildcard(self) -> None:
        self.assert_unreachable(
            """
def f(n: Int): Int =
    match n:
        | 0 -> 0
        | _ -> 1
        | 5 -> 5
""",
            "5",
        )

    def test_warns_wildcard_after_complete_bool_coverage(self) -> None:
        self.assert_unreachable(
            """
def f(b: Bool): Int =
    match b:
        | true -> 1
        | false -> 0
        | _ -> 2
""",
            "_",
        )

    def test_warns_guarded_case_shadowed_by_unguarded(self) -> None:
        self.assert_unreachable(
            """
def f(o: Option[Int]): Int =
    match o:
        | Some(x) -> x
        | None -> 0
        | Some(y) if y > 0 -> y
""",
            "Some(y)",
        )

    def test_no_warning_for_case_after_guarded_pattern(self) -> None:
        self.assert_no_warnings(
            """
def f(o: Option[Int]): Int =
    match o:
        | Some(x) if x > 0 -> x
        | Some(y) -> 0 - y
        | None -> 0
"""
        )

    def test_no_warning_for_or_case_with_reachable_branch(self) -> None:
        self.assert_no_warnings(
            """
def f(o: Option[Int]): Int =
    match o:
        | Some(1) -> 1
        | (Some(_) | None) -> 0
"""
        )

    def test_no_warning_for_exhaustive_match(self) -> None:
        self.assert_no_warnings(
            """
def f(o: Option[Int]): Int =
    match o:
        | Some(x) -> x
        | None -> 0
"""
        )

    def test_no_warning_for_any_scrutinee(self) -> None:
        self.assert_no_warnings(
            """
import java.time.LocalDate

def f(): Int =
    match LocalDate:
        | 1 -> 1
        | 1 -> 2
"""
        )


class LocalTypeInferenceTests(unittest.TestCase):
    def test_annotation_propagates_into_lambda(self) -> None:
        env = check_source("let inc: Int -> Int = fn x -> x + 1\n")
        self.assertEqual(env.lookup_value("inc"), FunctionType((INT,), INT))
        self.assertEqual(env.warnings, [])

    def test_annotation_checks_lambda_body(self) -> None:
        with self.assertRaises(LuneTypeError):
            check_source("let bad: Int -> Int = fn x -> x && true\n")

    def test_map_resolves_type_variable(self) -> None:
        env = check_source(
            """
let numbers = [1, 2, 3]
let doubled = map(numbers, fn x -> x * 2)
"""
        )
        self.assertEqual(env.lookup_value("doubled"), Type("List", (INT,)))
        self.assertEqual(env.warnings, [])

    def test_map_checks_lambda_body(self) -> None:
        with self.assertRaises(LuneTypeError):
            check_source("let bad = map([1, 2, 3], fn x -> x && true)\n")

    def test_filter_and_fold_infer_lambda_params(self) -> None:
        env = check_source(
            """
let numbers = [1, 2, 3]
let evens = filter(numbers, fn x -> x % 2 == 0)
let total = fold(numbers, 0, fn acc x -> acc + x)
"""
        )
        self.assertEqual(env.lookup_value("evens"), Type("List", (INT,)))
        self.assertEqual(env.lookup_value("total"), INT)
        self.assertEqual(env.warnings, [])

    def test_empty_list_takes_expected_type(self) -> None:
        env = check_source("let empty: List[Int] = []\n")
        self.assertEqual(env.lookup_value("empty"), Type("List", (INT,)))

    def test_list_of_lambdas_with_annotation(self) -> None:
        env = check_source("let fs: List[Int -> Int] = [fn x -> x + 1]\n")
        self.assertEqual(env.lookup_value("fs"), Type("List", (FunctionType((INT,), INT),)))
        self.assertEqual(env.warnings, [])

    def test_expected_type_distributes_into_if_branches(self) -> None:
        env = check_source("let f: Int -> Int = if true then (fn x -> x) else (fn x -> x + 1)\n")
        self.assertEqual(env.lookup_value("f"), FunctionType((INT,), INT))
        self.assertEqual(env.warnings, [])

    def test_curried_annotation_propagates(self) -> None:
        env = check_source("let add: Int -> Int -> Int = fn x -> fn y -> x + y\n")
        self.assertEqual(env.warnings, [])

    def test_annotated_lambda_param_checked_against_expected(self) -> None:
        check_source("let f: Int -> Int = fn x: Int -> x\n")
        with self.assertRaises(LuneTypeError):
            check_source("let f: Int -> Int = fn x: Bool -> 1\n")

    def test_rejects_lambda_with_too_many_params(self) -> None:
        with self.assertRaises(LuneTypeError) as ctx:
            check_source("let f: Int -> Int = fn x y -> x\n")
        self.assertEqual(ctx.exception.diagnostic.code, "TYP0005")

    def test_return_annotation_propagates_into_body_lambda(self) -> None:
        env = check_source(
            """
def makeAdder(n: Int): Int -> Int =
    fn x -> x + n
"""
        )
        self.assertEqual(env.warnings, [])

    def test_warns_lambda_without_context(self) -> None:
        env = check_source("let f = fn x -> x\n")
        codes = [warning.code for warning in env.warnings]
        self.assertIn("TYP0010", codes)

    def test_no_warning_with_call_context(self) -> None:
        env = check_source("let xs = map([1, 2, 3], fn x -> x)\n")
        self.assertEqual(env.warnings, [])

    def test_recursive_def_without_return_annotation(self) -> None:
        with self.assertRaises(LuneTypeError) as ctx:
            check_source(
                """
def fact(n: Int) =
    if n <= 1 then 1 else n * fact(n - 1)
"""
            )
        self.assertEqual(ctx.exception.diagnostic.code, "TYP0011")

    def test_recursive_def_with_return_annotation(self) -> None:
        env = check_source(
            """
def fact(n: Int): Int =
    if n <= 1 then 1 else n * fact(n - 1)
"""
        )
        self.assertEqual(env.lookup_value("fact"), FunctionType((INT,), INT))

    # --- nullable types (T?) ---

    def test_allows_null_for_nullable_annotation(self) -> None:
        env = check_source("let x: String? = null\n")
        self.assertEqual(env.lookup_value("x"), Type("Nullable", (STRING,)))

    def test_allows_non_null_value_for_nullable_annotation(self) -> None:
        env = check_source('let x: String? = "hi"\n')
        self.assertEqual(env.lookup_value("x"), Type("Nullable", (STRING,)))

    def test_rejects_null_for_non_nullable_annotation(self) -> None:
        with self.assertRaises(LuneTypeError):
            check_source("let x: String = null\n")

    def test_rejects_nullable_where_non_null_expected(self) -> None:
        with self.assertRaises(LuneTypeError):
            check_source("let x: String? = null\nlet y: String = x\n")

    def test_nullable_argument_accepts_both_value_and_null(self) -> None:
        source = """
def f(x: Int?): Int? =
    x
let a = f(3)
let b = f(null)
"""
        env = check_source(source)
        self.assertEqual(env.lookup_value("a"), Type("Nullable", (INT,)))
        self.assertEqual(env.lookup_value("b"), Type("Nullable", (INT,)))

    # --- pipeline operator (|>) ---

    def test_pipeline_operator_type_checks(self) -> None:
        source = """
def inc(n: Int): Int =
    n + 1
let r: Int = 5 |> inc
"""
        env = check_source(source)
        self.assertEqual(env.lookup_value("r"), INT)

    def test_pipeline_operator_chains(self) -> None:
        source = """
def inc(n: Int): Int =
    n + 1
let r = 5 |> inc |> inc
"""
        env = check_source(source)
        self.assertEqual(env.lookup_value("r"), INT)

    def test_pipeline_operator_supports_partial_application(self) -> None:
        source = """
def add(x: Int, y: Int): Int =
    x + y
let g = 5 |> add
"""
        env = check_source(source)
        self.assertEqual(env.lookup_value("g"), FunctionType((INT,), INT))

    def test_pipeline_operator_rejects_argument_mismatch(self) -> None:
        source = """
def inc(n: Int): Int =
    n + 1
let r = "s" |> inc
"""
        with self.assertRaises(LuneTypeError):
            check_source(source)

    # --- null pattern & match narrowing ---

    def test_match_null_pattern_narrows_binding(self) -> None:
        source = """
let x: Int? = null
let r = match x:
    | null -> 0
    | v -> v + 1
"""
        env = check_source(source)
        self.assertEqual(env.lookup_value("r"), INT)

    def test_match_bare_name_is_nullable_when_null_unhandled(self) -> None:
        # `v` is still Int? here, so arithmetic on it must fail.
        source = """
let x: Int? = null
let r = match x:
    | v -> v + 1
"""
        with self.assertRaises(LuneTypeError):
            check_source(source)

    def test_match_nullable_requires_null_case(self) -> None:
        source = """
def f(b: Bool?): Int =
    match b:
        | true -> 1
        | false -> 0
"""
        with self.assertRaises(LuneTypeError) as ctx:
            check_source(source)
        self.assertEqual(ctx.exception.diagnostic.code, "TYP0007")

    def test_match_nullable_requires_inner_exhaustive(self) -> None:
        source = """
def f(b: Bool?): Int =
    match b:
        | null -> -1
        | true -> 1
"""
        with self.assertRaises(LuneTypeError) as ctx:
            check_source(source)
        self.assertEqual(ctx.exception.diagnostic.code, "TYP0007")

    def test_match_nullable_exhaustive_ok(self) -> None:
        source = """
def f(b: Bool?): Int =
    match b:
        | null -> -1
        | true -> 1
        | false -> 0
"""
        self.assertEqual(check_source(source).lookup_value("f"), FunctionType((Type("Nullable", (BOOL,)),), INT))

    def test_match_nullable_unreachable_after_catch_all(self) -> None:
        source = """
def f(x: Int?): Int =
    match x:
        | null -> 0
        | v -> v
        | 0 -> 9
"""
        codes = [warning.code for warning in check_source(source).warnings]
        self.assertIn("TYP0009", codes)

    # --- ?? null-coalescing ---

    def test_null_coalescing_returns_non_null(self) -> None:
        env = check_source("let x: Int? = null\nlet r = x ?? 0\n")
        self.assertEqual(env.lookup_value("r"), INT)

    def test_null_coalescing_both_nullable_stays_nullable(self) -> None:
        env = check_source("let x: Int? = null\nlet y: Int? = null\nlet r = x ?? y\n")
        self.assertEqual(env.lookup_value("r"), Type("Nullable", (INT,)))

    def test_null_coalescing_rejects_non_nullable_left(self) -> None:
        with self.assertRaises(LuneTypeError):
            check_source("let x: Int = 1\nlet r = x ?? 0\n")

    def test_null_coalescing_rejects_type_mismatch(self) -> None:
        with self.assertRaises(LuneTypeError):
            check_source('let x: Int? = null\nlet r = x ?? "s"\n')

    # --- null comparison ---

    def test_compare_nullable_with_null(self) -> None:
        env = check_source("let x: Int? = null\nlet r = x == null\n")
        self.assertEqual(env.lookup_value("r"), BOOL)

    def test_compare_nullable_with_inner_value(self) -> None:
        env = check_source("let x: Int? = null\nlet r = x != 5\n")
        self.assertEqual(env.lookup_value("r"), BOOL)

    def test_compare_nullable_with_wrong_type_rejected(self) -> None:
        with self.assertRaises(LuneTypeError):
            check_source('let x: Int? = null\nlet r = x == "s"\n')

    # --- ?. safe navigation ---

    def test_safe_navigation_returns_nullable_member(self) -> None:
        source = """
record User:
    name: String
    age: Int
let u: User? = null
let r = u?.name
"""
        self.assertEqual(check_source(source).lookup_value("r"), Type("Nullable", (STRING,)))

    def test_safe_navigation_rejects_non_nullable_receiver(self) -> None:
        source = """
record User:
    name: String
def f(u: User): String? =
    u?.name
"""
        with self.assertRaises(LuneTypeError):
            check_source(source)

    def test_plain_navigation_on_nullable_rejected(self) -> None:
        source = """
record User:
    name: String
def f(u: User?): String =
    u.name
"""
        with self.assertRaises(LuneTypeError):
            check_source(source)

    def test_safe_navigation_chains(self) -> None:
        source = """
record Addr:
    city: String
record User:
    addr: Addr
let u: User? = null
let r = u?.addr?.city
"""
        self.assertEqual(check_source(source).lookup_value("r"), Type("Nullable", (STRING,)))

    # --- if-condition flow narrowing ---

    def test_flow_narrowing_then_branch(self) -> None:
        source = """
def f(x: Int?): Int =
    if x != null then x + 1 else 0
"""
        self.assertEqual(check_source(source).lookup_value("f"), FunctionType((Type("Nullable", (INT,)),), INT))

    def test_flow_narrowing_else_branch_on_eq_null(self) -> None:
        source = """
def f(x: Int?): Int =
    if x == null then 0 else x + 1
"""
        self.assertEqual(check_source(source).lookup_value("f"), FunctionType((Type("Nullable", (INT,)),), INT))

    def test_flow_narrowing_does_not_leak_to_other_branch(self) -> None:
        source = """
def f(x: Int?): Int =
    if x != null then 0 else x + 1
"""
        with self.assertRaises(LuneTypeError):
            check_source(source)

    # --- "did you mean" suggestions ---

    def test_suggestion_hints_helper(self) -> None:
        self.assertEqual(suggestion_hints("filterr", ["filter", "map", "fold"]), ["did you mean `filter`?"])
        self.assertEqual(suggestion_hints("xyz", ["filter", "map"]), [])

    def test_undefined_name_suggests_local(self) -> None:
        with self.assertRaises(LuneTypeError) as ctx:
            check_source("let total = 10\nlet x = totl + 1\n")
        self.assertIn("did you mean `total`?", ctx.exception.diagnostic.hints)

    def test_undefined_name_suggests_prelude(self) -> None:
        with self.assertRaises(LuneTypeError) as ctx:
            check_source("let xs = rang(1, 5)\n")
        self.assertIn("did you mean `range`?", ctx.exception.diagnostic.hints)

    def test_undefined_name_no_suggestion_when_far(self) -> None:
        with self.assertRaises(LuneTypeError) as ctx:
            check_source("let x = zzzzz + 1\n")
        self.assertEqual(ctx.exception.diagnostic.hints, [])

    def test_unknown_field_access_suggests_field(self) -> None:
        source = """
record User:
    name: String
    age: Int
let u = User(name = "Ada", age = 1)
let n = u.naem
"""
        with self.assertRaises(LuneTypeError) as ctx:
            check_source(source)
        self.assertIn("did you mean `name`?", ctx.exception.diagnostic.hints)

    def test_unexpected_construction_field_suggests_field(self) -> None:
        source = """
record User:
    name: String
let u = User(naem = "Ada")
"""
        with self.assertRaises(LuneTypeError) as ctx:
            check_source(source)
        self.assertIn("did you mean `name`?", ctx.exception.diagnostic.hints)


class ConstructorExpectedTypeTests(unittest.TestCase):
    """Expected types fix the free type variables of generic constructors and
    let `null` join value branches (LOCAL_TYPE_INFERENCE_SPEC.md section 5.6)."""

    def test_if_branches_instantiate_option_constructors(self) -> None:
        source = "def maybeDiv(x: Int, y: Int): Option[Double] = if y == 0 then None else Some(x / y)\n"
        env = check_source(source)
        self.assertEqual(env.lookup_value("maybeDiv"), FunctionType((INT, INT), Type("Option", (FLOAT,))))

    def test_match_arms_instantiate_result_constructors(self) -> None:
        source = """
def safeDiv(x: Int, y: Int): Result[Double, String] =
    match y:
        | 0 -> Err("div by zero")
        | _ -> Ok(x / y)
"""
        env = check_source(source)
        self.assertEqual(env.lookup_value("safeDiv"), FunctionType((INT, INT), Type("Result", (FLOAT, STRING))))

    def test_let_annotation_instantiates_bare_none(self) -> None:
        env = check_source("let nothing: Option[Double] = None\n")
        self.assertEqual(env.lookup_value("nothing"), Type("Option", (FLOAT,)))

    def test_let_annotation_instantiates_bare_nil(self) -> None:
        env = check_source("let empty: List[Int] = Nil\n")
        self.assertEqual(env.lookup_value("empty"), Type("List", (INT,)))

    def test_nullable_return_joins_null_and_value_branches(self) -> None:
        source = "def maybeDiv(x: Int, y: Int): Double? = if y == 0 then null else x / y\n"
        env = check_source(source)
        self.assertEqual(env.lookup_value("maybeDiv"), FunctionType((INT, INT), Type("Nullable", (FLOAT,))))

    def test_nullable_match_joins_null_and_value_arms(self) -> None:
        source = """
def bump(x: Int?): Int? =
    match x:
        | null -> null
        | v -> v + 1
"""
        env = check_source(source)
        self.assertEqual(env.lookup_value("bump"), FunctionType((Type("Nullable", (INT,)),), Type("Nullable", (INT,))))

    def test_concrete_argument_instantiates_constructor(self) -> None:
        source = """
def describe(r: Result[Int, String]): String =
    match r:
        | Ok(v) -> "ok"
        | Err(e) -> e

let s = describe(Ok(42))
let f = describe(Err("boom"))
"""
        env = check_source(source)
        self.assertEqual(env.lookup_value("s"), STRING)
        self.assertEqual(env.lookup_value("f"), STRING)

    def test_record_field_instantiates_constructor(self) -> None:
        source = """
record Holder:
    value: Option[Double]

let h = Holder(value = None)
"""
        env = check_source(source)
        self.assertEqual(env.lookup_value("h"), Type("Holder"))

    def test_user_defined_generic_adt_instantiates(self) -> None:
        source = """
type Box[T] =
    | Empty
    | Full(value: T)

def f(b: Bool): Box[Int] = if b then Full(1) else Empty()
"""
        env = check_source(source)
        self.assertEqual(env.lookup_value("f"), FunctionType((BOOL,), Type("Box", (INT,))))

    def test_generic_argument_unification_still_works(self) -> None:
        env = check_source("let a = getOrElse(Some(42), 0)\nlet b = getOrElse(None, 7)\n")
        self.assertEqual(env.lookup_value("a"), INT)
        self.assertEqual(env.lookup_value("b"), INT)

    def test_rejects_wrong_constructor_payload_for_annotation(self) -> None:
        with self.assertRaises(LuneTypeError):
            check_source('let bad: Option[Double] = Some("s")\n')

    def test_rejects_wrong_payload_in_instantiated_branch(self) -> None:
        with self.assertRaises(LuneTypeError):
            check_source('def f(x: Int, y: Int): Option[Double] = if y == 0 then None else Some("s")\n')

    def test_rejects_mismatched_err_payload(self) -> None:
        source = """
def safeDiv(x: Int, y: Int): Result[Double, String] =
    match y:
        | 0 -> Err(42)
        | _ -> Ok(x / y)
"""
        with self.assertRaises(LuneTypeError):
            check_source(source)

    def test_rejects_wrong_concrete_argument_instantiation(self) -> None:
        source = """
def describe(r: Result[Int, String]): String =
    match r:
        | Ok(v) -> "ok"
        | Err(e) -> e

let s = describe(Ok(1.5))
"""
        with self.assertRaises(LuneTypeError):
            check_source(source)

    def test_rejects_null_branch_for_non_nullable_return(self) -> None:
        with self.assertRaises(LuneTypeError):
            check_source("def f(y: Int): Double = if y == 0 then null else 1.5\n")

    def test_rigid_type_param_still_rejected(self) -> None:
        with self.assertRaises(LuneTypeError):
            check_source("def weird[T](x: T): Double = x\n")


if __name__ == "__main__":
    unittest.main()
