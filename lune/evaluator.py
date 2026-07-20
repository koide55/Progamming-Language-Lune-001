from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Callable

from . import nodes as ast
from .diagnostics import Diagnostic, DiagnosticError
from .parser import parse_source


class LuneRuntimeError(DiagnosticError):
    def __init__(self, message: str, code: str = "RUN0006"):
        super().__init__(Diagnostic(code=code, severity="error", message=message))


class Env:
    def __init__(self, parent: Env | None = None):
        self.parent = parent
        self.values: dict[str, Value] = {}

    def define(self, name: str, value: Value) -> None:
        self.values[name] = value

    def set(self, name: str, value: Value) -> None:
        if name in self.values:
            self.values[name] = value
            return
        if self.parent is not None:
            self.parent.set(name, value)
            return
        raise LuneRuntimeError(f"undefined variable: {name}")

    def lookup_raw(self, name: str) -> Value:
        if name in self.values:
            return self.values[name]
        if self.parent is not None:
            return self.parent.lookup_raw(name)
        raise LuneRuntimeError(f"undefined variable: {name}")

    def lookup(self, name: str) -> Value:
        return force_value(self.lookup_raw(name))

    def child(self) -> Env:
        return Env(self)


class ThunkState:
    UNEVALUATED = "unevaluated"
    EVALUATING = "evaluating"
    EVALUATED = "evaluated"
    FAILED = "failed"


Value = object


@dataclass
class Thunk:
    expr: ast.Expr
    env: Env
    state: str = ThunkState.UNEVALUATED
    value: Value | None = None
    error: Exception | None = None

    def force(self) -> Value:
        if self.state == ThunkState.EVALUATED:
            return self.value
        if self.state == ThunkState.FAILED:
            assert self.error is not None
            raise self.error
        if self.state == ThunkState.EVALUATING:
            raise LuneRuntimeError("recursive thunk evaluation")
        self.state = ThunkState.EVALUATING
        try:
            self.value = eval_expr(self.expr, self.env)
            self.state = ThunkState.EVALUATED
        except Exception as exc:
            self.error = exc
            self.state = ThunkState.FAILED
            raise
        return self.value


@dataclass
class LazyValue:
    compute: Callable[[], Value]
    state: str = ThunkState.UNEVALUATED
    value: Value | None = None
    error: Exception | None = None

    def force(self) -> Value:
        if self.state == ThunkState.EVALUATED:
            return self.value
        if self.state == ThunkState.FAILED:
            assert self.error is not None
            raise self.error
        if self.state == ThunkState.EVALUATING:
            raise LuneRuntimeError("recursive thunk evaluation")
        self.state = ThunkState.EVALUATING
        try:
            self.value = self.compute()
            self.state = ThunkState.EVALUATED
        except Exception as exc:
            self.error = exc
            self.state = ThunkState.FAILED
            raise
        return self.value


@dataclass(frozen=True)
class FunctionValue:
    name: str | None
    params: list[ast.Param]
    body: ast.Expr
    env: Env


@dataclass(frozen=True)
class BuiltinFunction:
    name: str
    func: Callable[[list[Value]], Value]
    force_args: bool = True


@dataclass(frozen=True)
class ConstructorValue:
    name: str
    fields: list[ast.Param]

    @property
    def arity(self) -> int:
        return len(self.fields)


@dataclass(frozen=True)
class PartialConstructorValue:
    constructor: ConstructorValue
    bound_fields: list[Value]

    @property
    def remaining_fields(self) -> list[ast.Param]:
        return self.constructor.fields[len(self.bound_fields) :]


@dataclass(frozen=True)
class RecordConstructorValue:
    name: str
    fields: list[ast.RecordField]


@dataclass(frozen=True)
class RecordValue:
    name: str
    field_order: list[str]
    fields: dict[str, Value]

    def __repr__(self) -> str:
        return format_value(self)


@dataclass(frozen=True)
class DataValue:
    constructor: str
    fields: list[Value]

    def __repr__(self) -> str:
        return format_value(self)


@dataclass(frozen=True)
class TupleValue:
    items: list[Value]

    def __repr__(self) -> str:
        return format_value(self)


UNIT = ()


