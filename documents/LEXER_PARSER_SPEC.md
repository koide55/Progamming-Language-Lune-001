# Lune Lexer/Parser Implementation Spec

Version: 0.1 draft  
Input syntax: `SYNTAX_SPEC.md`

この文書は、Lune の lexer/parser を実装できる粒度まで構文を落とした仕様である。表面構文の説明は `SYNTAX_SPEC.md` を参照する。

## 1. 実装方針

推奨構成:

- Lexer: 文字列からトークン列を生成する。
- Layout processor: 改行とインデントから `NEWLINE`、`INDENT`、`DEDENT` を生成する。
- Parser: トークン列から AST を生成する。
- Expression parser: Pratt parser または precedence climbing を使う。

構文エラーには、最低限、ファイル名、行、列、期待トークン、実際のトークンを含める。

## 2. 字句要素

### 2.1 文字集合

ソースコードは UTF-8 とする。

識別子は Unicode を許可してよいが、初期実装では ASCII のみでもよい。初期実装の最小規則:

```text
IDENT_START = [A-Za-z_]
IDENT_PART  = [A-Za-z0-9_]
IDENT       = IDENT_START IDENT_PART*
```

### 2.2 空白

通常の空白文字:

```text
SPACE = U+0020
TAB   = U+0009
CR    = U+000D
LF    = U+000A
```

改行は `LF` または `CRLF` を `NEWLINE` 候補として扱う。

行頭インデントには space のみを許可する。行頭に tab が現れた場合は字句エラーにする。

### 2.3 コメント

行コメント:

```lune
# comment
```

`#` から行末までを無視する。ただし文字列リテラル内の `#` はコメントではない。

ブロックコメント:

```lune
###
comment
###
```

ブロックコメントのネストは許可しない。未終端ブロックコメントは字句エラー。

### 2.4 キーワード

以下の識別子はキーワードトークンに変換する。

```text
module import as
let strict var def fn type record class interface
extends implements
if elif else then
match
while for in
try catch finally raise throw
lazy force seq deepForce
IO
public private protected internal
static abstract final override
abstract
new this super init
true false null
throws
```

`abstract` は重複してもよいが、実装上は 1 つのキーワードとして扱う。

### 2.5 リテラル

整数:

```text
INT_LITERAL = DIGIT ("_"? DIGIT)*
```

浮動小数:

```text
FLOAT_LITERAL =
    DIGIT ("_"? DIGIT)* "." DIGIT ("_"? DIGIT)* EXPONENT?
  | DIGIT ("_"? DIGIT)* EXPONENT

EXPONENT = [eE] [+-]? DIGIT ("_"? DIGIT)*
```

文字列:

```text
STRING_LITERAL = '"' string_char* '"'
```

エスケープ:

```text
\n \r \t \\ \" \0
\u{HEX+}
```

文字:

```text
CHAR_LITERAL = "'" char_char "'"
```

真偽値と null:

```text
true false null
```

これらは専用トークンとしても、キーワード + AST 変換としてもよい。

### 2.6 演算子と記号

単一文字:

```text
( ) [ ] { } , : . = | ! ? + - * / % < > @
```

`_` は単独なら `UNDERSCORE`、識別子の一部なら `IDENT` として扱う。たとえば `_` は `UNDERSCORE`、`_name` は `IDENT`。

複合記号:

```text
-> => == != <= >= && || |> :: ++ += -= *= /= %= ...
```

最長一致で字句解析する。たとえば `->` は `-` と `>` ではなく 1 トークン。

`...` は将来拡張用に予約する。初期実装では構文エラーにしてよい。

### 2.7 トークン種別

最小トークン種別:

```text
EOF
NEWLINE
INDENT
DEDENT

IDENT
INT_LITERAL
FLOAT_LITERAL
STRING_LITERAL
CHAR_LITERAL

MODULE IMPORT AS
LET STRICT VAR DEF FN TYPE RECORD CLASS INTERFACE
EXTENDS IMPLEMENTS
IF ELIF ELSE THEN
MATCH
WHILE FOR IN
TRY CATCH FINALLY RAISE THROW
LAZY FORCE SEQ DEEP_FORCE
IO_KW
PUBLIC PRIVATE PROTECTED INTERNAL
STATIC ABSTRACT FINAL OVERRIDE
NEW THIS SUPER
INIT
TRUE FALSE NULL
THROWS

LPAREN RPAREN
LBRACKET RBRACKET
LBRACE RBRACE
COMMA COLON DOT
ASSIGN
BAR
BANG
QUESTION
PLUS MINUS STAR SLASH PERCENT
LT GT
AT
UNDERSCORE

ARROW
FAT_ARROW
EQEQ
BANGEQ
LTEQ
GTEQ
ANDAND
OROR
PIPE_FORWARD
COLON_COLON
PLUS_PLUS
PLUS_ASSIGN
MINUS_ASSIGN
STAR_ASSIGN
SLASH_ASSIGN
PERCENT_ASSIGN
ELLIPSIS
```

## 3. レイアウト処理

### 3.1 入力と出力

Lexer は物理改行を `NEWLINE_RAW` として読み取る。Layout processor は以下を出力する。

```text
NEWLINE
INDENT
DEDENT
```

括弧内ではレイアウトトークンを原則生成しない。

### 3.2 括弧深度

以下のトークンで括弧深度を管理する。

- `(`, `[`, `{` で depth + 1
- `)`, `]`, `}` で depth - 1

depth > 0 のとき、物理改行は空白として扱い、`NEWLINE` を生成しない。

### 3.3 インデントスタック

初期状態:

```text
indentStack = [0]
atLineStart = true
```

行頭で space 数を数える。空行とコメントのみの行はインデント判定しない。

非空行のインデント幅 `n` について:

- `n == indentStack.top`: `NEWLINE` のみを出す。
- `n > indentStack.top`: `INDENT` を出し、`n` を push する。
- `n < indentStack.top`: `n` と一致する値が出るまで `DEDENT` を出す。一致しなければインデントエラー。

ファイル終端では、`indentStack` が `[0]` になるまで `DEDENT` を出し、最後に `EOF` を出す。

### 3.4 コロン後のブロック

`:` の直後にブロックを期待する構文では、次の有効トークンは `NEWLINE INDENT` でなければならない。

例:

```lune
if ok:
    value
```

ただし短い `if then else` は `:` を使わないため対象外。

### 3.5 `=` 後のブロック

関数定義や束縛で `=` の後にブロック式を置く場合、以下のどちらも許可する。

```lune
def f(): Int = 1
```

```lune
def f(): Int =
    1
```

2 つ目は `ASSIGN NEWLINE INDENT block DEDENT` として解析する。

## 4. AST ノード案

実装言語に依存しない名前だけを定義する。

### 4.1 ファイルと宣言

```text
ModuleFile(moduleName?, imports, declarations)
Import(path, alias?, importedNames?)

FunctionDecl(annotations, visibility?, name, typeParams, params, returnType?, body)
LetDecl(pattern, type?, value, isStrict)
VarDecl(name, type?, value)
TypeDecl(name, typeParams, constructors)
RecordDecl(name, typeParams, fields)
ClassDecl(annotations, modifiers, name, typeParams, constructorParams, extends?, implements, members)
InterfaceDecl(annotations, modifiers, name, typeParams, members)
```

### 4.2 型

```text
TypeName(path)
TypeApply(base, args)
FunctionType(params, result)
TupleType(items)
NullableType(inner)
```

### 4.3 式

```text
BlockExpr(statements, result?)
LiteralExpr(value)
NameExpr(name)
ThisExpr
SuperExpr
NullExpr

CallExpr(callee, args)
MemberExpr(receiver, name)
IndexExpr(receiver, args)
ListExpr(items)
UnaryExpr(op, expr)
BinaryExpr(op, left, right)
AssignExpr(target, op, value)

IfExpr(condition, thenBranch, elifBranches, elseBranch?)
MatchExpr(scrutinee, cases)
LambdaExpr(params, body)
TryExpr(body, catches, finallyBody?)
WhileExpr(condition, body)
ForExpr(pattern, iterable, body)
LazyExpr(body)
ForceExpr(expr)
SeqExpr(first, second)
DeepForceExpr(expr)
NewExpr(typeName, args)
IOBlockExpr(body)
RaiseExpr(expr)
```

