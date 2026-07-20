from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from itertools import product

from . import nodes as ast
from .diagnostics import Diagnostic, DiagnosticError, Fix, Label, SourceSpan
from .parser import parse_source


def _closest(name: str, candidates) -> str | None:
    matches = difflib.get_close_matches(name, list(candidates), n=1, cutoff=0.6)
    return matches[0] if matches else None


def suggestion_hints(name: str, candidates) -> list[str]:
    """A `did you mean \\`x\\`?` hint for the closest candidate name, if any."""
    match = _closest(name, candidates)
    return [f"did you mean `{match}`?"] if match else []


def name_suggestion(name: str, candidates, span: SourceSpan | None) -> tuple[list[str], list[Fix]]:
    """A hint plus a machine-applicable fix that replaces `name` with the closest candidate."""
    match = _closest(name, candidates)
    if match is None:
        return [], []
    hints = [f"did you mean `{match}`?"]
    fixes = [Fix(span, match, f"replace with `{match}`")] if span is not None else []
    return hints, fixes


def visible_value_names(env) -> list[str]:
    """All value names in scope (walking the parent chain), minus internals."""
    names: set[str] = set()
    current = env
    while current is not None:
        names.update(key for key in current.values if not key.startswith("__"))
        current = current.parent
    return sorted(names)


class LuneTypeError(DiagnosticError):
    def __init__(
        self,
        message: str,
        code: str = "TYP0003",
        span: SourceSpan | None = None,
        label: str | None = None,
        hints: list[str] | None = None,
        fixes: list[Fix] | None = None,
    ):
        super().__init__(
            Diagnostic(
                code=code,
                severity="error",
                message=message,
                primary=Label(span, label) if span is not None else None,
                hints=hints or [],
                fixes=fixes or [],
            )
        )


@dataclass(frozen=True)
class Type:
    name: str
    args: tuple[Type, ...] = ()

    def __repr__(self) -> str:
        if not self.args:
            return self.name
        return f"{self.name}[{', '.join(repr(arg) for arg in self.args)}]"


@dataclass(frozen=True)
class FunctionType:
    params: tuple[ValueType, ...]
    result: ValueType
    type_params: tuple[str, ...] = ()
    partial: bool = True
    variadic: bool = False

    def __repr__(self) -> str:
        prefix = f"[{', '.join(self.type_params)}] " if self.type_params else ""
        return f"{prefix}{format_function_type(self)}"


@dataclass(frozen=True)
class RecordConstructorType:
    name: str
    type_params: tuple[str, ...]
    fields: tuple[RecordFieldInfo, ...]
    result: Type

    def __repr__(self) -> str:
        fields = ", ".join(f"{field.name}: {field.type!r}" for field in self.fields)
        prefix = f"[{', '.join(self.type_params)}] " if self.type_params else ""
        return f"{prefix}({fields}) -> {self.result!r}"


ValueType = Type | FunctionType | RecordConstructorType

ANY = Type("Any")
BOTTOM = Type("Nothing")
BOOL = Type("Bool")
INT = Type("Int")
FLOAT = Type("Double")
STRING = Type("String")
CHAR = Type("Char")
UNIT = Type("Unit")
NULL = Type("Null")


def format_function_type(function: FunctionType) -> str:
    if not function.params:
        return f"() -> {format_function_result(function.result)}"
    parts = [format_function_param(param) for param in function.params]
    parts.append(format_function_result(function.result))
    return " -> ".join(parts)


def format_function_param(value_type: ValueType) -> str:
    if isinstance(value_type, FunctionType):
        return f"({format_function_type(value_type)})"
    return repr(value_type)


def format_function_result(value_type: ValueType) -> str:
    return format_function_type(value_type) if isinstance(value_type, FunctionType) else repr(value_type)


@dataclass(frozen=True)
class ConstructorInfo:
    name: str
    type_params: tuple[str, ...]
    fields: tuple[Type, ...]
    result: Type


@dataclass(frozen=True)
class TypeInfo:
    name: str
    type_params: tuple[str, ...]
    constructors: tuple[str, ...]


@dataclass(frozen=True)
class RecordFieldInfo:
    name: str
    type: Type
    is_strict: bool


@dataclass(frozen=True)
class RecordInfo:
    name: str
    type_params: tuple[str, ...]
    fields: tuple[RecordFieldInfo, ...]


@dataclass
class TypeEnv:
    parent: TypeEnv | None = None
    values: dict[str, ValueType] = field(default_factory=dict)
    constructors: dict[str, ConstructorInfo] = field(default_factory=dict)
    types: dict[str, TypeInfo] = field(default_factory=dict)
    records: dict[str, RecordInfo] = field(default_factory=dict)
    warnings: list[Diagnostic] = field(default_factory=list)

    def child(self) -> TypeEnv:
        return TypeEnv(self)

    def report_warning(self, diagnostic: Diagnostic) -> None:
        if self.parent is not None:
            self.parent.report_warning(diagnostic)
        else:
            self.warnings.append(diagnostic)

    def define_value(self, name: str, typ: ValueType) -> None:
        self.values[name] = typ

    def define_constructor(self, info: ConstructorInfo) -> None:
        self.constructors[info.name] = info
        self.values[info.name] = FunctionType(info.fields, info.result, info.type_params)

    def define_type(self, info: TypeInfo) -> None:
        self.types[info.name] = info

    def define_record(self, info: RecordInfo) -> None:
        self.records[info.name] = info
        self.types[info.name] = TypeInfo(info.name, info.type_params, ())
        result = Type(info.name, tuple(Type(param) for param in info.type_params))
        self.values[info.name] = RecordConstructorType(info.name, info.type_params, info.fields, result)

    def lookup_value(self, name: str) -> ValueType:
        if name in self.values:
            return self.values[name]
        if self.parent is not None:
            return self.parent.lookup_value(name)
        raise LuneTypeError(f"undefined name: {name}")

    def lookup_constructor(self, name: str) -> ConstructorInfo:
        if name in self.constructors:
            return self.constructors[name]
        if self.parent is not None:
            return self.parent.lookup_constructor(name)
        raise LuneTypeError(f"undefined constructor: {name}")

    def lookup_record(self, name: str) -> RecordInfo:
        if name in self.records:
            return self.records[name]
        if self.parent is not None:
            return self.parent.lookup_record(name)
        raise LuneTypeError(f"undefined record type: {name}")

    def lookup_type(self, name: str) -> TypeInfo | None:
        if name in self.types:
            return self.types[name]
        if self.parent is not None:
            return self.parent.lookup_type(name)
        return None


def check_source(source: str, filename: str = "<input>") -> TypeEnv:
    return check_module(parse_source(source, filename))


def check_module(module: ast.ModuleFile) -> TypeEnv:
    env = initial_type_env()
    check_module_into(module, env)
    return env


def check_module_into(module: ast.ModuleFile, env: TypeEnv, process_imports: bool = True) -> TypeEnv:
    if process_imports:
        for import_decl in module.imports:
            imported_name = import_decl.alias or import_decl.path.rsplit(".", 1)[-1]
            env.define_value(imported_name, ANY)
    for decl in module.declarations:
        predeclare_decl(decl, env)
    for decl in module.declarations:
        check_decl(decl, env)
    return env