def eval_source(source: str, filename: str = "<input>") -> Env:
    return eval_module(parse_source(source, filename))


def eval_module(module: ast.ModuleFile) -> Env:
    env = initial_env()
    eval_module_into(module, env)
    return env


def eval_module_into(module: ast.ModuleFile, env: Env) -> Env:
    for decl in module.declarations:
        eval_decl(decl, env)
    return env


def initial_env() -> Env:
    env = Env()
    state = {"ticks": 0}
    env.define("__tuple__", BuiltinFunction("__tuple__", lambda args: TupleValue(args), force_args=False))
    env.define("print", BuiltinFunction("print", _builtin_print))
    env.define("println", BuiltinFunction("println", _builtin_println))
    env.define("show", BuiltinFunction("show", lambda args: format_value(args[0])))
    env.define("id", BuiltinFunction("id", lambda args: force_value(args[0])))
    env.define("const", BuiltinFunction("const", lambda args: force_value(args[0]), force_args=False))
    env.define("not", BuiltinFunction("not", lambda args: not truthy(args[0])))
    env.define("crash", BuiltinFunction("crash", _builtin_crash))
    env.define("tick", BuiltinFunction("tick", lambda args: _builtin_tick(state)))
    env.define("tickCount", BuiltinFunction("tickCount", lambda args: state["ticks"]))
    register_standard_library(env)
    return env


def _builtin_print(args: list[Value]) -> Value:
    print(*(_show_value(arg) for arg in args), end="")
    return UNIT


def _builtin_println(args: list[Value]) -> Value:
    print(*(_show_value(arg) for arg in args))
    return UNIT


def _builtin_crash(args: list[Value]) -> Value:
    raise LuneRuntimeError("crash() was evaluated")


def _builtin_tick(state: dict[str, int]) -> Value:
    state["ticks"] += 1
    return state["ticks"]


def register_standard_library(env: Env) -> None:
    env.define("Some", ConstructorValue("Some", [_param("value")]))
    env.define("None", DataValue("None", []))
    env.define("Ok", ConstructorValue("Ok", [_param("value")]))
    env.define("Err", ConstructorValue("Err", [_param("error")]))
    env.define("Cons", ConstructorValue("Cons", [_param("head"), _param("tail")]))
    env.define("Nil", DataValue("Nil", []))

    env.define("isSome", BuiltinFunction("isSome", lambda args: _is_constructor(args[0], "Some")))
    env.define("isNone", BuiltinFunction("isNone", lambda args: _is_constructor(args[0], "None")))
    env.define("getOrElse", BuiltinFunction("getOrElse", _builtin_get_or_else, force_args=False))
    env.define("optionMap", BuiltinFunction("optionMap", _builtin_option_map, force_args=False))

    env.define("isOk", BuiltinFunction("isOk", lambda args: _is_constructor(args[0], "Ok")))
    env.define("isErr", BuiltinFunction("isErr", lambda args: _is_constructor(args[0], "Err")))
    env.define("resultMap", BuiltinFunction("resultMap", _builtin_result_map, force_args=False))
    env.define("unwrapOr", BuiltinFunction("unwrapOr", _builtin_unwrap_or, force_args=False))

    env.define("isEmpty", BuiltinFunction("isEmpty", lambda args: _is_constructor(args[0], "Nil")))
    env.define("head", BuiltinFunction("head", _builtin_head))
    env.define("tail", BuiltinFunction("tail", _builtin_tail))
    env.define("length", BuiltinFunction("length", _builtin_length))
    env.define("map", BuiltinFunction("map", _builtin_map, force_args=False))
    env.define("filter", BuiltinFunction("filter", _builtin_filter, force_args=False))
    env.define("fold", BuiltinFunction("fold", _builtin_fold, force_args=False))
    env.define("take", BuiltinFunction("take", _builtin_take, force_args=False))
    env.define("drop", BuiltinFunction("drop", _builtin_drop, force_args=False))
    env.define("range", BuiltinFunction("range", _builtin_range))
    env.define("iterate", BuiltinFunction("iterate", _builtin_iterate, force_args=False))
    env.define("repeat", BuiltinFunction("repeat", _builtin_repeat, force_args=False))
    env.define("naturalsFrom", BuiltinFunction("naturalsFrom", _builtin_naturals_from))