### 4.4 パターン

```text
WildcardPattern
NamePattern(name)
LiteralPattern(value)
TuplePattern(items)
ConstructorPattern(name, args)
RecordPattern(name, fields)
OrPattern(patterns)
TypedPattern(pattern, type)
```

### 4.5 補助ノード

```text
Param(name, type?, isStrict)
Field(name, type, isVar, isStrict)
Constructor(name, fields)
MatchCase(pattern, guard?, body)
CatchClause(name, type, body)
Annotation(name, args)
```

## 5. トップレベル文法

以下では `NL` を 1 個以上の `NEWLINE` とする。

```ebnf
file
  ::= NL* module_decl? import_decl* top_decl* EOF

module_decl
  ::= MODULE qualified_name NL+

import_decl
  ::= IMPORT import_path import_alias? NL+

import_alias
  ::= AS IDENT

import_path
  ::= qualified_name import_list?

import_list
  ::= DOT LBRACE IDENT (COMMA IDENT)* COMMA? RBRACE

qualified_name
  ::= IDENT (DOT IDENT)*

top_decl
  ::= annotations? function_decl NL*
   |  annotations? type_decl NL*
   |  annotations? record_decl NL*
   |  annotations? class_decl NL*
   |  annotations? interface_decl NL*
   |  let_decl NL*
   |  var_decl NL*
```

## 6. 宣言文法

```ebnf
annotations
  ::= annotation+

annotation
  ::= AT qualified_name annotation_args? NL*

annotation_args
  ::= LPAREN argument_list? RPAREN

modifiers
  ::= modifier*

modifier
  ::= PUBLIC | PRIVATE | PROTECTED | INTERNAL | STATIC | ABSTRACT | FINAL | OVERRIDE

function_decl
  ::= modifiers DEF IDENT type_params? param_list return_type? throws_clause? ASSIGN function_body

function_body
  ::= expr
   |  NEWLINE INDENT block DEDENT

param_list
  ::= LPAREN params? RPAREN

params
  ::= param (COMMA param)* COMMA?

param
  ::= strict_marker? IDENT type_annotation?

strict_marker
  ::= BANG | STRICT

type_annotation
  ::= COLON type

return_type
  ::= COLON type

throws_clause
  ::= THROWS type (COMMA type)*

let_decl
  ::= strict_marker? LET pattern type_annotation? ASSIGN decl_body

var_decl
  ::= VAR IDENT type_annotation? ASSIGN decl_body

decl_body
  ::= expr
   |  NEWLINE INDENT block DEDENT

type_decl
  ::= TYPE IDENT type_params? ASSIGN NEWLINE INDENT constructor_decl+ DEDENT

constructor_decl
  ::= BAR IDENT constructor_fields? NL+

constructor_fields
  ::= LPAREN params? RPAREN

record_decl
  ::= RECORD IDENT type_params? COLON NEWLINE INDENT record_field+ DEDENT

record_field
  ::= strict_marker? VAR? IDENT COLON type NL+

class_decl
  ::= modifiers CLASS IDENT type_params? param_list? extends_clause? implements_clause? COLON NEWLINE INDENT class_member* DEDENT

extends_clause
  ::= EXTENDS type_name

implements_clause
  ::= IMPLEMENTS type_name (COMMA type_name)*

class_member
  ::= NL
   |  annotations? function_decl NL*
   |  annotations? init_decl NL*
   |  let_decl NL*
   |  var_decl NL*

init_decl
  ::= INIT param_list COLON NEWLINE INDENT block DEDENT

interface_decl
  ::= modifiers INTERFACE IDENT type_params? extends_interfaces? COLON NEWLINE INDENT interface_member* DEDENT

extends_interfaces
  ::= EXTENDS type_name (COMMA type_name)*

interface_member
  ::= NL
   |  annotations? modifiers DEF IDENT type_params? param_list return_type? throws_clause? NL+
```

Note: `INIT` を専用キーワードにするか、`IDENT("init")` として扱うかは実装で選べる。初期実装では `init` を予約語に追加することを推奨する。

## 7. 型文法