def initial_type_env() -> TypeEnv:
    env = TypeEnv()
    env.define_value("__tuple__", builtin_function((ANY,), ANY, variadic=True))
    env.define_value("print", builtin_function((ANY,), UNIT, variadic=True))
    env.define_value("println", builtin_function((ANY,), UNIT, variadic=True))
    env.define_value("show", builtin_function((ANY,), STRING))
    env.define_value("id", builtin_function((Type("T"),), Type("T"), ("T",)))
    env.define_value("const", builtin_function((Type("T"), Type("U")), Type("T"), ("T", "U")))
    env.define_value("not", builtin_function((BOOL,), BOOL))
    env.define_value("crash", builtin_function((), BOTTOM))
    env.define_value("tick", builtin_function((), INT))
    env.define_value("tickCount", builtin_function((), INT))
    register_standard_library_types(env)
    return env


def builtin_function(
    params: tuple[ValueType, ...],
    result: ValueType,
    type_params: tuple[str, ...] = (),
    variadic: bool = False,
) -> FunctionType:
    return FunctionType(params, result, type_params, partial=False, variadic=variadic)


def register_standard_library_types(env: TypeEnv) -> None:
    t = Type("T")
    u = Type("U")
    e = Type("E")
    option_t = Type("Option", (t,))
    result_t_e = Type("Result", (t, e))
    list_t = Type("List", (t,))
    list_u = Type("List", (u,))

    env.define_type(TypeInfo("Option", ("T",), ("Some", "None")))
    env.define_constructor(ConstructorInfo("Some", ("T",), (t,), option_t))
    env.define_constructor(ConstructorInfo("None", ("T",), (), option_t))
    env.define_value("None", option_t)

    env.define_type(TypeInfo("Result", ("T", "E"), ("Ok", "Err")))
    env.define_constructor(ConstructorInfo("Ok", ("T", "E"), (t,), result_t_e))
    env.define_constructor(ConstructorInfo("Err", ("T", "E"), (e,), result_t_e))

    env.define_type(TypeInfo("List", ("T",), ("Cons", "Nil")))
    env.define_constructor(ConstructorInfo("Cons", ("T",), (t, list_t), list_t))
    env.define_constructor(ConstructorInfo("Nil", ("T",), (), list_t))
    env.define_value("Nil", list_t)

    env.define_value("isSome", builtin_function((option_t,), BOOL, ("T",)))
    env.define_value("isNone", builtin_function((option_t,), BOOL, ("T",)))
    env.define_value("getOrElse", builtin_function((option_t, t), t, ("T",)))
    env.define_value("optionMap", builtin_function((option_t, FunctionType((t,), u)), Type("Option", (u,)), ("T", "U")))

    env.define_value("isOk", builtin_function((result_t_e,), BOOL, ("T", "E")))
    env.define_value("isErr", builtin_function((result_t_e,), BOOL, ("T", "E")))
    env.define_value("resultMap", builtin_function((result_t_e, FunctionType((t,), u)), Type("Result", (u, e)), ("T", "U", "E")))
    env.define_value("unwrapOr", builtin_function((result_t_e, t), t, ("T", "E")))

    env.define_value("isEmpty", builtin_function((list_t,), BOOL, ("T",)))
    env.define_value("head", builtin_function((list_t,), option_t, ("T",)))
    env.define_value("tail", builtin_function((list_t,), Type("Option", (list_t,)), ("T",)))
    env.define_value("length", builtin_function((ANY,), INT))
    env.define_value("map", builtin_function((list_t, FunctionType((t,), u)), list_u, ("T", "U")))
    env.define_value("filter", builtin_function((list_t, FunctionType((t,), BOOL)), list_t, ("T",)))
    env.define_value("fold", builtin_function((list_t, u, FunctionType((u, t), u)), u, ("T", "U")))
    env.define_value("take", builtin_function((list_t, INT), list_t, ("T",)))
    env.define_value("drop", builtin_function((list_t, INT), list_t, ("T",)))
    env.define_value("range", builtin_function((INT, INT), Type("List", (INT,))))
    # Infinite/lazy lists: Lune's List is lazy-tailed, so these produce streams
    # that the existing take/map/filter consume lazily.
    env.define_value("iterate", builtin_function((FunctionType((t,), t), t), list_t, ("T",)))
    env.define_value("repeat", builtin_function((t,), list_t, ("T",)))
    env.define_value("naturalsFrom", builtin_function((INT,), Type("List", (INT,))))
    env.define_value("takeWhile", builtin_function((list_t, FunctionType((t,), BOOL)), list_t, ("T",)))
    env.define_value("dropWhile", builtin_function((list_t, FunctionType((t,), BOOL)), list_t, ("T",)))
    env.define_value("zip", builtin_function((list_t, list_u), Type("List", (Type("Tuple", (t, u)),)), ("T", "U")))
    env.define_value(
        "zipWith",
        builtin_function((list_t, list_u, FunctionType((t, u), Type("V"))), Type("List", (Type("V"),)), ("T", "U", "V")),
    )
    env.define_value("cycle", builtin_function((list_t,), list_t, ("T",)))


def predeclare_decl(decl: ast.Decl, env: TypeEnv) -> None:
    if isinstance(decl, ast.TypeDecl):
        type_params = tuple(decl.type_params)
        type_info = TypeInfo(decl.name, type_params, tuple(ctor.name for ctor in decl.constructors))
        env.define_type(type_info)
        result = Type(decl.name, tuple(Type(param) for param in type_params))
        for ctor in decl.constructors:
            fields = tuple(type_from_ast(field.type, type_params) for field in ctor.fields)
            env.define_constructor(ConstructorInfo(ctor.name, type_params, fields, result))
    elif isinstance(decl, ast.RecordDecl):
        seen: set[str] = set()
        fields: list[RecordFieldInfo] = []
        for field in decl.fields:
            if field.name in seen:
                raise LuneTypeError(f"duplicate record field: {field.name}", "REC0001", field.span, "field is declared more than once")
            seen.add(field.name)
            fields.append(RecordFieldInfo(field.name, type_from_ast(field.type, decl.type_params), field.is_strict))
        env.define_record(RecordInfo(decl.name, tuple(decl.type_params), tuple(fields)))
    elif isinstance(decl, ast.FunctionDecl):
        param_types = tuple(required_type(param.type, f"parameter {param.name}") for param in decl.params)
        if decl.return_type is None:
            return
        env.define_value(decl.name, FunctionType(param_types, type_from_ast(decl.return_type, decl.type_params), tuple(decl.type_params)))


def check_decl(decl: ast.Decl, env: TypeEnv) -> None:
    if isinstance(decl, ast.TypeDecl | ast.RecordDecl):
        return
    if isinstance(decl, ast.FunctionDecl):
        check_function_decl(decl, env)
        return
    if isinstance(decl, ast.LetDecl):
        expected = type_from_ast(decl.type) if decl.type is not None else None
        value_type = infer_expr(decl.value, env, expected)
        if expected is not None:
            require_value_assignable(value_type, expected, "let annotation", getattr(decl.value, "span", None), f"this expression has type {value_type!r}")
            value_type = expected
        bind_pattern_types(decl.pattern, value_type, env)
        check_pattern_irrefutable(decl.pattern, value_type, env, "let")
        return
    if isinstance(decl, ast.VarDecl):
        annotated = type_from_ast(decl.type) if decl.type is not None else None
        value_type = infer_expr(decl.value, env, annotated)
        expected = annotated if annotated is not None else value_type
        require_value_assignable(value_type, expected, "var annotation")
        env.define_value(decl.name, expected)
        return
    raise LuneTypeError(f"unsupported declaration: {type(decl).__name__}")