def _param(name: str, is_strict: bool = False) -> ast.Param:
    return ast.Param(name, None, is_strict)


def _is_constructor(value: Value, name: str) -> bool:
    value = force_value(value)
    return isinstance(value, DataValue) and value.constructor == name


def _builtin_get_or_else(args: list[Value]) -> Value:
    option = force_value(args[0])
    if _is_constructor(option, "Some"):
        return force_value(option.fields[0])
    if _is_constructor(option, "None"):
        return force_value(args[1])
    raise LuneRuntimeError(f"getOrElse expects Option, got {option!r}")


def _builtin_option_map(args: list[Value]) -> Value:
    option = force_value(args[0])
    function = force_value(args[1])
    if _is_constructor(option, "None"):
        return DataValue("None", [])
    if _is_constructor(option, "Some"):
        return DataValue("Some", [LazyValue(lambda: apply_value(function, [option.fields[0]]))])
    raise LuneRuntimeError(f"optionMap expects Option, got {option!r}")


def _builtin_result_map(args: list[Value]) -> Value:
    result = force_value(args[0])
    function = force_value(args[1])
    if _is_constructor(result, "Err"):
        return DataValue("Err", [result.fields[0]])
    if _is_constructor(result, "Ok"):
        return DataValue("Ok", [LazyValue(lambda: apply_value(function, [result.fields[0]]))])
    raise LuneRuntimeError(f"resultMap expects Result, got {result!r}")


def _builtin_unwrap_or(args: list[Value]) -> Value:
    result = force_value(args[0])
    if _is_constructor(result, "Ok"):
        return force_value(result.fields[0])
    if _is_constructor(result, "Err"):
        return force_value(args[1])
    raise LuneRuntimeError(f"unwrapOr expects Result, got {result!r}")


def _builtin_head(args: list[Value]) -> Value:
    items = force_value(args[0])
    if _is_constructor(items, "Nil"):
        return DataValue("None", [])
    if _is_constructor(items, "Cons"):
        return DataValue("Some", [items.fields[0]])
    raise LuneRuntimeError(f"head expects List, got {items!r}")


def _builtin_tail(args: list[Value]) -> Value:
    items = force_value(args[0])
    if _is_constructor(items, "Nil"):
        return DataValue("None", [])
    if _is_constructor(items, "Cons"):
        return DataValue("Some", [items.fields[1]])
    raise LuneRuntimeError(f"tail expects List, got {items!r}")


def _builtin_length(args: list[Value]) -> Value:
    value = force_value(args[0])
    if isinstance(value, str):
        return len(value)
    count = 0
    while True:
        value = force_value(value)
        if _is_constructor(value, "Nil"):
            return count
        if not _is_constructor(value, "Cons"):
            raise LuneRuntimeError(f"length expects List or String, got {value!r}")
        count += 1
        value = value.fields[1]


def _builtin_map(args: list[Value]) -> Value:
    items = force_value(args[0])
    function = force_value(args[1])
    if _is_constructor(items, "Nil"):
        return DataValue("Nil", [])
    if _is_constructor(items, "Cons"):
        head = LazyValue(lambda: apply_value(function, [items.fields[0]]))
        tail = LazyValue(lambda: _builtin_map([items.fields[1], function]))
        return DataValue("Cons", [head, tail])
    raise LuneRuntimeError(f"map expects List, got {items!r}")


def _builtin_filter(args: list[Value]) -> Value:
    items = force_value(args[0])
    predicate = force_value(args[1])
    while True:
        items = force_value(items)
        if _is_constructor(items, "Nil"):
            return DataValue("Nil", [])
        if not _is_constructor(items, "Cons"):
            raise LuneRuntimeError(f"filter expects List, got {items!r}")
        head = items.fields[0]
        tail = items.fields[1]
        if truthy(apply_value(predicate, [head])):
            return DataValue("Cons", [head, LazyValue(lambda tail=tail, predicate=predicate: _builtin_filter([tail, predicate]))])
        items = tail


