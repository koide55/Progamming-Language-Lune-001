from __future__ import annotations

from dataclasses import dataclass, field

from . import nodes as ast
from .diagnostics import Diagnostic, DiagnosticError, Label, SourceSpan
from .parser import parse_source


class LuneTypeError(DiagnosticError):
    def __init__(
        self,
        message: str,
        code: str = "TYP0003",
        span: SourceSpan | None = None,
        label: str | None = None,
        hints: list[str] | None = None,
    ):
        super().__init__(
            Diagnostic(
                code=code,
                severity="error",
                message=message,
                primary=Label(span, label) if span is not None else None,
                hints=hints or [],
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
        params = ", ".join(repr(param) for param in self.params)
        prefix = f"[{', '.join(self.type_params)}] " if self.type_params else ""
        return f"{prefix}({params}) -> {self.result!r}"


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

    def child(self) -> TypeEnv:
        return TypeEnv(self)

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
        value_type = infer_expr(decl.value, env)
        expected = type_from_ast(decl.type) if decl.type is not None else None
        if expected is not None:
            require_assignable(value_type, expected, "let annotation", getattr(decl.value, "span", None), f"this expression has type {value_type!r}")
            value_type = expected
        bind_pattern_types(decl.pattern, value_type, env)
        return
    if isinstance(decl, ast.VarDecl):
        value_type = infer_expr(decl.value, env)
        expected = type_from_ast(decl.type) if decl.type is not None else value_type
        require_assignable(value_type, expected, "var annotation")
        env.define_value(decl.name, expected)
        return
    raise LuneTypeError(f"unsupported declaration: {type(decl).__name__}")


def check_function_decl(decl: ast.FunctionDecl, env: TypeEnv) -> None:
    local = env.child()
    for param in decl.params:
        local.define_value(param.name, required_type(param.type, f"parameter {param.name}"))
    body_type = infer_expr(decl.body, local)
    if decl.return_type is None:
        env.define_value(decl.name, FunctionType(tuple(required_type(param.type, f"parameter {param.name}") for param in decl.params), body_type, tuple(decl.type_params)))
        return
    expected = type_from_ast(decl.return_type, decl.type_params)
    require_assignable(body_type, expected, f"return type of {decl.name}", getattr(decl.body, "span", None), f"function body has type {body_type!r}")


def infer_expr(expr: ast.Expr, env: TypeEnv) -> ValueType:
    if isinstance(expr, ast.BlockExpr):
        local = env.child()
        for item in expr.statements:
            if isinstance(item, ast.Decl):
                check_decl(item, local)
            else:
                infer_expr(item, local)
        return infer_expr(expr.result, local) if expr.result is not None else UNIT
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
            raise LuneTypeError(f"undefined name: {expr.name}", "TYP0001", expr.span, "name is not defined") from exc
    if isinstance(expr, ast.NullExpr):
        return NULL
    if isinstance(expr, ast.CallExpr):
        if isinstance(expr.callee, ast.NameExpr) and expr.callee.name == "__tuple__":
            return Type("Tuple", tuple(ensure_type(infer_expr(arg.value, env)) for arg in expr.args))
        callee_type = infer_expr(expr.callee, env)
        return infer_call(callee_type, expr.args, env, expr.span)
    if isinstance(expr, ast.ListExpr):
        if not expr.items:
            return Type("List", (ANY,))
        item_types = [ensure_type(infer_expr(item, env)) for item in expr.items]
        return Type("List", (common_type(item_types),))
    if isinstance(expr, ast.LambdaExpr):
        params = tuple(type_from_ast(param.type) if param.type is not None else ANY for param in expr.params)
        local = env.child()
        for param, param_type in zip(expr.params, params, strict=True):
            local.define_value(param.name, param_type)
        return FunctionType(params, ensure_type(infer_expr(expr.body, local)))
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
        then_type = ensure_type(infer_expr(expr.then_branch, env))
        branch_types = [then_type]
        for condition, branch in expr.elif_branches:
            require_assignable(ensure_type(infer_expr(condition, env)), BOOL, "elif condition")
            branch_types.append(ensure_type(infer_expr(branch, env)))
        if expr.else_branch is not None:
            branch_types.append(ensure_type(infer_expr(expr.else_branch, env)))
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
        infer_expr(expr.body, local)
        return UNIT
    if isinstance(expr, ast.MatchExpr):
        scrutinee_type = ensure_type(infer_expr(expr.scrutinee, env))
        result_types: list[Type] = []
        for case in expr.cases:
            local = env.child()
            bind_pattern_types(case.pattern, scrutinee_type, local)
            if case.guard is not None:
                require_assignable(ensure_type(infer_expr(case.guard, local)), BOOL, "match guard")
            result_types.append(ensure_type(infer_expr(case.body, local)))
        return common_type(result_types) if result_types else BOTTOM
    if isinstance(expr, ast.LazyExpr):
        return Type("Lazy", (ensure_type(infer_expr(expr.body, env)),))
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
        return infer_expr(expr.body, env)
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
        if receiver_type == ANY:
            return FunctionType((), ANY)
        if receiver_type == STRING and expr.name == "length":
            return FunctionType((), INT)
        field_type = lookup_record_field_type(receiver_type, expr.name, env, expr.span)
        if field_type is not None:
            return field_type
        raise LuneTypeError(f"unsupported member access on {receiver_type!r}: {expr.name}")
    raise LuneTypeError(f"unsupported expression: {type(expr).__name__}")


def infer_call(callee_type: ValueType, args: list[ast.Argument], env: TypeEnv, span: SourceSpan | None = None) -> ValueType:
    if isinstance(callee_type, RecordConstructorType):
        return infer_record_constructor_call(callee_type, args, env, span)
    if not isinstance(callee_type, FunctionType):
        raise LuneTypeError(f"value is not callable: {callee_type!r}", "TYP0004", span, "this value is not callable")
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
    for expected, arg in zip(callee_type.params, args):
        actual = infer_expr(arg.value, env)
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
    raise LuneTypeError(f"unknown record field: {receiver_type.name}.{field_name}", "REC0002", span, "field is not declared by this record")


def infer_binary(expr: ast.BinaryExpr, env: TypeEnv) -> Type:
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


def type_from_ast(node: ast.TypeNode | None, type_params: list[str] | tuple[str, ...] = ()) -> Type:
    if node is None:
        return ANY
    if isinstance(node, ast.TypeName):
        return Type(node.name)
    if isinstance(node, ast.TypeApply):
        base = type_from_ast(node.base, type_params)
        return Type(base.name, tuple(type_from_ast(arg, type_params) for arg in node.args))
    if isinstance(node, ast.TupleType):
        return Type("Tuple", tuple(type_from_ast(item, type_params) for item in node.items))
    if isinstance(node, ast.NullableType):
        return Type("Nullable", (type_from_ast(node.inner, type_params),))
    if isinstance(node, ast.FunctionType):
        return ANY
    raise LuneTypeError(f"unsupported type syntax: {type(node).__name__}")


def required_type(node: ast.TypeNode | None, label: str) -> Type:
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
    if expected == ANY or actual == ANY or expected == BOTTOM or actual == BOTTOM:
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
        if expected == ANY:
            return
        raise LuneTypeError(f"expected {expected!r}, got {actual!r}")
    unify(expected, actual, substitutions)


def substitute(typ: Type, substitutions: dict[str, Type]) -> Type:
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
    if actual == NULL and expected.name == "Nullable":
        return
    if actual == expected:
        return
    if expected.name == actual.name and len(expected.args) == len(actual.args):
        for actual_arg, expected_arg in zip(actual.args, expected.args, strict=True):
            require_assignable(actual_arg, expected_arg, context)
        return
    raise LuneTypeError(f"{context}: expected {expected!r}, got {actual!r}", "TYP0003", span, label)


def require_numeric(typ: Type, context: str) -> None:
    if typ not in {INT, FLOAT, BOTTOM, ANY}:
        raise LuneTypeError(f"{context}: expected numeric type, got {typ!r}")


def require_comparable(left: Type, right: Type, context: str) -> None:
    if left in {ANY, BOTTOM} or right in {ANY, BOTTOM}:
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