def check_function_decl(decl: ast.FunctionDecl, env: TypeEnv) -> None:
    local = env.child()
    for param in decl.params:
        local.define_value(param.name, required_type(param.type, f"parameter {param.name}"))
    if decl.return_type is None:
        try:
            body_type = infer_expr(decl.body, local)
        except LuneTypeError as exc:
            if exc.diagnostic.message == f"undefined name: {decl.name}":
                raise LuneTypeError(
                    f"recursive function requires a return type annotation: {decl.name}",
                    "TYP0011",
                    decl.span,
                    "the function calls itself before its type is known",
                    [f"add a return type, e.g. `def {decl.name}(...): T = ...`"],
                ) from exc
            raise
        env.define_value(decl.name, FunctionType(tuple(required_type(param.type, f"parameter {param.name}") for param in decl.params), body_type, tuple(decl.type_params)))
        return
    expected = type_from_ast(decl.return_type, decl.type_params)
    body_type = infer_expr(decl.body, local, expected)
    require_value_assignable(body_type, expected, f"return type of {decl.name}", getattr(decl.body, "span", None), f"function body has type {body_type!r}")


def infer_expr(expr: ast.Expr, env: TypeEnv, expected: ValueType | None = None) -> ValueType:
    """Infer the type of an expression.

    When `expected` is given, it is distributed structurally into lambdas,
    list literals, tuples, branches, and blocks (LOCAL_TYPE_INFERENCE_SPEC.md
    section 5). Expression forms that do not consume the expected type ignore
    it; assignability remains the caller's responsibility.
    """
    if isinstance(expr, ast.BlockExpr):
        local = env.child()
        for item in expr.statements:
            if isinstance(item, ast.Decl):
                check_decl(item, local)
            else:
                infer_expr(item, local)
        return infer_expr(expr.result, local, expected) if expr.result is not None else UNIT
    if isinstance(expr, ast.LiteralExpr):
        value = expr.value
        if isinstance(value, bool):
            return BOOL
        if isinstance(value, int):
            return INT
        if isinstance(value, float):
            return FLOAT
        if isinstance(value, str):
            return STRING
        if value == ():
            return UNIT
        return ANY
    if isinstance(expr, ast.NameExpr):
        try:
            return env.lookup_value(expr.name)
        except LuneTypeError as exc:
            raise LuneTypeError(
                f"undefined name: {expr.name}",
                "TYP0001",
                expr.span,
                "name is not defined",
                *name_suggestion(expr.name, visible_value_names(env), expr.span),
            ) from exc
    if isinstance(expr, ast.NullExpr):
        return NULL
    if isinstance(expr, ast.CallExpr):
        if isinstance(expr.callee, ast.NameExpr) and expr.callee.name == "__tuple__":
            if isinstance(expected, Type) and expected.name == "Tuple" and len(expected.args) == len(expr.args):
                return Type(
                    "Tuple",
                    tuple(
                        ensure_type(infer_expr(arg.value, env, element))
                        for arg, element in zip(expr.args, expected.args, strict=True)
                    ),
                )
            return Type("Tuple", tuple(ensure_type(infer_expr(arg.value, env)) for arg in expr.args))
        callee_type = infer_expr(expr.callee, env)
        return infer_call(callee_type, expr.args, env, expr.span)
    if isinstance(expr, ast.ListExpr):
        if isinstance(expected, Type) and expected.name == "List" and len(expected.args) == 1:
            element = expected.args[0]
            if not expr.items:
                return expected
            item_types = [infer_expr(item, env, element) for item in expr.items]
            if contains_type_var(element):
                return Type("List", (common_type([ensure_type(item_type) for item_type in item_types]),))
            for item, item_type in zip(expr.items, item_types, strict=True):
                require_value_assignable(item_type, element, "list element", getattr(item, "span", None), f"this element has type {item_type!r}")
            return expected
        if not expr.items:
            return Type("List", (ANY,))
        item_types = [ensure_type(infer_expr(item, env)) for item in expr.items]
        return Type("List", (common_type(item_types),))
    if isinstance(expr, ast.LambdaExpr):
        if isinstance(expected, FunctionType):
            return check_lambda(expr, expected, env)
        params_list: list[ValueType] = []
        for param in expr.params:
            if param.type is not None:
                params_list.append(type_from_ast(param.type))
            else:
                params_list.append(ANY)
                env.report_warning(
                    Diagnostic(
                        code="TYP0010",
                        severity="warning",
                        message=f"cannot infer type of parameter {param.name}",
                        primary=Label(param.span, "parameter type falls back to Any") if param.span is not None else None,
                        hints=[f"add a type annotation, e.g. `fn {param.name}: Int -> ...`"],
                    )
                )
        params = tuple(params_list)
        local = env.child()
        for param, param_type in zip(expr.params, params, strict=True):
            local.define_value(param.name, param_type)
        return FunctionType(params, infer_expr(expr.body, local))
    if isinstance(expr, ast.UnaryExpr):
        value_type = ensure_type(infer_expr(expr.expr, env))
        if expr.op == "-":
            require_numeric(value_type, "unary -")
            return value_type
        if expr.op == "!":
            require_assignable(value_type, BOOL, "unary !")
            return BOOL
    if isinstance(expr, ast.BinaryExpr):
        return infer_binary(expr, env)
    if isinstance(expr, ast.IfExpr):
        require_assignable(ensure_type(infer_expr(expr.condition, env)), BOOL, "if condition")
        # Flow-narrow a nullable `x` in the branches of `if x != null` / `x == null`.
        then_env, else_env = narrow_if_branches(expr.condition, env)
        if isinstance(expected, FunctionType):
            # branches produce function values; ensure_type/common_type do not
            # apply, so each branch is checked against the expected type instead
            branch_value = infer_expr(expr.then_branch, then_env, expected)
            for condition, branch in expr.elif_branches:
                require_assignable(ensure_type(infer_expr(condition, env)), BOOL, "elif condition")
                infer_expr(branch, env, expected)
            if expr.else_branch is not None:
                infer_expr(expr.else_branch, else_env, expected)
            return branch_value
        branch_types = [ensure_type(infer_expr(expr.then_branch, then_env, expected))]
        for condition, branch in expr.elif_branches:
            require_assignable(ensure_type(infer_expr(condition, env)), BOOL, "elif condition")
            branch_types.append(ensure_type(infer_expr(branch, env, expected)))
        if expr.else_branch is not None:
            branch_types.append(ensure_type(infer_expr(expr.else_branch, else_env, expected)))
        else:
            branch_types.append(UNIT)
        return common_type(branch_types)
    if isinstance(expr, ast.WhileExpr):
        require_assignable(
            ensure_type(infer_expr(expr.condition, env)),
            BOOL,
            "while condition",
            getattr(expr.condition, "span", None),
            "condition must be Bool",
        )
        infer_expr(expr.body, env.child())
        return UNIT
    if isinstance(expr, ast.ForExpr):
        iterable_type = ensure_type(infer_expr(expr.iterable, env))
        if iterable_type == ANY:
            item_type = ANY
        elif iterable_type.name == "List" and len(iterable_type.args) == 1:
            item_type = iterable_type.args[0]
        else:
            raise LuneTypeError(
                f"for iterable must be List, got {iterable_type!r}",
                "TYP0006",
                getattr(expr.iterable, "span", None),
                "iterable must be List[T]",
            )
        local = env.child()
        bind_pattern_types(expr.pattern, item_type, local)
        check_pattern_irrefutable(expr.pattern, item_type, env, "for")
        infer_expr(expr.body, local)
        return UNIT
    if isinstance(expr, ast.MatchExpr):
        scrutinee_type = ensure_type(infer_expr(expr.scrutinee, env))
        nullable = scrutinee_type.name == "Nullable" and bool(scrutinee_type.args)
        inner_type = scrutinee_type.args[0] if nullable else scrutinee_type
        null_live = nullable
        result_types: list[Type] = []
        for case in expr.cases:
            local = env.child()
            if nullable:
                # Non-null patterns match the inner `T`; a top-level catch-all
                # binding narrows to `T` once a previous case has handled null.
                if isinstance(case.pattern, ast.NamePattern | ast.WildcardPattern):
                    arm_type = scrutinee_type if null_live else inner_type
                else:
                    arm_type = inner_type
                bind_pattern_types(case.pattern, arm_type, local)
                if case.guard is None and pattern_matches_null(case.pattern):
                    null_live = False
            else:
                bind_pattern_types(case.pattern, scrutinee_type, local)
            if case.guard is not None:
                require_assignable(ensure_type(infer_expr(case.guard, local)), BOOL, "match guard")
            result_types.append(ensure_type(infer_expr(case.body, local, expected)))
        check_match_exhaustiveness(expr, scrutinee_type, env)
        return common_type(result_types) if result_types else BOTTOM
    if isinstance(expr, ast.LazyExpr):
        body_expected = None
        if isinstance(expected, Type) and expected.name == "Lazy" and len(expected.args) == 1:
            body_expected = expected.args[0]
        return Type("Lazy", (ensure_type(infer_expr(expr.body, env, body_expected)),))
    if isinstance(expr, ast.ForceExpr):
        value_type = ensure_type(infer_expr(expr.expr, env))
        if value_type.name == "Lazy" and len(value_type.args) == 1:
            return value_type.args[0]
        return value_type
    if isinstance(expr, ast.SeqExpr):
        infer_expr(expr.first, env)
        return infer_expr(expr.second, env)
    if isinstance(expr, ast.DeepForceExpr):
        return infer_expr(expr.expr, env)
    if isinstance(expr, ast.IOBlockExpr):
        return infer_expr(expr.body, env, expected)
    if isinstance(expr, ast.RaiseExpr):
        return BOTTOM
    if isinstance(expr, ast.AssignExpr):
        if not isinstance(expr.target, ast.NameExpr):
            raise LuneTypeError("only name assignment is supported by the type checker")
        target_type = ensure_type(env.lookup_value(expr.target.name))
        value_type = ensure_type(infer_expr(expr.value, env))
        require_assignable(value_type, target_type, "assignment")
        return target_type
    if isinstance(expr, ast.MemberExpr):
        receiver_type = ensure_type(infer_expr(expr.receiver, env))
        return infer_member_type(receiver_type, expr.name, env, expr.span)
    if isinstance(expr, ast.SafeMemberExpr):
        # `receiver?.name`: the receiver must be nullable; the result is the
        # member's type made nullable (null when the receiver is null).
        receiver_type = ensure_type(infer_expr(expr.receiver, env))
        if receiver_type == ANY:
            return ANY
        if receiver_type.name != "Nullable" or not receiver_type.args:
            raise LuneTypeError(
                f"?. expects a nullable receiver, got {receiver_type!r}",
                "TYP0003",
                expr.span,
                "this expression is not nullable",
            )
        member_type = infer_member_type(receiver_type.args[0], expr.name, env, expr.span)
        if isinstance(member_type, Type):
            if member_type.name == "Nullable":
                return member_type
            return Type("Nullable", (member_type,))
        return member_type
    raise LuneTypeError(f"unsupported expression: {type(expr).__name__}")