def _builtin_fold(args: list[Value]) -> Value:
    items = force_value(args[0])
    acc = args[1]
    function = force_value(args[2])
    while True:
        items = force_value(items)
        if _is_constructor(items, "Nil"):
            return acc
        if not _is_constructor(items, "Cons"):
            raise LuneRuntimeError(f"fold expects List, got {items!r}")
        acc = apply_value(function, [acc, items.fields[0]])
        items = items.fields[1]


def _builtin_take(args: list[Value]) -> Value:
    count = int(force_value(args[1]))
    if count <= 0:
        return DataValue("Nil", [])
    items = force_value(args[0])
    if _is_constructor(items, "Nil"):
        return DataValue("Nil", [])
    if _is_constructor(items, "Cons"):
        tail = LazyValue(lambda: _builtin_take([items.fields[1], count - 1]))
        return DataValue("Cons", [items.fields[0], tail])
    raise LuneRuntimeError(f"take expects List, got {items!r}")


def _builtin_drop(args: list[Value]) -> Value:
    items = args[0]
    count = int(force_value(args[1]))
    while count > 0:
        items = force_value(items)
        if _is_constructor(items, "Nil"):
            return DataValue("Nil", [])
        if not _is_constructor(items, "Cons"):
            raise LuneRuntimeError(f"drop expects List, got {items!r}")
        items = items.fields[1]
        count -= 1
    return items


def _builtin_range(args: list[Value]) -> Value:
    start = int(force_value(args[0]))
    end = int(force_value(args[1]))
    result: Value = DataValue("Nil", [])
    for value in reversed(range(start, end)):
        result = DataValue("Cons", [value, result])
    return result


def _builtin_iterate(args: list[Value]) -> Value:
    # iterate(f, x) = [x, f(x), f(f(x)), ...] — infinite, with a lazy tail.
    function = force_value(args[0])
    x = args[1]
    return DataValue(
        "Cons",
        [x, LazyValue(lambda: _builtin_iterate([function, LazyValue(lambda: apply_value(function, [x]))]))],
    )


def _builtin_repeat(args: list[Value]) -> Value:
    # repeat(x) = [x, x, x, ...] — infinite, with a lazy tail.
    x = args[0]
    return DataValue("Cons", [x, LazyValue(lambda: _builtin_repeat([x]))])


def _builtin_naturals_from(args: list[Value]) -> Value:
    # naturalsFrom(n) = [n, n+1, n+2, ...] — infinite, with a lazy tail.
    n = int(force_value(args[0]))
    return DataValue("Cons", [n, LazyValue(lambda: _builtin_naturals_from([n + 1]))])


def eval_decl(decl: ast.Decl, env: Env) -> Value:
    if isinstance(decl, ast.FunctionDecl):
        env.define(decl.name, FunctionValue(decl.name, decl.params, decl.body, env))
        return UNIT
    if isinstance(decl, ast.LetDecl):
        bind_let(decl, env)
        return UNIT
    if isinstance(decl, ast.VarDecl):
        env.define(decl.name, force_value(eval_expr(decl.value, env)))
        return UNIT
    if isinstance(decl, ast.TypeDecl):
        for ctor in decl.constructors:
            env.define(ctor.name, ConstructorValue(ctor.name, ctor.fields))
        return UNIT
    if isinstance(decl, ast.RecordDecl):
        env.define(decl.name, RecordConstructorValue(decl.name, decl.fields))
        return UNIT
    raise LuneRuntimeError(f"unsupported declaration: {type(decl).__name__}")


def bind_let(decl: ast.LetDecl, env: Env) -> None:
    if isinstance(decl.pattern, ast.NamePattern) and not decl.is_strict:
        env.define(decl.pattern.name, Thunk(decl.value, env))
        return
    value = force_value(eval_expr(decl.value, env)) if decl.is_strict else eval_expr(decl.value, env)
    bindings = match_pattern(decl.pattern, force_value(value))
    if bindings is None:
        raise LuneRuntimeError("let pattern did not match")
    for name, bound in bindings.items():
        env.define(name, bound)