関数型の `->` は右結合である。

```ebnf
type
  ::= function_type

function_type
  ::= tuple_or_postfix_type (ARROW function_type)?

tuple_or_postfix_type
  ::= LPAREN type (COMMA type)+ COMMA? RPAREN nullable_suffix*
   |  postfix_type

postfix_type
  ::= primary_type type_apply* nullable_suffix*

primary_type
  ::= qualified_name
   |  LPAREN type RPAREN

type_apply
  ::= LBRACKET type (COMMA type)* COMMA? RBRACKET

nullable_suffix
  ::= QUESTION

type_params
  ::= LBRACKET IDENT (COMMA IDENT)* COMMA? RBRACKET

type_name
  ::= qualified_name type_apply*
```

例:

```text
Int -> Int -> Int        => FunctionType([Int], FunctionType([Int], Int))
(Int, String) -> Bool    => FunctionType([TupleType(Int, String)], Bool)
Map[String, List[Int]?]  => TypeApply(Map, [String, NullableType(TypeApply(List, [Int]))])
```

## 8. 文とブロック

```ebnf
block
  ::= NL* block_item* result_expr? NL*

block_item
  ::= let_decl NL+
   |  var_decl NL+
   |  expr NL+

result_expr
  ::= expr
```

ブロックの最後の式は `BlockExpr.result` になる。最後以外の式は副作用目的の式文として `BlockExpr.statements` に入る。

`let_decl` と `var_decl` は式ではなく、ブロック内宣言として扱う。`let ... in ...` は式として別に扱う。

## 9. 式パーサ

式は Pratt parser を推奨する。

### 9.1 開始規則

```ebnf
expr
  ::= if_expr
   |  short_if_expr
   |  match_expr
   |  lambda_expr
   |  try_expr
   |  while_expr
   |  for_expr
   |  io_block_expr
   |  let_in_expr
   |  precedence_expr
```

### 9.2 特殊式

```ebnf
if_expr
  ::= IF expr COLON suite elif_clause* else_clause?

elif_clause
  ::= ELIF expr COLON suite

else_clause
  ::= ELSE COLON suite

short_if_expr
  ::= IF precedence_expr THEN expr ELSE expr

match_expr
  ::= MATCH expr COLON NEWLINE INDENT match_case+ DEDENT

match_case
  ::= BAR pattern guard? ARROW case_body

guard
  ::= IF expr

case_body
  ::= expr
   |  NEWLINE INDENT block DEDENT

lambda_expr
  ::= FN lambda_params ARROW lambda_body

lambda_params
  ::= lambda_param+
   |  LPAREN params? RPAREN

lambda_param
  ::= strict_marker? IDENT type_annotation?

lambda_body
  ::= expr
   |  NEWLINE INDENT block DEDENT

try_expr
  ::= TRY COLON suite catch_clause+ finally_clause?

catch_clause
  ::= CATCH IDENT COLON type COLON suite

finally_clause
  ::= FINALLY COLON suite

while_expr
  ::= WHILE expr COLON suite

for_expr
  ::= FOR pattern IN expr COLON suite

io_block_expr
  ::= IO_KW COLON suite

let_in_expr
  ::= LET pattern type_annotation? ASSIGN expr IN expr

suite
  ::= NEWLINE INDENT block DEDENT
```

### 9.3 Pratt parser 優先順位

数値が大きいほど強く結合する。

```text
binding power:

assignment      10   right  = += -= *= /= %=
pipeline        20   left   |>
or              30   left   ||
and             40   left   &&
comparison      50   none   == != < <= > >=
cons_concat     60   right  :: ++
additive        70   left   + -
multiplicative  80   left   * / %
prefix          90   right  ! -
postfix        100   left   . () [] record_update
primary        110
```

代入演算子の左辺として許可する AST:

- `NameExpr`
- `MemberExpr`
- `IndexExpr`

比較演算子は非結合とする。`a < b < c` は構文エラーにする。将来 Python 風 chained comparison を導入する場合は別仕様にする。

### 9.4 Pratt parser の primary