def infer_member_type(receiver_type: Type, name: str, env: TypeEnv, span: SourceSpan | None) -> ValueType:
    if receiver_type == ANY:
        return FunctionType((), ANY)
    if receiver_type == STRING and name == "length":
        return FunctionType((), INT)
    field_type = lookup_record_field_type(receiver_type, name, env, span)
    if field_type is not None:
        return field_type
    raise LuneTypeError(f"unsupported member access on {receiver_type!r}: {name}")


def _null_check_target(condition: ast.Expr, env: TypeEnv) -> tuple[str, Type, bool] | None:
    """If `condition` is `x == null` / `x != null` on a nullable name `x`,
    return (name, inner type, narrow_then), else None. `narrow_then` is True
    when the then-branch is the non-null one (i.e. for `x != null`)."""
    if not isinstance(condition, ast.BinaryExpr) or condition.op not in {"==", "!="}:
        return None
    left, right = condition.left, condition.right
    if isinstance(left, ast.NameExpr) and isinstance(right, ast.NullExpr):
        name = left.name
    elif isinstance(right, ast.NameExpr) and isinstance(left, ast.NullExpr):
        name = right.name
    else:
        return None
    try:
        typ = env.lookup_value(name)
    except LuneTypeError:
        return None
    if not isinstance(typ, Type) or typ.name != "Nullable" or not typ.args:
        return None
    return name, typ.args[0], condition.op == "!="


def narrow_if_branches(condition: ast.Expr, env: TypeEnv) -> tuple[TypeEnv, TypeEnv]:
    """Return (then_env, else_env), narrowing a nullable name to its inner type
    in the branch where the null check guarantees it is non-null."""
    check = _null_check_target(condition, env)
    if check is None:
        return env, env
    name, inner, narrow_then = check
    narrowed = env.child()
    narrowed.define_value(name, inner)
    return (narrowed, env) if narrow_then else (env, narrowed)


def contains_type_var(typ: ValueType) -> bool:
    if isinstance(typ, FunctionType):
        return any(contains_type_var(param) for param in typ.params) or contains_type_var(typ.result)
    if isinstance(typ, RecordConstructorType):
        return bool(typ.type_params)
    if is_type_var(typ):
        return True
    return any(contains_type_var(arg) for arg in typ.args)


def check_lambda(expr: ast.LambdaExpr, expected: FunctionType, env: TypeEnv) -> FunctionType:
    """Check a lambda against an expected function type (LOCAL_TYPE_INFERENCE_SPEC.md section 5.1)."""
    expected = flatten_function_type(expected)
    if len(expr.params) > len(expected.params):
        raise LuneTypeError(
            f"lambda takes {len(expr.params)} parameters, but expected type has {len(expected.params)}",
            "TYP0005",
            expr.span,
            "too many lambda parameters",
        )
    local = env.child()
    param_types: list[ValueType] = []
    for param, expected_param in zip(expr.params, expected.params, strict=False):
        if param.type is not None:
            annotated = type_from_ast(param.type)
            if not contains_type_var(expected_param):
                require_value_assignable(
                    expected_param,
                    annotated,
                    f"parameter {param.name}",
                    param.span,
                    f"annotation {annotated!r} does not accept expected {expected_param!r}",
                )
            param_type: ValueType = annotated
        else:
            param_type = expected_param
        param_types.append(param_type)
        local.define_value(param.name, param_type)
    remaining = expected.params[len(expr.params) :]
    body_expected: ValueType = FunctionType(remaining, expected.result) if remaining else expected.result
    body_type = infer_expr(expr.body, local, body_expected)
    if not contains_type_var(body_expected):
        require_value_assignable(
            body_type,
            body_expected,
            "lambda body",
            getattr(expr.body, "span", None),
            f"lambda body has type {body_type!r}",
        )
        result: ValueType = body_expected
    else:
        result = body_type
    return FunctionType(tuple(param_types), result)