def eval_expr(expr: ast.Expr, env: Env) -> Value:
    if isinstance(expr, ast.BlockExpr):
        return eval_block(expr, env.child())
    if isinstance(expr, ast.LiteralExpr):
        return expr.value
    if isinstance(expr, ast.NameExpr):
        return env.lookup(expr.name)
    if isinstance(expr, ast.NullExpr):
        return None
    if isinstance(expr, ast.CallExpr):
        return eval_call(expr, env)
    if isinstance(expr, ast.ListExpr):
        return eval_list_expr(expr, env)
    if isinstance(expr, ast.UnaryExpr):
        value = force_value(eval_expr(expr.expr, env))
        if expr.op == "-":
            return -value
        if expr.op == "!":
            return not truthy(value)
        raise LuneRuntimeError(f"unsupported unary operator: {expr.op}")
    if isinstance(expr, ast.BinaryExpr):
        return eval_binary(expr, env)
    if isinstance(expr, ast.IfExpr):
        return eval_if(expr, env)
    if isinstance(expr, ast.WhileExpr):
        return eval_while(expr, env)
    if isinstance(expr, ast.ForExpr):
        return eval_for(expr, env)
    if isinstance(expr, ast.MatchExpr):
        return eval_match(expr, env)
    if isinstance(expr, ast.LambdaExpr):
        return FunctionValue(None, expr.params, expr.body, env)
    if isinstance(expr, ast.LazyExpr):
        return Thunk(expr.body, env)
    if isinstance(expr, ast.ForceExpr):
        return force_value(eval_expr(expr.expr, env))
    if isinstance(expr, ast.SeqExpr):
        force_value(eval_expr(expr.first, env))
        return eval_expr(expr.second, env)
    if isinstance(expr, ast.DeepForceExpr):
        return deep_force(eval_expr(expr.expr, env))
    if isinstance(expr, ast.IOBlockExpr):
        return eval_block(expr.body, env.child())
    if isinstance(expr, ast.RaiseExpr):
        raise LuneRuntimeError(str(force_value(eval_expr(expr.expr, env))))
    if isinstance(expr, ast.MemberExpr):
        receiver = force_value(eval_expr(expr.receiver, env))
        return eval_member(receiver, expr.name)
    if isinstance(expr, ast.SafeMemberExpr):
        receiver = force_value(eval_expr(expr.receiver, env))
        return None if receiver is None else eval_member(receiver, expr.name)
    if isinstance(expr, ast.AssignExpr):
        return eval_assign(expr, env)
    raise LuneRuntimeError(f"unsupported expression: {type(expr).__name__}")


def eval_block(block: ast.BlockExpr, env: Env) -> Value:
    for item in block.statements:
        if isinstance(item, ast.Decl):
            eval_decl(item, env)
        else:
            force_value(eval_expr(item, env))
    if block.result is None:
        return UNIT
    return eval_expr(block.result, env)


def eval_call(expr: ast.CallExpr, env: Env) -> Value:
    callee = force_value(eval_expr(expr.callee, env))
    if isinstance(callee, BuiltinFunction):
        if callee.force_args:
            args = [force_value(eval_expr(arg.value, env)) for arg in expr.args]
        else:
            args = [Thunk(arg.value, env) for arg in expr.args]
        return callee.func(args)
    if isinstance(callee, ConstructorValue):
        args = prepare_constructor_args(callee, [], expr.args, env)
        return apply_constructor(callee, [], args)
    if isinstance(callee, PartialConstructorValue):
        args = prepare_constructor_args(callee.constructor, callee.bound_fields, expr.args, env)
        return apply_constructor(callee.constructor, callee.bound_fields, args)
    if isinstance(callee, RecordConstructorValue):
        return apply_record_constructor(callee, expr.args, env)
    if isinstance(callee, FunctionValue):
        if not expr.args and not callee.params:
            return apply_function(callee, [])
        return apply_function_to_ast_args(callee, expr.args, env)
    raise LuneRuntimeError(f"value is not callable: {callee!r}")


def eval_list_expr(expr: ast.ListExpr, env: Env) -> Value:
    result: Value = DataValue("Nil", [])
    for item in reversed(expr.items):
        result = DataValue("Cons", [Thunk(item, env), result])
    return result