```ebnf
primary
  ::= literal
   |  IDENT
   |  THIS
   |  SUPER
   |  NULL
   |  NEW type_name argument_list_parens
   |  LAZY lazy_body
   |  FORCE expr_prefix
   |  SEQ expr_prefix expr_prefix
   |  DEEP_FORCE expr_prefix
   |  RAISE expr
   |  LPAREN tuple_or_group RPAREN
   |  list_literal

literal
  ::= INT_LITERAL
   |  FLOAT_LITERAL
   |  STRING_LITERAL
   |  CHAR_LITERAL
   |  TRUE
   |  FALSE

lazy_body
  ::= expr_prefix
   |  COLON suite

tuple_or_group
  ::= expr
   |  expr COMMA expr_list? COMMA?

list_literal
  ::= LBRACKET expr_list? COMMA? RBRACKET

expr_list
  ::= expr (COMMA expr)* 
```

`expr_prefix` は prefix binding power 以上で読む式を表す実装上の補助規則である。Pratt parser では `parseExpr(90)` 相当として扱う。

例:

```text
force x.y()     => ForceExpr(CallExpr(MemberExpr(NameExpr("x"), "y"), []))
force a + b     => BinaryExpr("+", ForceExpr(NameExpr("a")), NameExpr("b"))
seq a b + c     => BinaryExpr("+", SeqExpr(NameExpr("a"), NameExpr("b")), NameExpr("c"))
```

### 9.5 Pratt parser の postfix

```ebnf
postfix
  ::= primary postfix_part*

postfix_part
  ::= DOT IDENT
   |  argument_list_parens
   |  LBRACKET argument_list? RBRACKET
   |  record_update

argument_list_parens
  ::= LPAREN argument_list? RPAREN

argument_list
  ::= argument (COMMA argument)* COMMA?

argument
  ::= IDENT ASSIGN expr
   |  expr

record_update
  ::= LBRACE record_update_field (COMMA record_update_field)* COMMA? RBRACE

record_update_field
  ::= IDENT ASSIGN expr
```

`foo {x = 1}` のような空白付き record update は初期実装では許可しない。`foo{x = 1}` または `foo .` ではなく、postfix として直接続く `{` のみを record update とする。

## 10. パターン文法

パターン内の `|` は or-pattern として使うため、match case 先頭の `|` とは文脈で区別する。

```ebnf
pattern
  ::= or_pattern

or_pattern
  ::= typed_pattern (BAR typed_pattern)*

typed_pattern
  ::= pattern_atom (COLON type)?

pattern_atom
  ::= UNDERSCORE
   |  literal
   |  IDENT
   |  constructor_pattern
   |  tuple_pattern
   |  record_pattern

constructor_pattern
  ::= qualified_name LPAREN pattern_args? RPAREN

pattern_args
  ::= pattern (COMMA pattern)* COMMA?

tuple_pattern
  ::= LPAREN pattern COMMA pattern (COMMA pattern)* COMMA? RPAREN

record_pattern
  ::= qualified_name LPAREN record_pattern_fields? RPAREN

record_pattern_fields
  ::= record_pattern_field (COMMA record_pattern_field)* COMMA?

record_pattern_field
  ::= IDENT ASSIGN pattern
```

曖昧性解消:

- `_` は `WildcardPattern`。
- 大文字で始まる `IDENT` はコンストラクタ候補、小文字で始まる `IDENT` は束縛名候補。
- `IDENT(...)` はコンストラクタまたはレコードパターンとして解析する。
- `IDENT` 単体は、名前解決段階で nullary constructor か name binding かを判定してよい。

初期実装で簡単にする場合:

- nullary constructor は `None` のような大文字始まりのみ許可。
- 変数束縛は小文字始まりまたは `_` 始まりのみ許可。

## 11. 曖昧性と採用ルール

### 11.1 `!` の扱い

宣言のパラメータ位置、フィールド位置では `!name: Type` を正格マーカーとして扱う。

式位置では `!expr` を論理否定として扱う。

### 11.2 `IO` の扱い

`IO:` のように `IO_KW COLON` が現れた場合は `IOBlockExpr`。

`IO[Unit]` のように型位置に現れた場合は通常の型名として扱う。