def infer_call(callee_type: ValueType, args: list[ast.Argument], env: TypeEnv, span: SourceSpan | None = None) -> ValueType:
    if isinstance(callee_type, RecordConstructorType):
        return infer_record_constructor_call(callee_type, args, env, span)
    if not isinstance(callee_type, FunctionType):
        raise LuneTypeError(f"value is not callable: {callee_type!r}", "TYP0004", span, "this value is not callable")
    callee_type = flatten_function_type(callee_type)
    if callee_type.variadic:
        substitutions: dict[str, Type] = {}
        expected = callee_type.params[-1] if callee_type.params else ANY
        for arg in args:
            actual = infer_expr(arg.value, env)
            unify_value(expected, actual, substitutions)
        return substitute_value(callee_type.result, substitutions)
    if len(args) > len(callee_type.params):
        raise LuneTypeError(f"expected at most {len(callee_type.params)} arguments, got {len(args)}", "TYP0005", span, "wrong number of arguments")
    if len(args) < len(callee_type.params) and not callee_type.partial:
        raise LuneTypeError(f"expected {len(callee_type.params)} arguments, got {len(args)}", "TYP0005", span, "wrong number of arguments")
    substitutions: dict[str, Type] = {}
    # two-pass checking (LOCAL_TYPE_INFERENCE_SPEC.md section 6): non-lambda
    # arguments resolve type variables first, then lambdas are checked against
    # the substituted parameter types.
    deferred: list[tuple[ValueType, ast.Argument]] = []
    for expected, arg in zip(callee_type.params, args):
        if isinstance(arg.value, ast.LambdaExpr):
            deferred.append((expected, arg))
            continue
        actual = infer_expr(arg.value, env)
        unify_value(expected, actual, substitutions)
    for expected, arg in deferred:
        resolved = substitute_value(expected, substitutions)
        actual = infer_expr(arg.value, env, resolved if isinstance(resolved, FunctionType) else None)
        unify_value(expected, actual, substitutions)
    params = tuple(substitute_value(param, substitutions) for param in callee_type.params)
    result = substitute_value(callee_type.result, substitutions)
    remaining = params[len(args) :]
    if remaining:
        return FunctionType(remaining, result, callee_type.type_params, partial=callee_type.partial)
    return result


def infer_record_constructor_call(
    constructor_type: RecordConstructorType,
    args: list[ast.Argument],
    env: TypeEnv,
    span: SourceSpan | None = None,
) -> Type:
    by_name = {field.name: field for field in constructor_type.fields}
    seen: set[str] = set()
    substitutions: dict[str, Type] = {}
    for arg in args:
        if arg.name is None:
            raise LuneTypeError(
                f"{constructor_type.name} requires named record fields",
                "REC0006",
                arg.span or span,
                "use field = value",
            )
        field = by_name.get(arg.name)
        if field is None:
            raise LuneTypeError(
                f"unexpected record field for {constructor_type.name}: {arg.name}",
                "REC0005",
                arg.span or span,
                "this field is not declared by the record",
                suggestion_hints(arg.name, by_name),
            )
        if arg.name in seen:
            raise LuneTypeError(
                f"duplicate record initializer field: {arg.name}",
                "REC0004",
                arg.span or span,
                "field is initialized more than once",
            )
        seen.add(arg.name)
        actual = ensure_type(infer_expr(arg.value, env))
        unify(field.type, actual, substitutions)
    missing = [field.name for field in constructor_type.fields if field.name not in seen]
    if missing:
        raise LuneTypeError(
            f"missing record field for {constructor_type.name}: {missing[0]}",
            "REC0003",
            span,
            "record construction is missing a required field",
        )
    return substitute(constructor_type.result, substitutions)


def lookup_record_field_type(receiver_type: Type, field_name: str, env: TypeEnv, span: SourceSpan | None = None) -> Type | None:
    try:
        info = env.lookup_record(receiver_type.name)
    except LuneTypeError:
        return None
    if len(info.type_params) != len(receiver_type.args):
        return None
    substitutions = {param: arg for param, arg in zip(info.type_params, receiver_type.args, strict=True)}
    for field in info.fields:
        if field.name == field_name:
            return substitute(field.type, substitutions)
    raise LuneTypeError(
        f"unknown record field: {receiver_type.name}.{field_name}",
        "REC0002",
        span,
        "field is not declared by this record",
        suggestion_hints(field_name, [field.name for field in info.fields]),
    )


def infer_binary(expr: ast.BinaryExpr, env: TypeEnv) -> ValueType:
    if expr.op == "|>":
        # `x |> f` is sugar for `f(x)` (LANGUAGE_FUTURE_SPEC.md section 4).
        # The evaluator applies the right operand to the left (evaluator.py
        # eval_binary), so we type it exactly like the equivalent call. The
        # right operand is a function value, so it must not go through
        # ensure_type (which rejects function types).
        callee_type = infer_expr(expr.right, env)
        return infer_call(callee_type, [ast.Argument(value=expr.left)], env, expr.span)
    if expr.op == "??":
        # `a ?? b`: if the nullable `a` is null, fall back to `b`. The result is
        # non-null when the fallback is non-null.
        left = ensure_type(infer_expr(expr.left, env))
        right = ensure_type(infer_expr(expr.right, env))
        if left in {ANY, BOTTOM}:
            return left
        if left.name != "Nullable" or not left.args:
            raise LuneTypeError(
                f"?? expects a nullable left operand, got {left!r}",
                "TYP0003",
                expr.span,
                "this expression is not nullable",
            )
        inner = left.args[0]
        right_nullable = right.name == "Nullable" or right == NULL
        right_inner = right.args[0] if (right.name == "Nullable" and right.args) else right
        if right != NULL:
            require_assignable(right_inner, inner, "??", expr.span)
        return Type("Nullable", (inner,)) if right_nullable else inner
    if expr.op in {"&&", "||"}:
        require_assignable(ensure_type(infer_expr(expr.left, env)), BOOL, expr.op)
        require_assignable(ensure_type(infer_expr(expr.right, env)), BOOL, expr.op)
        return BOOL
    left = ensure_type(infer_expr(expr.left, env))
    right = ensure_type(infer_expr(expr.right, env))
    if expr.op in {"+", "-", "*", "/", "%"}:
        if expr.op == "+" and left == STRING and right == STRING:
            return STRING
        require_numeric(left, expr.op)
        require_assignable(right, left, expr.op)
        if expr.op == "/":
            # runtime "/" always performs true division (evaluator.py eval_binary),
            # so the result is Double even for Int / Int.
            return FLOAT
        return left
    if expr.op in {"==", "!="}:
        require_comparable(left, right, expr.op)
        return BOOL
    if expr.op in {"<", "<=", ">", ">="}:
        require_numeric(left, expr.op)
        require_assignable(right, left, expr.op)
        return BOOL
    raise LuneTypeError(f"unsupported binary operator: {expr.op}")