def apply_record_constructor(constructor: RecordConstructorValue, args: list[ast.Argument], env: Env) -> Value:
    by_name = {field.name: field for field in constructor.fields}
    values: dict[str, Value] = {}
    for arg in args:
        if arg.name is None:
            raise LuneRuntimeError(f"{constructor.name} requires named record fields")
        field = by_name.get(arg.name)
        if field is None:
            raise LuneRuntimeError(f"unexpected record field for {constructor.name}: {arg.name}")
        if arg.name in values:
            raise LuneRuntimeError(f"duplicate record initializer field: {arg.name}")
        if field.is_strict:
            values[arg.name] = force_value(eval_expr(arg.value, env))
        else:
            values[arg.name] = Thunk(arg.value, env)
    for field in constructor.fields:
        if field.name not in values:
            raise LuneRuntimeError(f"missing record field for {constructor.name}: {field.name}")
    return RecordValue(constructor.name, [field.name for field in constructor.fields], values)


def prepare_function_args(function: FunctionValue, args: list[ast.Argument], env: Env) -> list[Value]:
    values: list[Value] = []
    for param, arg in zip(function.params, args):
        if param.is_strict:
            values.append(force_value(eval_expr(arg.value, env)))
        else:
            values.append(Thunk(arg.value, env))
    return values


def apply_function_to_ast_args(function: FunctionValue, args: list[ast.Argument], env: Env) -> Value:
    current: Value = function
    remaining = args
    while remaining:
        current = force_value(current)
        if not isinstance(current, FunctionValue):
            raise LuneRuntimeError(f"value is not callable: {current!r}")
        if not current.params:
            current = apply_function(current, [])
            continue
        batch = remaining[: len(current.params)]
        values = prepare_function_args(current, batch, env)
        current = apply_function(current, values)
        remaining = remaining[len(batch) :]
    return current


def apply_function(function: FunctionValue, args: list[Value]) -> Value:
    if len(args) > len(function.params):
        raise LuneRuntimeError(f"{function.name or '<lambda>'} expects at most {len(function.params)} arguments, got {len(args)}")
    call_env = function.env.child()
    for param, arg in zip(function.params, args):
        call_env.define(param.name, arg)
    remaining = function.params[len(args) :]
    if remaining:
        return FunctionValue(function.name, remaining, function.body, call_env)
    return eval_expr(function.body, call_env)


def prepare_constructor_args(constructor: ConstructorValue, bound_fields: list[Value], args: list[ast.Argument], env: Env) -> list[Value]:
    remaining_fields = constructor.fields[len(bound_fields) :]
    if len(args) > len(remaining_fields):
        raise LuneRuntimeError(f"{constructor.name} expects at most {len(remaining_fields)} more arguments, got {len(args)}")
    values: list[Value] = []
    for field, arg in zip(remaining_fields, args):
        if field.is_strict:
            values.append(force_value(eval_expr(arg.value, env)))
        else:
            values.append(Thunk(arg.value, env))
    return values


def apply_constructor(constructor: ConstructorValue, bound_fields: list[Value], args: list[Value]) -> Value:
    fields = [*bound_fields, *args]
    if len(fields) > constructor.arity:
        raise LuneRuntimeError(f"{constructor.name} expects at most {constructor.arity} arguments, got {len(fields)}")
    if len(fields) < constructor.arity:
        return PartialConstructorValue(constructor, fields)
    return DataValue(constructor.name, fields)


def eval_binary(expr: ast.BinaryExpr, env: Env) -> Value:
    if expr.op == "&&":
        left = force_value(eval_expr(expr.left, env))
        return eval_expr(expr.right, env) if truthy(left) else False
    if expr.op == "||":
        left = force_value(eval_expr(expr.left, env))
        return True if truthy(left) else eval_expr(expr.right, env)
    if expr.op == "??":
        left = force_value(eval_expr(expr.left, env))
        return left if left is not None else eval_expr(expr.right, env)

    left = force_value(eval_expr(expr.left, env))
    right = force_value(eval_expr(expr.right, env))
    if expr.op == "+":
        return left + right
    if expr.op == "-":
        return left - right
    if expr.op == "*":
        return left * right
    if expr.op == "/":
        return left / right
    if expr.op == "%":
        return left % right
    if expr.op == "==":
        return left == right
    if expr.op == "!=":
        return left != right
    if expr.op == "<":
        return left < right
    if expr.op == "<=":
        return left <= right
    if expr.op == ">":
        return left > right
    if expr.op == ">=":
        return left >= right
    if expr.op == "|>":
        return apply_value(right, [left])
    raise LuneRuntimeError(f"unsupported binary operator: {expr.op}")


