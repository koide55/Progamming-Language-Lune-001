from __future__ import annotations

import unittest

from lune.evaluator import DataValue, LuneRuntimeError, RecordValue, ThunkState, eval_source, force_value, format_value


class EvaluatorTests(unittest.TestCase):
    def value_of(self, source: str, name: str):
        env = eval_source(source)
        return force_value(env.lookup_raw(name))

    def test_let_arithmetic(self) -> None:
        self.assertEqual(self.value_of("let answer = 1 + 2 * 3\n", "answer"), 7)

    def test_function_call_uses_lazy_arguments(self) -> None:
        source = """
def first(a: Int, b: Int): Int =
    a

let answer = first(10, crash())
"""
        self.assertEqual(self.value_of(source, "answer"), 10)

    def test_lambda_partial_application_returns_closure(self) -> None:
        source = """
let add = fn x y -> x + y
let inc = add(1)
let answer = inc(41)
"""
        self.assertEqual(self.value_of(source, "answer"), 42)

    def test_function_decl_partial_application_returns_closure(self) -> None:
        source = """
def add(x: Int, y: Int): Int =
    x + y

let inc = add(1)
let answer = inc(41)
"""
        self.assertEqual(self.value_of(source, "answer"), 42)

    def test_curried_function_can_receive_multiple_call_arguments(self) -> None:
        source = """
let add = fn x -> fn y -> x + y
let answer = add(20, 22)
"""
        self.assertEqual(self.value_of(source, "answer"), 42)

    def test_zero_arg_function_call(self) -> None:
        source = """
let thunk = fn -> 42
let answer = thunk()
"""
        self.assertEqual(self.value_of(source, "answer"), 42)

    def test_partial_application_preserves_lazy_arguments(self) -> None:
        source = """
let first = fn x y -> x
let keepCrash = first(crash())
let answer = keepCrash(42)
"""
        env = eval_source(source)
        with self.assertRaises(LuneRuntimeError):
            force_value(env.lookup_raw("answer"))

    def test_partial_application_forces_strict_arguments_when_closure_is_built(self) -> None:
        source = """
let second = fn !x y -> y
let partial = second(crash())
let answer = seq partial 42
"""
        env = eval_source(source)
        with self.assertRaises(LuneRuntimeError):
            force_value(env.lookup_raw("answer"))

    def test_force_lazy_evaluates_thunk(self) -> None:
        source = """
let delayed = lazy 1 + 2
let answer = force delayed
"""
        self.assertEqual(self.value_of(source, "answer"), 3)

    def test_match_constructor(self) -> None:
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
        self.assertEqual(self.value_of(source, "answer"), 42)

    def test_match_does_not_force_unused_field(self) -> None:
        source = """
type Box =
    | Box(value: Int)

def ignore(box: Box): Int =
    match box:
        | Box(_) -> 1

let answer = ignore(Box(crash()))
"""
        self.assertEqual(self.value_of(source, "answer"), 1)

    def test_force_exposes_error(self) -> None:
        source = """
let delayed = lazy crash()
let answer = force delayed
"""
        env = eval_source(source)
        with self.assertRaises(LuneRuntimeError):
            force_value(env.lookup_raw("answer"))

    def test_constructor_value_repr(self) -> None:
        source = """
type Option[T] =
    | Some(value: T)
    | None

let answer = Some(1)
"""
        value = self.value_of(source, "answer")
        self.assertIsInstance(value, DataValue)
        self.assertEqual(repr(value), "Some(1)")

    def test_list_repr_is_lisp_style(self) -> None:
        self.assertEqual(repr(self.value_of("let answer = range(1, 3)\n", "answer")), "(1 2)")
        self.assertEqual(repr(self.value_of("let answer = Nil\n", "answer")), "()")

    def test_list_literal_evaluates_to_list(self) -> None:
        self.assertEqual(repr(self.value_of("let answer = [1, 2, 3]\n", "answer")), "(1 2 3)")
        self.assertEqual(repr(self.value_of("let answer = []\n", "answer")), "()")

    def test_lisp_style_list_literal_evaluates_to_list(self) -> None:
        self.assertEqual(repr(self.value_of("let answer = (1 2 3)\n", "answer")), "(1 2 3)")
        self.assertEqual(repr(self.value_of("let answer = ((1 2) (3 4))\n", "answer")), "((1 2) (3 4))")

    def test_list_literal_elements_are_lazy(self) -> None:
        source = """
let items = [1, crash()]
let answer = head(items)
"""
        self.assertEqual(repr(self.value_of(source, "answer")), "Some(1)")

    def test_value_display_uses_lune_syntax(self) -> None:
        source = """
record User:
    name: String
    age: Int

let user = User(name = "Ada", age = 36)
let values = ["Ada", "Lune"]
let option = Some("ok")
let pair = ("Ada", true)
"""
        env = eval_source(source)
        self.assertEqual(format_value(env.lookup_raw("user")), '{ name = "Ada", age = 36 }')
        self.assertEqual(format_value(env.lookup_raw("values")), '("Ada" "Lune")')
        self.assertEqual(format_value(env.lookup_raw("option")), 'Some("ok")')
        self.assertEqual(format_value(env.lookup_raw("pair")), '("Ada", true)')

    def test_constructor_partial_application_returns_constructor_closure(self) -> None:
        source = """
type Pair =
    | Pair(left: Int, right: Int)

let withOne = Pair(1)
let pair = withOne(41)
let answer =
    match pair:
        | Pair(left, right) -> left + right
"""
        self.assertEqual(self.value_of(source, "answer"), 42)

    def test_record_construction_and_field_access(self) -> None:
        source = """
record User:
    name: String
    age: Int

let ada = User(name = "Ada", age = 36)
let name = ada.name
let age = ada.age
"""
        env = eval_source(source)
        ada = force_value(env.lookup_raw("ada"))
        self.assertIsInstance(ada, RecordValue)
        self.assertEqual(force_value(env.lookup_raw("name")), "Ada")
        self.assertEqual(force_value(env.lookup_raw("age")), 36)

    def test_record_field_access_forces_only_selected_field(self) -> None:
        source = """
record User:
    name: String
    age: Int

let ada = User(name = crash(), age = 36)
let answer = ada.age
"""
        self.assertEqual(self.value_of(source, "answer"), 36)

    def test_record_strict_field_is_forced_at_construction(self) -> None:
        source = """
record User:
    !name: String
    age: Int

let ada = User(name = crash(), age = 36)
let answer = seq ada 42
"""
        env = eval_source(source)
        with self.assertRaises(LuneRuntimeError):
            force_value(env.lookup_raw("answer"))

    def test_while_loop_updates_outer_vars(self) -> None:
        source = """
let answer =
    var i = 0
    var total = 0
    while i < 5:
        total = total + i
        i = i + 1
    total
"""
        self.assertEqual(self.value_of(source, "answer"), 10)

    def test_while_condition_is_checked_each_iteration(self) -> None:
        source = """
let answer =
    var i = 0
    while i < 3:
        i = i + 1
    i
"""
        self.assertEqual(self.value_of(source, "answer"), 3)

    def test_for_loop_iterates_list(self) -> None:
        source = """
let answer =
    var total = 0
    for x in range(1, 5):
        total = total + x
    total
"""
        self.assertEqual(self.value_of(source, "answer"), 10)

    def test_for_loop_supports_patterns(self) -> None:
        source = """
let pairs = [(1, 10), (2, 20)]
let answer =
    var total = 0
    for (left, right) in pairs:
        total = total + left + right
    total
"""
        self.assertEqual(self.value_of(source, "answer"), 33)

    def test_for_loop_does_not_evaluate_body_for_empty_list(self) -> None:
        source = """
let answer =
    for _ in Nil:
        crash()
    42
"""
        self.assertEqual(self.value_of(source, "answer"), 42)

    def test_successful_thunk_is_memoized(self) -> None:
        source = """
let x = tick()
let answer = x + x
let count = tickCount()
"""
        env = eval_source(source)
        self.assertEqual(force_value(env.lookup_raw("answer")), 2)
        self.assertEqual(force_value(env.lookup_raw("count")), 1)

    def test_failed_thunk_is_memoized(self) -> None:
        source = """
let delayed = seq tick() crash()
let count = tickCount()
"""
        env = eval_source(source)
        delayed = env.lookup_raw("delayed")
        with self.assertRaises(LuneRuntimeError):
            force_value(delayed)
        with self.assertRaises(LuneRuntimeError):
            force_value(delayed)
        self.assertEqual(force_value(env.lookup_raw("count")), 1)
        self.assertEqual(delayed.state, ThunkState.FAILED)

    def test_division_by_zero_is_a_lune_diagnostic(self) -> None:
        env = eval_source("let x = 1 / 0\nlet y = 5 % 0\n")
        with self.assertRaisesRegex(LuneRuntimeError, "division by zero") as ctx:
            force_value(env.lookup_raw("x"))
        self.assertEqual(ctx.exception.diagnostic.code, "RUN0006")
        self.assertTrue(ctx.exception.diagnostic.hints)
        with self.assertRaisesRegex(LuneRuntimeError, "division by zero"):
            force_value(env.lookup_raw("y"))

    def test_recursive_thunk_is_detected(self) -> None:
        env = eval_source("let x = x\n")
        with self.assertRaisesRegex(LuneRuntimeError, "recursive thunk evaluation") as ctx:
            force_value(env.lookup_raw("x"))
        self.assertEqual(ctx.exception.diagnostic.code, "RUN0005")
        self.assertTrue(ctx.exception.diagnostic.hints)

    def test_mutually_recursive_thunks_are_detected(self) -> None:
        env = eval_source("let a = b\nlet b = a\n")
        with self.assertRaisesRegex(LuneRuntimeError, "recursive thunk evaluation") as ctx:
            force_value(env.lookup_raw("a"))
        self.assertEqual(ctx.exception.diagnostic.code, "RUN0005")

    def test_strict_function_argument_is_evaluated_even_when_unused(self) -> None:
        source = """
def first(a: Int, !b: Int): Int =
    a

let answer = first(10, crash())
"""
        env = eval_source(source)
        with self.assertRaises(LuneRuntimeError):
            force_value(env.lookup_raw("answer"))

    def test_strict_let_is_evaluated_during_module_evaluation(self) -> None:
        with self.assertRaises(LuneRuntimeError):
            eval_source("strict let answer = crash()\n")

    def test_strict_constructor_field_is_evaluated_at_construction(self) -> None:
        source = """
type Box =
    | Box(!value: Int)

let answer = Box(crash())
"""
        env = eval_source(source)
        with self.assertRaises(LuneRuntimeError):
            force_value(env.lookup_raw("answer"))

    def test_seq_forces_only_outer_constructor(self) -> None:
        source = """
type Box =
    | Box(value: Int)

let box = Box(crash())
let answer = seq box 1
"""
        self.assertEqual(self.value_of(source, "answer"), 1)

    def test_deep_force_forces_constructor_fields(self) -> None:
        source = """
type Box =
    | Box(value: Int)

let box = Box(crash())
let answer = deepForce box
"""
        env = eval_source(source)
        with self.assertRaises(LuneRuntimeError):
            force_value(env.lookup_raw("answer"))

    def test_literal_pattern_forces_field(self) -> None:
        source = """
type Box =
    | Box(value: Int)

def check(box: Box): Int =
    match box:
        | Box(0) -> 0
        | Box(_) -> 1

let answer = check(Box(crash()))
"""
        env = eval_source(source)
        with self.assertRaises(LuneRuntimeError):
            force_value(env.lookup_raw("answer"))

    # --- null safety ---

    def test_match_null_pattern_selects_case(self) -> None:
        source = """
def f(x: Int?): Int =
    match x:
        | null -> -1
        | v -> v + 100

let hit = f(5)
let miss = f(null)
"""
        self.assertEqual(self.value_of(source, "hit"), 105)
        self.assertEqual(self.value_of(source, "miss"), -1)

    def test_null_coalescing_uses_value_when_present(self) -> None:
        self.assertEqual(self.value_of("let x: Int? = 7\nlet r = x ?? 0\n", "r"), 7)

    def test_null_coalescing_uses_fallback_when_null(self) -> None:
        self.assertEqual(self.value_of("let x: Int? = null\nlet r = x ?? 0\n", "r"), 0)

    def test_null_coalescing_short_circuits_fallback(self) -> None:
        # the fallback must not be evaluated when the left operand is non-null
        self.assertEqual(self.value_of("let x: Int? = 7\nlet r = x ?? crash()\n", "r"), 7)

    def test_null_comparison(self) -> None:
        source = "let x: Int? = null\nlet a = x == null\nlet b = x != null\n"
        self.assertIs(self.value_of(source, "a"), True)
        self.assertIs(self.value_of(source, "b"), False)

    def test_safe_navigation_reads_field_when_present(self) -> None:
        source = """
record User:
    name: String
    age: Int

let u: User? = User(name = "Ada", age = 36)
let r = u?.name
"""
        self.assertEqual(self.value_of(source, "r"), "Ada")

    def test_safe_navigation_returns_null_when_receiver_null(self) -> None:
        source = """
record User:
    name: String
    age: Int

let u: User? = null
let r = u?.name
"""
        self.assertIsNone(self.value_of(source, "r"))

    def test_flow_narrowing_runtime(self) -> None:
        source = """
def f(x: Int?): Int =
    if x != null then x + 1 else 0

let a = f(41)
let b = f(null)
"""
        self.assertEqual(self.value_of(source, "a"), 42)
        self.assertEqual(self.value_of(source, "b"), 0)


if __name__ == "__main__":
    unittest.main()