def bind_pattern_types(pattern: ast.Pattern, value_type: Type, env: TypeEnv) -> None:
    if isinstance(pattern, ast.WildcardPattern):
        return
    if isinstance(pattern, ast.NullPattern):
        # `null` matches only the null value and binds nothing.
        return
    if isinstance(pattern, ast.NamePattern):
        env.define_value(pattern.name, value_type)
        return
    if isinstance(pattern, ast.LiteralPattern):
        require_assignable(literal_type(pattern.value), value_type, "literal pattern")
        return
    if isinstance(pattern, ast.ConstructorPattern):
        info = env.lookup_constructor(pattern.name)
        substitutions: dict[str, Type] = {}
        unify(info.result, value_type, substitutions)
        if len(pattern.args) != len(info.fields):
            raise LuneTypeError(f"constructor pattern {pattern.name} expects {len(info.fields)} fields, got {len(pattern.args)}")
        for subpattern, field_type in zip(pattern.args, info.fields, strict=True):
            bind_pattern_types(subpattern, substitute(field_type, substitutions), env)
        return
    if isinstance(pattern, ast.TuplePattern):
        if value_type.name != "Tuple" or len(value_type.args) != len(pattern.items):
            raise LuneTypeError(f"tuple pattern cannot match {value_type!r}")
        for subpattern, item_type in zip(pattern.items, value_type.args, strict=True):
            bind_pattern_types(subpattern, item_type, env)
        return
    if isinstance(pattern, ast.OrPattern):
        for item in pattern.patterns:
            bind_pattern_types(item, value_type, env.child())
        return
    if isinstance(pattern, ast.TypedPattern):
        expected = type_from_ast(pattern.type)
        require_assignable(value_type, expected, "typed pattern")
        bind_pattern_types(pattern.pattern, expected, env)
        return
    raise LuneTypeError(f"unsupported pattern: {type(pattern).__name__}")


# --- match exhaustiveness (TYP0007), see documents/MATCH_EXHAUSTIVENESS_SPEC.md ---


@dataclass(frozen=True)
class PatternHead:
    kind: str  # "ctor" | "lit" | "tuple"
    key: object
    arity: int


@dataclass(frozen=True)
class NormalPattern:
    head: PatternHead | None  # None means wildcard
    args: tuple[NormalPattern, ...] = ()


WILDCARD_PATTERN = NormalPattern(None)

# The `null` value is modelled as a distinguished nullary head. Exhaustiveness
# for `T?` is checked by splitting the match into "does it cover null?" and
# "does it cover the inner T?" (see check_match_exhaustiveness).
NULL_HEAD = PatternHead("lit", ("null", None), 0)


def normalize_pattern(pattern: ast.Pattern) -> list[NormalPattern]:
    """Reduce a pattern to wildcard/constructor form, expanding OR patterns."""
    if isinstance(pattern, ast.WildcardPattern | ast.NamePattern):
        return [WILDCARD_PATTERN]
    if isinstance(pattern, ast.NullPattern):
        return [NormalPattern(NULL_HEAD)]
    if isinstance(pattern, ast.TypedPattern):
        return normalize_pattern(pattern.pattern)
    if isinstance(pattern, ast.OrPattern):
        expanded: list[NormalPattern] = []
        for item in pattern.patterns:
            expanded.extend(normalize_pattern(item))
        return expanded
    if isinstance(pattern, ast.LiteralPattern):
        key = (type(pattern.value).__name__, pattern.value)
        return [NormalPattern(PatternHead("lit", key, 0))]
    if isinstance(pattern, ast.ConstructorPattern):
        head = PatternHead("ctor", pattern.name, len(pattern.args))
        return [NormalPattern(head, args) for args in _normalize_product(pattern.args)]
    if isinstance(pattern, ast.TuplePattern):
        head = PatternHead("tuple", len(pattern.items), len(pattern.items))
        return [NormalPattern(head, args) for args in _normalize_product(pattern.items)]
    return [WILDCARD_PATTERN]


def _normalize_product(patterns: list[ast.Pattern]) -> list[tuple[NormalPattern, ...]]:
    normalized = [normalize_pattern(item) for item in patterns]
    return [tuple(combo) for combo in product(*normalized)]


def _type_signature(typ: Type, env: TypeEnv) -> list[tuple[PatternHead, tuple[Type, ...], str]] | None:
    """Complete constructor signature of a type as (head, field types, display) triples.

    Returns None for open types, which only a wildcard can exhaust.
    """
    if typ in {ANY, BOTTOM} or is_type_var(typ):
        return None
    if typ == BOOL:
        return [
            (PatternHead("lit", ("bool", True), 0), (), "true"),
            (PatternHead("lit", ("bool", False), 0), (), "false"),
        ]
    if typ.name == "Tuple" and typ.args:
        head = PatternHead("tuple", len(typ.args), len(typ.args))
        return [(head, typ.args, "")]
    info = env.lookup_type(typ.name)
    if info is None or not info.constructors:
        return None
    signature: list[tuple[PatternHead, tuple[Type, ...], str]] = []
    for ctor_name in info.constructors:
        try:
            ctor = env.lookup_constructor(ctor_name)
        except LuneTypeError:
            return None
        substitutions: dict[str, Type] = {}
        try:
            unify(ctor.result, typ, substitutions)
            fields = tuple(substitute(field_type, substitutions) for field_type in ctor.fields)
        except LuneTypeError:
            fields = tuple(ANY for _ in ctor.fields)
        signature.append((PatternHead("ctor", ctor_name, len(ctor.fields)), fields, ctor_name))
    return signature


def _specialize(rows: list[list[NormalPattern]], head: PatternHead) -> list[list[NormalPattern]]:
    specialized: list[list[NormalPattern]] = []
    for row in rows:
        first = row[0]
        if first.head is None:
            specialized.append([WILDCARD_PATTERN] * head.arity + row[1:])
        elif first.head == head:
            specialized.append(list(first.args) + row[1:])
    return specialized


def _render_head(head: PatternHead, display: str, args: list[str]) -> str:
    if head.kind == "tuple":
        return "(" + ", ".join(args) + ")"
    if head.kind == "lit" or head.arity == 0:
        return display
    return f"{display}({', '.join(args)})"


def find_missing_pattern(rows: list[list[NormalPattern]], column_types: list[Type], env: TypeEnv) -> list[str] | None:
    """Return a witness (one rendered pattern per column) not covered by rows, or None."""
    if not column_types:
        return None if rows else []
    column_type = column_types[0]
    rest_types = column_types[1:]
    signature = _type_signature(column_type, env)
    present = {row[0].head for row in rows if row[0].head is not None}
    if signature is not None and all(head in present for head, _fields, _display in signature):
        for head, field_types, display in signature:
            witness = find_missing_pattern(_specialize(rows, head), list(field_types) + rest_types, env)
            if witness is not None:
                rendered = _render_head(head, display, witness[: head.arity])
                return [rendered] + witness[head.arity :]
        return None
    default_rows = [row[1:] for row in rows if row[0].head is None]
    witness = find_missing_pattern(default_rows, rest_types, env)
    if witness is None:
        return None
    if signature is not None:
        for head, _field_types, display in signature:
            if head not in present:
                return [_render_head(head, display, ["_"] * head.arity)] + witness
    return ["_"] + witness


def _head_field_types(head: PatternHead, column_type: Type, env: TypeEnv) -> list[Type]:
    if head.kind == "lit":
        return []
    if head.kind == "tuple":
        if column_type.name == "Tuple" and len(column_type.args) == head.arity:
            return list(column_type.args)
        return [ANY] * head.arity
    try:
        ctor = env.lookup_constructor(str(head.key))
    except LuneTypeError:
        return [ANY] * head.arity
    substitutions: dict[str, Type] = {}
    try:
        unify(ctor.result, column_type, substitutions)
        return [substitute(field_type, substitutions) for field_type in ctor.fields]
    except LuneTypeError:
        return [ANY] * head.arity