def eval_if(expr: ast.IfExpr, env: Env) -> Value:
    if truthy(force_value(eval_expr(expr.condition, env))):
        return eval_expr(expr.then_branch, env)
    for condition, branch in expr.elif_branches:
        if truthy(force_value(eval_expr(condition, env))):
            return eval_expr(branch, env)
    if expr.else_branch is None:
        return UNIT
    return eval_expr(expr.else_branch, env)


def eval_while(expr: ast.WhileExpr, env: Env) -> Value:
    while truthy(force_value(eval_expr(expr.condition, env))):
        eval_block(expr.body, env.child())
    return UNIT


def eval_for(expr: ast.ForExpr, env: Env) -> Value:
    current = force_value(eval_expr(expr.iterable, env))
    while True:
        if isinstance(current, DataValue) and current.constructor == "Nil":
            return UNIT
        if not isinstance(current, DataValue) or current.constructor != "Cons" or len(current.fields) != 2:
            raise LuneRuntimeError(f"for iterable must be List, got {current!r}")
        bindings = match_pattern(expr.pattern, current.fields[0])
        if bindings is None:
            raise LuneRuntimeError(f"for pattern did not match: {force_value(current.fields[0])!r}")
        body_env = env.child()
        for name, bound in bindings.items():
            body_env.define(name, bound)
        eval_block(expr.body, body_env)
        current = force_value(current.fields[1])


def eval_match(expr: ast.MatchExpr, env: Env) -> Value:
    value = force_value(eval_expr(expr.scrutinee, env))
    for case in expr.cases:
        bindings = match_pattern(case.pattern, value)
        if bindings is None:
            continue
        case_env = env.child()
        for name, bound in bindings.items():
            case_env.define(name, bound)
        if case.guard is not None and not truthy(force_value(eval_expr(case.guard, case_env))):
            continue
        return eval_expr(case.body, case_env)
    raise LuneRuntimeError(f"non-exhaustive match for value: {value!r}")


def match_pattern(pattern: ast.Pattern, value: Value) -> dict[str, Value] | None:
    if isinstance(pattern, ast.WildcardPattern):
        return {}
    if isinstance(pattern, ast.NullPattern):
        return {} if force_value(value) is None else None
    if isinstance(pattern, ast.NamePattern):
        return {pattern.name: value}
    if isinstance(pattern, ast.LiteralPattern):
        return {} if force_value(value) == pattern.value else None
    if isinstance(pattern, ast.ConstructorPattern):
        value = force_value(value)
        if not isinstance(value, DataValue) or value.constructor != pattern.name:
            return None
        if len(value.fields) != len(pattern.args):
            return None
        bindings: dict[str, Value] = {}
        for subpattern, field in zip(pattern.args, value.fields, strict=True):
            sub = match_pattern(subpattern, field)
            if sub is None:
                return None
            bindings.update(sub)
        return bindings
    if isinstance(pattern, ast.TuplePattern):
        value = force_value(value)
        if not isinstance(value, TupleValue) or len(value.items) != len(pattern.items):
            return None
        bindings = {}
        for subpattern, item in zip(pattern.items, value.items, strict=True):
            sub = match_pattern(subpattern, item)
            if sub is None:
                return None
            bindings.update(sub)
        return bindings
    if isinstance(pattern, ast.OrPattern):
        for item in pattern.patterns:
            sub = match_pattern(item, value)
            if sub is not None:
                return sub
        return None
    if isinstance(pattern, ast.TypedPattern):
        return match_pattern(pattern.pattern, value)
    raise LuneRuntimeError(f"unsupported pattern: {type(pattern).__name__}")


def eval_member(receiver: Value, name: str) -> Value:
    if isinstance(receiver, RecordValue):
        if name not in receiver.fields:
            raise LuneRuntimeError(f"unknown record field: {receiver.name}.{name}")
        return force_value(receiver.fields[name])
    if isinstance(receiver, DataValue):
        raise LuneRuntimeError("data field access is not implemented yet; use match")
    if isinstance(receiver, str) and name == "length":
        return BuiltinFunction("String.length", lambda args: len(receiver))
    raise LuneRuntimeError(f"unsupported member access: {receiver!r}.{name}")


