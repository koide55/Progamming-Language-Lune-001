from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .diagnostics import SourceSpan


@dataclass(frozen=True)
class Node:
    pass


@dataclass(frozen=True)
class ModuleFile(Node):
    module_name: str | None
    imports: list[ImportDecl]
    declarations: list[Decl]
    span: SourceSpan | None = None


@dataclass(frozen=True)
class ImportDecl(Node):
    path: str
    alias: str | None = None
    span: SourceSpan | None = None


class Decl(Node):
    pass


@dataclass(frozen=True)
class Param(Node):
    name: str
    type: TypeNode | None
    is_strict: bool = False
    span: SourceSpan | None = None


@dataclass(frozen=True)
class FunctionDecl(Decl):
    name: str
    type_params: list[str]
    params: list[Param]
    return_type: TypeNode | None
    body: Expr
    span: SourceSpan | None = None


@dataclass(frozen=True)
class LetDecl(Decl):
    pattern: Pattern
    type: TypeNode | None
    value: Expr
    is_strict: bool = False
    span: SourceSpan | None = None


@dataclass(frozen=True)
class VarDecl(Decl):
    name: str
    type: TypeNode | None
    value: Expr
    span: SourceSpan | None = None


@dataclass(frozen=True)
class TypeDecl(Decl):
    name: str
    type_params: list[str]
    constructors: list[Constructor]
    span: SourceSpan | None = None


@dataclass(frozen=True)
class RecordDecl(Decl):
    name: str
    type_params: list[str]
    fields: list[RecordField]
    span: SourceSpan | None = None


@dataclass(frozen=True)
class Constructor(Node):
    name: str
    fields: list[Param] = field(default_factory=list)
    span: SourceSpan | None = None


@dataclass(frozen=True)
class RecordField(Node):
    name: str
    type: TypeNode
    is_strict: bool = False
    span: SourceSpan | None = None


class TypeNode(Node):
    pass


@dataclass(frozen=True)
class TypeName(TypeNode):
    name: str
    span: SourceSpan | None = None


@dataclass(frozen=True)
class TypeApply(TypeNode):
    base: TypeNode
    args: list[TypeNode]
    span: SourceSpan | None = None


@dataclass(frozen=True)
class FunctionType(TypeNode):
    params: list[TypeNode]
    result: TypeNode
    span: SourceSpan | None = None


@dataclass(frozen=True)
class TupleType(TypeNode):
    items: list[TypeNode]
    span: SourceSpan | None = None


@dataclass(frozen=True)
class NullableType(TypeNode):
    inner: TypeNode
    span: SourceSpan | None = None


class Expr(Node):
    pass


@dataclass(frozen=True)
class BlockExpr(Expr):
    statements: list[Decl | Expr]
    result: Expr | None = None
    span: SourceSpan | None = None


@dataclass(frozen=True)
class LiteralExpr(Expr):
    value: Any
    span: SourceSpan | None = None


@dataclass(frozen=True)
class NameExpr(Expr):
    name: str
    span: SourceSpan | None = None


@dataclass(frozen=True)
class ThisExpr(Expr):
    span: SourceSpan | None = None


@dataclass(frozen=True)
class SuperExpr(Expr):
    span: SourceSpan | None = None


@dataclass(frozen=True)
class NullExpr(Expr):
    span: SourceSpan | None = None


@dataclass(frozen=True)
class CallExpr(Expr):
    callee: Expr
    args: list[Argument]
    span: SourceSpan | None = None


@dataclass(frozen=True)
class Argument(Node):
    value: Expr
    name: str | None = None
    span: SourceSpan | None = None


@dataclass(frozen=True)
class MemberExpr(Expr):
    receiver: Expr
    name: str
    span: SourceSpan | None = None


@dataclass(frozen=True)
class SafeMemberExpr(Expr):
    """`receiver?.name` — safe navigation; yields null when the receiver is null."""

    receiver: Expr
    name: str
    span: SourceSpan | None = None


@dataclass(frozen=True)
class IndexExpr(Expr):
    receiver: Expr
    args: list[Expr]
    span: SourceSpan | None = None


@dataclass(frozen=True)
class ListExpr(Expr):
    items: list[Expr]
    span: SourceSpan | None = None


@dataclass(frozen=True)
class UnaryExpr(Expr):
    op: str
    expr: Expr
    span: SourceSpan | None = None


@dataclass(frozen=True)
class BinaryExpr(Expr):
    op: str
    left: Expr
    right: Expr
    span: SourceSpan | None = None


@dataclass(frozen=True)
class AssignExpr(Expr):
    target: Expr
    op: str
    value: Expr
    span: SourceSpan | None = None


@dataclass(frozen=True)
class IfExpr(Expr):
    condition: Expr
    then_branch: Expr
    elif_branches: list[tuple[Expr, Expr]]
    else_branch: Expr | None
    span: SourceSpan | None = None


@dataclass(frozen=True)
class WhileExpr(Expr):
    condition: Expr
    body: BlockExpr
    span: SourceSpan | None = None


@dataclass(frozen=True)
class ForExpr(Expr):
    pattern: Pattern
    iterable: Expr
    body: BlockExpr
    span: SourceSpan | None = None


@dataclass(frozen=True)
class MatchExpr(Expr):
    scrutinee: Expr
    cases: list[MatchCase]
    span: SourceSpan | None = None


@dataclass(frozen=True)
class MatchCase(Node):
    pattern: Pattern
    guard: Expr | None
    body: Expr
    span: SourceSpan | None = None


@dataclass(frozen=True)
class LambdaExpr(Expr):
    params: list[Param]
    body: Expr
    span: SourceSpan | None = None


@dataclass(frozen=True)
class LazyExpr(Expr):
    body: Expr
    span: SourceSpan | None = None


@dataclass(frozen=True)
class ForceExpr(Expr):
    expr: Expr
    span: SourceSpan | None = None


@dataclass(frozen=True)
class SeqExpr(Expr):
    first: Expr
    second: Expr
    span: SourceSpan | None = None


@dataclass(frozen=True)
class DeepForceExpr(Expr):
    expr: Expr
    span: SourceSpan | None = None


@dataclass(frozen=True)
class NewExpr(Expr):
    type: TypeNode
    args: list[Argument]
    span: SourceSpan | None = None


@dataclass(frozen=True)
class IOBlockExpr(Expr):
    body: BlockExpr
    span: SourceSpan | None = None


@dataclass(frozen=True)
class RaiseExpr(Expr):
    expr: Expr
    span: SourceSpan | None = None


class Pattern(Node):
    pass


@dataclass(frozen=True)
class WildcardPattern(Pattern):
    span: SourceSpan | None = None


@dataclass(frozen=True)
class NullPattern(Pattern):
    span: SourceSpan | None = None


@dataclass(frozen=True)
class NamePattern(Pattern):
    name: str
    span: SourceSpan | None = None


@dataclass(frozen=True)
class LiteralPattern(Pattern):
    value: Any
    span: SourceSpan | None = None


@dataclass(frozen=True)
class TuplePattern(Pattern):
    items: list[Pattern]
    span: SourceSpan | None = None


@dataclass(frozen=True)
class ConstructorPattern(Pattern):
    name: str
    args: list[Pattern]
    span: SourceSpan | None = None


@dataclass(frozen=True)
class OrPattern(Pattern):
    patterns: list[Pattern]
    span: SourceSpan | None = None


@dataclass(frozen=True)
class TypedPattern(Pattern):
    pattern: Pattern
    type: TypeNode
    span: SourceSpan | None = None