def is_useful(rows: list[list[NormalPattern]], q: list[NormalPattern], column_types: list[Type], env: TypeEnv) -> bool:
    """Maranget usefulness: does q match some value that rows do not cover?"""
    if not column_types:
        return not rows
    first = q[0]
    column_type = column_types[0]
    rest_types = column_types[1:]
    if first.head is not None:
        field_types = _head_field_types(first.head, column_type, env)
        return is_useful(_specialize(rows, first.head), list(first.args) + q[1:], field_types + rest_types, env)
    signature = _type_signature(column_type, env)
    present = {row[0].head for row in rows if row[0].head is not None}
    if signature is not None and all(head in present for head, _fields, _display in signature):
        for head, field_types, _display in signature:
            padded = [WILDCARD_PATTERN] * head.arity + q[1:]
            if is_useful(_specialize(rows, head), padded, list(field_types) + rest_types, env):
                return True
        return False
    default_rows = [row[1:] for row in rows if row[0].head is None]
    return is_useful(default_rows, q[1:], rest_types, env)


def pattern_matches_null(pattern: ast.Pattern) -> bool:
    """True if the pattern can match the null value (a null head or a wildcard)."""
    return any(row.head == NULL_HEAD or row.head is None for row in normalize_pattern(pattern))


def project_nonnull_rows(pattern: ast.Pattern) -> list[list[NormalPattern]]:
    """Rows of a pattern restricted to the non-null (inner `T`) values of `T?`."""
    return [[row] for row in normalize_pattern(pattern) if row.head != NULL_HEAD]


def _report_unreachable(case: ast.MatchCase, env: TypeEnv) -> None:
    env.report_warning(
        Diagnostic(
            code="TYP0009",
            severity="warning",
            message=f"unreachable match case: {render_pattern(case.pattern)}",
            primary=Label(case.span, "this case can never match") if case.span is not None else None,
            hints=["remove this case, or move it before the cases that cover it"],
        )
    )


def _report_non_exhaustive(expr: ast.MatchExpr, missing: str) -> None:
    hints = [f"add a case for {missing}, or a wildcard case `| _ -> ...`"]
    if any(case.guard is not None for case in expr.cases):
        hints.append("guarded cases do not count toward exhaustiveness")
    raise LuneTypeError(
        f"non-exhaustive match: missing case {missing}",
        "TYP0007",
        expr.span,
        f"pattern {missing} is not covered",
        hints,
    )


def check_match_exhaustiveness(expr: ast.MatchExpr, scrutinee_type: Type, env: TypeEnv) -> None:
    if scrutinee_type in {ANY, BOTTOM} or is_type_var(scrutinee_type):
        return
    if scrutinee_type.name == "Nullable" and scrutinee_type.args:
        check_nullable_match_exhaustiveness(expr, scrutinee_type, env)
        return
    rows: list[list[NormalPattern]] = []
    for case in expr.cases:
        case_rows = [[normalized] for normalized in normalize_pattern(case.pattern)]
        if rows and not any(is_useful(rows, case_row, [scrutinee_type], env) for case_row in case_rows):
            _report_unreachable(case, env)
        if case.guard is None:
            rows.extend(case_rows)
    witness = find_missing_pattern(rows, [scrutinee_type], env)
    if witness is not None:
        _report_non_exhaustive(expr, witness[0])


def check_nullable_match_exhaustiveness(expr: ast.MatchExpr, scrutinee_type: Type, env: TypeEnv) -> None:
    """Exhaustiveness for `T?`: null must be covered, and so must the inner `T`.

    The match is split because non-null patterns are written un-wrapped (`0`,
    `v`) rather than through a constructor, so they are checked against the
    inner type `T` while `null` is tracked separately.
    """
    inner_type = scrutinee_type.args[0]
    null_covered = False
    inner_rows: list[list[NormalPattern]] = []
    for case in expr.cases:
        matches_null = pattern_matches_null(case.pattern)
        nonnull_rows = project_nonnull_rows(case.pattern)
        useful_null = matches_null and not null_covered
        useful_inner = any(is_useful(inner_rows, row, [inner_type], env) for row in nonnull_rows)
        if (null_covered or inner_rows) and not useful_null and not useful_inner:
            _report_unreachable(case, env)
        if case.guard is None:
            null_covered = null_covered or matches_null
            inner_rows.extend(nonnull_rows)
    if not null_covered:
        _report_non_exhaustive(expr, "null")
    witness = find_missing_pattern(inner_rows, [inner_type], env)
    if witness is not None:
        _report_non_exhaustive(expr, witness[0])


def render_pattern(pattern: ast.Pattern) -> str:
    if isinstance(pattern, ast.WildcardPattern):
        return "_"
    if isinstance(pattern, ast.NullPattern):
        return "null"
    if isinstance(pattern, ast.NamePattern):
        return pattern.name
    if isinstance(pattern, ast.LiteralPattern):
        value = pattern.value
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, str):
            return f'"{value}"'
        return repr(value)
    if isinstance(pattern, ast.TuplePattern):
        return "(" + ", ".join(render_pattern(item) for item in pattern.items) + ")"
    if isinstance(pattern, ast.ConstructorPattern):
        if not pattern.args:
            return pattern.name
        return f"{pattern.name}({', '.join(render_pattern(arg) for arg in pattern.args)})"
    if isinstance(pattern, ast.OrPattern):
        return " | ".join(render_pattern(item) for item in pattern.patterns)
    if isinstance(pattern, ast.TypedPattern):
        return render_pattern(pattern.pattern)
    return type(pattern).__name__


def check_pattern_irrefutable(pattern: ast.Pattern, value_type: ValueType, env: TypeEnv, context: str) -> None:
    """Reject refutable patterns in let/for bindings (TYP0008)."""
    if isinstance(pattern, ast.WildcardPattern | ast.NamePattern):
        return
    if not isinstance(value_type, Type):
        return
    if value_type in {ANY, BOTTOM} or is_type_var(value_type):
        return
    rows = [[normalized] for normalized in normalize_pattern(pattern)]
    witness = find_missing_pattern(rows, [value_type], env)
    if witness is None:
        return
    rendered = render_pattern(pattern)
    raise LuneTypeError(
        f"refutable pattern in {context} binding: {rendered}",
        "TYP0008",
        getattr(pattern, "span", None),
        "this pattern can fail to match",
        [
            f"the pattern does not cover {witness[0]}",
            f"use `match` to handle all cases of {value_type!r}",
        ],
    )


def type_from_ast(node: ast.TypeNode | None, type_params: list[str] | tuple[str, ...] = ()) -> ValueType:
    if node is None:
        return ANY
    if isinstance(node, ast.TypeName):
        return Type(node.name)
    if isinstance(node, ast.TypeApply):
        base = type_from_ast(node.base, type_params)
        if not isinstance(base, Type):
            raise LuneTypeError(f"unsupported generic type base: {base!r}")
        return Type(base.name, tuple(type_from_ast(arg, type_params) for arg in node.args))
    if isinstance(node, ast.TupleType):
        if not node.items:
            return UNIT
        return Type("Tuple", tuple(type_from_ast(item, type_params) for item in node.items))
    if isinstance(node, ast.NullableType):
        inner = type_from_ast(node.inner, type_params)
        if not isinstance(inner, Type):
            raise LuneTypeError(f"function type cannot be nullable in v0.1: {inner!r}")
        return Type("Nullable", (inner,))
    if isinstance(node, ast.FunctionType):
        return function_type_from_ast(node, type_params)
    raise LuneTypeError(f"unsupported type syntax: {type(node).__name__}")


def function_type_from_ast(node: ast.FunctionType, type_params: list[str] | tuple[str, ...] = ()) -> FunctionType:
    params: list[ValueType] = []
    current: ast.TypeNode = node
    while isinstance(current, ast.FunctionType):
        for param in current.params:
            params.extend(function_params_from_ast(param, type_params))
        current = current.result
    return FunctionType(tuple(params), type_from_ast(current, type_params))