def eval_assign(expr: ast.AssignExpr, env: Env) -> Value:
    if not isinstance(expr.target, ast.NameExpr):
        raise LuneRuntimeError("only variable assignment is implemented")
    value = force_value(eval_expr(expr.value, env))
    env.set(expr.target.name, value)
    return value


def apply_value(function: Value, args: list[Value]) -> Value:
    function = force_value(function)
    if isinstance(function, BuiltinFunction):
        values = [force_value(arg) for arg in args] if function.force_args else args
        return function.func(values)
    if isinstance(function, ConstructorValue):
        values = prepare_runtime_constructor_args(function, [], args)
        return apply_constructor(function, [], values)
    if isinstance(function, PartialConstructorValue):
        values = prepare_runtime_constructor_args(function.constructor, function.bound_fields, args)
        return apply_constructor(function.constructor, function.bound_fields, values)
    if isinstance(function, FunctionValue):
        return apply_function_to_values(function, args)
    raise LuneRuntimeError(f"value is not callable: {function!r}")


def apply_function_to_values(function: FunctionValue, args: list[Value]) -> Value:
    current: Value = function
    remaining = args
    while remaining:
        current = force_value(current)
        if not isinstance(current, FunctionValue):
            raise LuneRuntimeError(f"value is not callable: {current!r}")
        if not current.params:
            current = apply_function(current, [])
            continue
        batch = remaining[: len(current.params)]
        values = prepare_runtime_function_args(current, batch)
        current = apply_function(current, values)
        remaining = remaining[len(batch) :]
    return current


def prepare_runtime_function_args(function: FunctionValue, args: list[Value]) -> list[Value]:
    return [force_value(arg) if param.is_strict else arg for param, arg in zip(function.params, args)]


def prepare_runtime_constructor_args(constructor: ConstructorValue, bound_fields: list[Value], args: list[Value]) -> list[Value]:
    remaining_fields = constructor.fields[len(bound_fields) :]
    if len(args) > len(remaining_fields):
        raise LuneRuntimeError(f"{constructor.name} expects at most {len(remaining_fields)} more arguments, got {len(args)}")
    return [force_value(arg) if field.is_strict else arg for field, arg in zip(remaining_fields, args)]


def force_value(value: Value) -> Value:
    if isinstance(value, Thunk | LazyValue):
        return value.force()
    return value


def deep_force(value: Value) -> Value:
    value = force_value(value)
    if isinstance(value, DataValue):
        for field in value.fields:
            deep_force(field)
    elif isinstance(value, RecordValue):
        for field in value.fields.values():
            deep_force(field)
    elif isinstance(value, TupleValue):
        for item in value.items:
            deep_force(item)
    return value


def truthy(value: Value) -> bool:
    return bool(force_value(value))


def format_value(value: Value) -> str:
    value = force_value(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if value == UNIT:
        return "()"
    if isinstance(value, RecordValue):
        items = ", ".join(f"{name} = {format_value(value.fields[name])}" for name in value.field_order)
        return f"{{ {items} }}" if items else "{}"
    if isinstance(value, DataValue):
        rendered_list = _try_render_list(value)
        if rendered_list is not None:
            return rendered_list
        if not value.fields:
            return value.constructor
        return f"{value.constructor}({', '.join(format_value(field) for field in value.fields)})"
    if isinstance(value, TupleValue):
        items = ", ".join(format_value(item) for item in value.items)
        if len(value.items) == 1:
            return f"({items},)"
        return f"({items})"
    return repr(value)


def _try_render_list(value: DataValue) -> str | None:
    if value.constructor == "Nil":
        return "()"
    if value.constructor != "Cons":
        return None

    items: list[str] = []
    current: Value = value
    while True:
        current = force_value(current)
        if isinstance(current, DataValue) and current.constructor == "Nil":
            return f"({' '.join(items)})"
        if not isinstance(current, DataValue) or current.constructor != "Cons" or len(current.fields) != 2:
            return None
        items.append(format_value(current.fields[0]))
        current = current.fields[1]


def _show_value(value: Value) -> str:
    return format_value(value)