式位置で `IO(...)` と書かれた場合は通常の関数呼び出しとして扱う。ブロック形式の副作用構文は `IO:` のみ。

### 11.3 `if` の 2 形式

複数行形式:

```lune
if cond:
    a
else:
    b
```

短い形式:

```lune
if cond then a else b
```

`if expr COLON` が見えたら複数行形式、`if expr THEN` が見えたら短い形式として解析する。

### 11.4 `let` の 2 形式

ブロック内宣言:

```lune
let x = value
```

式:

```lune
let x = value in body
```

`let` を式位置で読んだ場合、同じ論理行に `IN` が存在すれば `LetInExpr` とする。ブロックの statement 位置では `let_decl` を優先する。

### 11.5 関数呼び出し

関数呼び出しは必ず括弧を要求する。

```lune
f(x)
```

ML 風の空白適用 `f x` は採用しない。これは Python との親和性とパーサ実装の単純さを優先するため。

ただしラムダのパラメータ列は `fn x y -> ...` を許可する。

### 11.6 オフサイドルール

`match` の case は `INDENT` 内に置く。

```lune
match x:
    | A -> 1
    | B -> 2
```

case 本体が複数行の場合、`-> NEWLINE INDENT block DEDENT` とする。

## 12. パーサ実装順序

最小実装の順序:

1. Lexer: 識別子、キーワード、数値、文字列、記号、コメント。
2. Layout processor: `NEWLINE`、`INDENT`、`DEDENT`。
3. Parser: `file`、`module`、`import`、`let`、`def`。
4. Pratt parser: リテラル、名前、呼び出し、二項演算、`if then else`。
5. ブロック式: `= NEWLINE INDENT block DEDENT`。
6. `match` とパターン。
7. `type` 宣言。
8. `record`、`class`、`interface`。
9. `IO:`、`try/catch/finally`、Java 連携構文。

## 13. 最小受け入れテスト

### 13.1 let

```lune
module sample

let x = 1 + 2 * 3
```

期待:

```text
ModuleFile(
  moduleName = sample,
  declarations = [
    LetDecl(NamePattern("x"), value = BinaryExpr("+", 1, BinaryExpr("*", 2, 3)))
  ]
)
```

### 13.2 関数とブロック

```lune
def abs(x: Int): Int =
    if x < 0:
        -x
    else:
        x
```

期待:

```text
FunctionDecl(
  name = "abs",
  params = [Param("x", Int)],
  returnType = Int,
  body = IfExpr(...)
)
```

### 13.3 ADT と match

```lune
type Option[T] =
    | Some(value: T)
    | None

def getOrElse[T](option: Option[T], defaultValue: T): T =
    match option:
        | Some(value) -> value
        | None -> defaultValue
```

期待:

```text
TypeDecl("Option", ["T"], [Constructor("Some"), Constructor("None")])
FunctionDecl("getOrElse", body = MatchExpr(...))
```

### 13.4 Java 呼び出し

```lune
import java.time.LocalDate

def today(): IO[String] =
    IO:
        LocalDate.now().toString()
```

期待:

```text
Import(java.time.LocalDate)
FunctionDecl("today", body = IOBlockExpr(BlockExpr(result = CallExpr(MemberExpr(CallExpr(MemberExpr(LocalDate, "now")), "toString")))))
```

## 14. エラー回復

初期実装のエラー回復は単純でよい。

同期トークン:

```text
NEWLINE
DEDENT
DEF
LET
VAR
TYPE
RECORD
CLASS
INTERFACE
BAR
EOF
```

宣言パース中にエラーが出た場合、次のトップレベル開始トークンまたは同じインデントの `NEWLINE` まで読み飛ばす。

match case 中のエラーでは、次の `BAR` または `DEDENT` まで読み飛ばす。

## 15. 初期実装で保留してよい構文

以下はトークンとして予約しつつ、初期 parser では構文エラーにしてよい。

- `for`
- `while`
- `try/catch/finally`
- `class`
- `interface`
- `record update`
- named arguments
- annotations
- `throws`
- `use`
- chained import list `import lune.collections.{List, Map}`

この保留により、Phase 0 の parser は `module`、`import`、`let`、`def`、`type`、式、`match` に集中できる。