def function_params_from_ast(node: ast.TypeNode, type_params: list[str] | tuple[str, ...]) -> list[ValueType]:
    if isinstance(node, ast.TupleType):
        return [type_from_ast(item, type_params) for item in node.items]
    return [type_from_ast(node, type_params)]


def required_type(node: ast.TypeNode | None, label: str) -> ValueType:
    if node is None:
        raise LuneTypeError(f"{label} requires a type annotation in v0.1")
    return type_from_ast(node)


def ensure_type(value_type: ValueType) -> Type:
    if isinstance(value_type, FunctionType | RecordConstructorType):
        raise LuneTypeError(f"expected value type, got function type {value_type!r}")
    return value_type


def literal_type(value: object) -> Type:
    if isinstance(value, bool):
        return BOOL
    if isinstance(value, int):
        return INT
    if isinstance(value, float):
        return FLOAT
    if isinstance(value, str):
        return STRING
    if value == ():
        return UNIT
    return ANY


def unify(expected: Type, actual: Type, substitutions: dict[str, Type]) -> None:
    if isinstance(expected, FunctionType) or isinstance(actual, FunctionType):
        unify_value(expected, actual, substitutions)
        return
    if expected == ANY or actual == ANY or expected == BOTTOM or actual == BOTTOM:
        return
    if expected.name == "Nullable" and expected.args:
        # `null` and a non-null `T` both satisfy `T?` (see require_assignable).
        # This is the path used by let/var annotations and call arguments.
        if actual == NULL:
            return
        source = actual.args[0] if actual.name == "Nullable" and actual.args else actual
        unify(expected.args[0], source, substitutions)
        return
    if is_type_var(expected):
        if expected == actual:
            return
        existing = substitutions.get(expected.name)
        if existing is None:
            substitutions[expected.name] = actual
            return
        require_assignable(actual, existing, f"type parameter {expected.name}")
        return
    if expected.name != actual.name or len(expected.args) != len(actual.args):
        raise LuneTypeError(f"expected {expected!r}, got {actual!r}")
    for expected_arg, actual_arg in zip(expected.args, actual.args, strict=True):
        unify(expected_arg, actual_arg, substitutions)


def unify_value(expected: ValueType, actual: ValueType, substitutions: dict[str, Type]) -> None:
    if isinstance(expected, RecordConstructorType) or isinstance(actual, RecordConstructorType):
        if expected == ANY or actual == ANY:
            return
        raise LuneTypeError(f"expected {expected!r}, got {actual!r}")
    if isinstance(expected, FunctionType):
        expected = flatten_function_type(expected)
        actual = flatten_function_type(actual) if isinstance(actual, FunctionType) else actual
        if actual == ANY:
            return
        if not isinstance(actual, FunctionType):
            raise LuneTypeError(f"expected {expected!r}, got {actual!r}")
        if len(expected.params) != len(actual.params):
            raise LuneTypeError(f"expected {len(expected.params)} function parameters, got {len(actual.params)}")
        for expected_param, actual_param in zip(expected.params, actual.params, strict=True):
            unify_value(expected_param, actual_param, substitutions)
        unify_value(expected.result, actual.result, substitutions)
        return
    if isinstance(actual, FunctionType):
        actual = flatten_function_type(actual)
        if expected == ANY:
            return
        raise LuneTypeError(f"expected {expected!r}, got {actual!r}")
    unify(expected, actual, substitutions)


def flatten_function_type(function: FunctionType) -> FunctionType:
    params = list(function.params)
    result = function.result
    while isinstance(result, FunctionType) and result.params:
        params.extend(result.params)
        result = result.result
    return FunctionType(tuple(params), result, function.type_params, function.partial, function.variadic)


def substitute(typ: Type, substitutions: dict[str, Type]) -> Type:
    if isinstance(typ, FunctionType | RecordConstructorType):
        return substitute_value(typ, substitutions)
    if typ.name in substitutions and not typ.args:
        return substitutions[typ.name]
    if not typ.args:
        return typ
    return Type(typ.name, tuple(substitute(arg, substitutions) for arg in typ.args))


def substitute_value(typ: ValueType, substitutions: dict[str, Type]) -> ValueType:
    if isinstance(typ, FunctionType):
        return FunctionType(
            tuple(substitute_value(param, substitutions) for param in typ.params),
            substitute_value(typ.result, substitutions),
            typ.type_params,
            typ.partial,
            typ.variadic,
        )
    if isinstance(typ, RecordConstructorType):
        return RecordConstructorType(
            typ.name,
            typ.type_params,
            tuple(RecordFieldInfo(field.name, substitute(field.type, substitutions), field.is_strict) for field in typ.fields),
            substitute(typ.result, substitutions),
        )
    return substitute(typ, substitutions)


def is_type_var(typ: Type) -> bool:
    return not typ.args and len(typ.name) == 1 and typ.name.isupper() and typ.name not in {"Int", "Bool", "String", "Double", "Char", "Unit", "Any", "Nothing"}


def require_assignable(
    actual: Type,
    expected: Type,
    context: str,
    span: SourceSpan | None = None,
    label: str | None = None,
) -> None:
    if expected == ANY or actual == ANY or actual == BOTTOM:
        return
    if expected.name == "Nullable" and expected.args:
        # `null` and a non-null `T` are both assignable to `T?`; `T?` is
        # covariant in its element. The reverse (`T?` where `T` is expected)
        # is intentionally rejected, so this branch only fires when the
        # *expected* type is nullable.
        if actual == NULL:
            return
        source = actual.args[0] if actual.name == "Nullable" and actual.args else actual
        require_assignable(source, expected.args[0], context, span, label)
        return
    if actual == expected:
        return
    if expected.name == actual.name and len(expected.args) == len(actual.args):
        for actual_arg, expected_arg in zip(actual.args, expected.args, strict=True):
            require_assignable(actual_arg, expected_arg, context)
        return
    raise LuneTypeError(f"{context}: expected {expected!r}, got {actual!r}", "TYP0003", span, label)


def require_value_assignable(
    actual: ValueType,
    expected: ValueType,
    context: str,
    span: SourceSpan | None = None,
    label: str | None = None,
) -> None:
    try:
        unify_value(expected, actual, {})
    except LuneTypeError as exc:
        raise LuneTypeError(f"{context}: expected {expected!r}, got {actual!r}", "TYP0003", span, label) from exc


def require_numeric(typ: Type, context: str) -> None:
    if typ not in {INT, FLOAT, BOTTOM, ANY}:
        raise LuneTypeError(f"{context}: expected numeric type, got {typ!r}")


def require_comparable(left: Type, right: Type, context: str) -> None:
    if left in {ANY, BOTTOM} or right in {ANY, BOTTOM}:
        return
    # `null` compares with anything, and a nullable `T?` compares with `T` (or
    # another `T?`) — this is how null checks like `x == null` are written.
    if left == NULL or right == NULL:
        return
    left_inner = left.args[0] if left.name == "Nullable" and left.args else left
    right_inner = right.args[0] if right.name == "Nullable" and right.args else right
    if left_inner == right_inner:
        return
    if left != right:
        raise LuneTypeError(f"{context}: cannot compare {left!r} and {right!r}")


def common_type(types: list[Type]) -> Type:
    if not types:
        return UNIT
    current = types[0]
    for typ in types[1:]:
        if current == typ:
            continue
        if current == ANY or typ == ANY:
            current = ANY
            continue
        if current == BOTTOM:
            current = typ
            continue
        if typ == BOTTOM:
            continue
        raise LuneTypeError(f"branch type mismatch: {current!r} vs {typ!r}")
    return current
