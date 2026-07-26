# Lune 構文仕様: Python + ML 案

Version: 0.1 draft  
Related: `LANGUAGE_SPEC.md`, `LEXER_PARSER_SPEC.md`, `LAZY_EVALUATION_SPEC.md`

## 1. 構文設計の方針

Lune の表面構文は Python の読みやすさと、ML 系言語の式指向・パターンマッチ・代数的データ型を組み合わせる。

設計方針:

- ブロックは Python 風のインデントで表す。
- 関数、条件分岐、match、let はすべて式として扱う。
- 型注釈は `name: Type` 形式にする。
- ジェネリクスは `List[Int]` のように角括弧で表す。
- 代数的データ型は ML 風に `type` と `|` で表す。
- 関数定義は Python に近い `def name(args): Return =` を基本形にする。
- ラムダは ML 風の `fn x -> expr` を使う。
- Java 連携は構文上も隠さず、明示的な `import java...` と通常のメンバー呼び出しで扱う。

## 2. レイアウト規則

### 2.1 インデント

Lune はインデントを構文として扱う。

```lune
def abs(x: Int): Int =
    if x < 0:
        -x
    else:
        x
```

字句解析器は Python と同様に `INDENT`、`DEDENT`、`NEWLINE` を生成する。

推奨インデントは 4 spaces。タブとスペースの混在はコンパイルエラー。

### 2.2 複数行式

括弧、角括弧、波括弧の内側では改行を自由に入れられる。

```lune
let names =
    users
        .filter(fn u -> u.active)
        .map(fn u -> u.name)
        .toList()
```

パイプラインでは行頭の演算子を許可する。

```lune
let names =
    users
    |> filter(fn u -> u.active)
    |> map(fn u -> u.name)
```

### 2.3 文と式

トップレベル、クラス本体、ブロック本体には宣言または式を書ける。

ブロックの最後の式が、そのブロックの値になる。

```lune
def scoreLabel(score: Int): String =
    let passed = score >= 80
    if passed:
        "pass"
    else:
        "fail"
```

`return` は使用できるが、主に Java 互換や早期脱出のための機能とする。

## 3. コメント

```lune
# 行コメント

###
ブロックコメント
###
```

Python との親和性を優先し、行コメントは `#` を採用する。

## 4. モジュールと import

```lune
module example.hello

import java.time.LocalDate
import java.time.format.DateTimeFormatter as Formatter
import lune.collections.{List, Map}
```

`module` はファイル先頭に 1 回だけ書ける。省略時はファイルパスからモジュール名を推論してもよい。

`import ... as ...` によって別名を定義できる。

## 5. 束縛

### 5.1 let

```lune
let x = 10
let name: String = "Ada"
```

`let` は不変束縛で、デフォルトでは遅延評価される。

### 5.2 strict let

```lune
strict let size = file.length()
```

`strict let` は束縛時に評価される。

### 5.3 var

```lune
var count = 0
count = count + 1
```

`var` は可変束縛で、常に正格評価される。複合代入 (`count += 1` など) は 14.1 節を参照。

### 5.4 let-in 式

ML 風の局所式として `let ... in ...` も許可する。

```lune
let result =
    let x = 10 in x * x
```

ただし通常の複数行ブロックでは `in` を使わない。

```lune
let result =
    let x = 10
    x * x
```

## 6. 関数

### 6.1 通常定義

```lune
def square(x: Int): Int =
    x * x
```

戻り値型は省略できる。

```lune
def square(x: Int) =
    x * x
```

### 6.2 短い関数

単一式の場合は 1 行で書ける。

```lune
def add(x: Int, y: Int): Int = x + y
```

### 6.3 遅延引数と正格引数

引数はデフォルトで遅延評価される。

```lune
def choose(cond: Bool, a: Int, b: Int): Int =
    if cond:
        a
    else:
        b
```

正格評価したい引数には `!` を付ける。

```lune
def add(!x: Int, !y: Int): Int =
    x + y
```

`!x: Int` は `strict x: Int` の短縮形である。仕様書では `!` を推奨表記とし、`strict` は明示的な長い表記として残す。

### 6.4 ラムダ

```lune
let inc = fn x -> x + 1
let add = fn x y -> x + y
let named = fn user: User -> user.name
```

複数行ラムダ:

```lune
let normalize =
    fn user ->
        let name = user.name.trim()
        user.withName(name)
```

### 6.5 部分適用

```lune
let add10 = add(10)
let names = map(fn u -> u.name, users)
```

引数が不足した関数呼び出しは関数を返す。

## 7. 型構文

### 7.1 基本型

```lune
Bool
Int
Long
Float
Double
Char
String
Unit
Any
Nothing
```

### 7.2 関数型

```lune
Int -> Int
Int -> Int -> Int
(Int, Int) -> Int
String -> IO[Unit]
```

`->` は右結合である。

```lune
Int -> Int -> Int
# Int -> (Int -> Int)
```

`(Int, Int) -> Int` は `Int -> Int -> Int` の糖衣である。タプルを 1 つ受け取る関数は `Tuple[Int, Int] -> Int` と書く。

### 7.3 ジェネリクス

```lune
List[Int]
Map[String, User]
Result[User, Error]
```

### 7.4 null 許容型

```lune
String?
User?
```

通常の参照型は null 非許容である。

### 7.5 タプル型

```lune
(Int, String)
(String, Int, Bool)
```

単一要素タプルは存在しない。

## 8. 制御式

### 8.1 if

```lune
let label =
    if score >= 80:
        "pass"
    elif score >= 60:
        "retry"
    else:
        "fail"
```

`if` は式である。`else` がない場合の型は `Unit` を含む共通型として扱うが、値を必要とする文脈では警告する。

短い `if`:

```lune
let label = if ok then "ok" else "ng"
```

複数行では `then` を使わず、Python 風の `:` を使う。

### 8.2 match

```lune
let value =
    match option:
        | Some(x) -> x
        | None -> 0
```

複数行の case 本体:

```lune
match user:
    | Active(name) ->
        log(name)
        name
    | Suspended(reason) ->
        "suspended: " + reason
```

`match` は式であり、代数的データ型に対して網羅性チェックを行う。

### 8.3 while

```lune
while i < 10:
    print(i)
    i = i + 1
```

`while` は `Unit` を返す。純粋コードでは利用を制限し、主に `IO` や局所的な最適化で使う。

### 8.4 for

```lune
for item in items:
    IO.println(item)
```

`for` は `Unit` を返す。コレクション変換には `map`、`filter`、`fold` を推奨する。

## 9. パターン

### 9.1 基本パターン

```lune
match value:
    | 0 -> "zero"
    | 1 -> "one"
    | n -> "many"
```

### 9.2 ワイルドカード

```lune
match value:
    | Some(_) -> true
    | None -> false
```

### 9.3 コンストラクタパターン

```lune
match tree:
    | Leaf(value) -> value
    | Node(left, right) -> sum(left) + sum(right)
```

### 9.4 レコードパターン

```lune
match user:
    | User(name = "root", role = role) -> role
    | User(name = name) -> name
```

### 9.5 ガード

```lune
match x:
    | n if n < 0 -> "negative"
    | 0 -> "zero"
    | _ -> "positive"
```

### 9.6 null パターン

nullable `T?` の `null` 値にマッチする。他のパターンは非 null の内部値にマッチし、`null` を被覆した後のトップレベル名束縛は非 null `T` にナローイングされる。

```lune
match value:
    | null -> 0
    | v -> v
```

## 10. 代数的データ型

ML 風に `type` と `|` で表す。

```lune
type Option[T] =
    | Some(value: T)
    | None
```

レコード型のコンストラクタ:

```lune
type User =
    | User(name: String, age: Int)
```

再帰データ型:

```lune
type List[T] =
    | Cons(head: T, tail: List[T])
    | Nil
```

有限リストはリストリテラルでも作れる。

```lune
let numbers = [1, 2, 3]
let sameNumbers = (1 2 3)
let empty: List[Int] = []
```

`()` は `Unit` であり、空リストには `[]` を使う。

正格フィールド:

```lune
type Point =
    | Point(!x: Double, !y: Double)
```

`!field: Type` はフィールドを正格評価する。

## 11. レコード

軽量なレコードは `record` で定義する。

```lune
record User:
    name: String
    age: Int
```

生成:

```lune
let user = User(name = "Ada", age = 36)
```

更新:

```lune
let older = user{age = user.age + 1}
```

レコードフィールドはデフォルトで不変である。可変フィールドには `var` を付ける。

```lune
record Counter:
    var value: Int
```

## 12. クラスと OO

### 12.1 クラス

```lune
class User(name: String, age: Int):
    def displayName(): String =
        name
```

クラス本体もインデントブロックである。

### 12.2 フィールド

```lune
class Counter:
    private var value = 0

    def increment(): Unit =
        value = value + 1

    def get(): Int =
        value
```

### 12.3 継承

```lune
abstract class Animal:
    abstract def speak(): String

class Dog extends Animal:
    override def speak(): String =
        "woof"
```

### 12.4 インターフェース

```lune
interface Named:
    def name(): String

class Person(value: String) implements Named:
    override def name(): String =
        value
```

### 12.5 コンストラクタ

プライマリコンストラクタ:

```lune
class Point(!x: Double, !y: Double):
    def distanceFromOrigin(): Double =
        Math.sqrt(x * x + y * y)
```

セカンダリコンストラクタ:

```lune
class User(name: String, age: Int):
    init(name: String):
        this(name, 0)
```

## 13. メンバーアクセスと呼び出し

```lune
user.name
user.displayName()
list.add("hello")
```

関数呼び出しは括弧を使う。

```lune
add(1, 2)
map(fn x -> x + 1, xs)
```

メソッドチェーン:

```lune
let names =
    users
        .filter(fn u -> u.active)
        .map(fn u -> u.name)
        .toList()
```

## 14. 演算子

優先順位は高い順に以下とする。

| 優先度 | 演算子 | 結合 |
| --- | --- | --- |
| 1 | `.`, `?.`, `()`, `[]` | 左 |
| 2 | unary `!`, unary `-` | 右 |
| 3 | `*`, `/`, `//`, `%` | 左 |
| 4 | `+`, `-` | 左 |
| 5 | `::`, `++` | 右 |
| 6 | `==`, `!=`, `<`, `<=`, `>`, `>=` | 非結合 |
| 7 | `&&` | 左 |
| 8 | `||` | 左 |
| 9 | `??` | 右 |
| 10 | `|>` | 左 |
| 11 | `=`, `+=`, `-=`, `*=`, `/=`, `//=`, `%=` | 右 |

`=` は代入または束縛構文で使う。等価比較は `==`。`??` は null 合体（左辺は nullable）、`?.` はセーフナビゲーション。`/` は常に実数除算（`Int / Int` も `Double`）、`//` は床除算（`Int // Int` は `Int`）。詳細は `LANGUAGE_SPEC.md`。

`//` はコメント開始記号ではない（行コメントは `#`、ブロックコメントは `###`）。

### 14.1 複合代入

`+= -= *= /= //= %=` は複合代入演算子である。`x op= e` は `x = x op e` と同じ意味を持ち、値としては代入後の値になる。

```lune
var x = 10
x += 5      # x = x + 5 と同じ。x は 15
x *= 3 + 4  # 右辺全体が第 2 オペランドになる。x = x * 7 で 105
x //= 2     # 床除算。x = x // 2 で 52
```

- 代入対象は通常代入と同じ制約で、名前のみをサポートする。
- 結果の型は `x op e` と同じ規則で決まる。`/` は常に真の除算なので `/=` の結果は `Double` であり、`Int` の変数への `x /= 2` は型エラーになる。`Int` の変数を `Int` のまま割るには `x //= 2` を使う。
- `//=` の丸めも `//` と同じく負の無限大方向である。`var x = -7` に対する `x //= 2` は `-3` ではなく `-4` になる。
- `x /= 0`、`x //= 0`、`x %= 0` は `x / 0` / `x // 0` / `x % 0` と同じく `RUN0006`（ゼロ除算）になる。
- `+` は String 同士も受け付けるため、`s += "..."` は文字列連結になる。

## 15. 遅延評価構文

### 15.1 暗黙の遅延

```lune
def first(a: Int, b: Int): Int =
    a

first(10, crash())
```

`crash()` は必要にならなければ評価されない。

### 15.2 明示的な lazy

```lune
let later = lazy:
    expensive()

let value = force later
```

短い形式:

```lune
let later = lazy expensive()
let value = force later
```

### 15.3 正格化

```lune
seq x y
deepForce tree
```

`seq x y` は `x` を弱頭正規形まで評価してから `y` を返す。

`deepForce` はデータ構造全体を可能な限り評価する。

## 16. IO 構文

`IO` ブロックは副作用を束ねる。

```lune
def main(args: Array[String]): IO[Unit] =
    IO:
        let name = Console.readLine("name> ")
        Console.println("Hello, " + name)
```

`IO:` ブロックの内部では Java の副作用呼び出しを通常の式として書ける。ブロック外では副作用呼び出しは型エラーまたは警告になる。

## 17. Java 相互運用構文

### 17.1 import

```lune
import java.time.LocalDate
import java.util.ArrayList
```

### 17.2 new

```lune
let list = new ArrayList[String]()
```

### 17.3 static 呼び出し

```lune
let today = LocalDate.now()
let maxValue = java.lang.Math.max(10, 20)
```

### 17.4 checked exception

```lune
def readText(path: Path): IO[String] throws java.io.IOException =
    IO:
        Files.readString(path)
```

### 17.5 Java 公開名

```lune
@java.name("com.example.App")
class App:
    @java.static
    def main(args: Array[String]): Unit =
        run(args).unsafeRun()
```

## 18. 例外

```lune
try:
    risky()
catch e: java.io.IOException:
    recover(e)
catch e: Exception:
    raise e
finally:
    cleanup()
```

例外送出:

```lune
raise IllegalArgumentException("invalid")
```

Python 風に `raise` を採用する。Java 互換のため `throw` は別名として許可してもよい。

## 19. サンプルプログラム

### 19.1 Hello world

```lune
module hello

def main(args: Array[String]): IO[Unit] =
    IO:
        Console.println("Hello, Lune")
```

### 19.2 Option

```lune
type Option[T] =
    | Some(value: T)
    | None

def getOrElse[T](option: Option[T], defaultValue: T): T =
    match option:
        | Some(value) -> value
        | None -> defaultValue
```

### 19.3 無限リスト

```lune
type Stream[T] =
    | Cons(head: T, tail: Lazy[Stream[T]])
    | Empty

def from(n: Int): Stream[Int] =
    Cons(n, lazy from(n + 1))

def take[T](!count: Int, stream: Stream[T]): List[T] =
    match (count, stream):
        | (0, _) -> Nil
        | (_, Empty) -> Nil
        | (n, Cons(head, tail)) -> Cons(head, take(n - 1, force tail))
```

### 19.4 OO と Java

```lune
module example.greeter

import java.time.LocalDate

interface Greeter:
    def greet(name: String): String

class FriendlyGreeter(prefix: String) implements Greeter:
    override def greet(name: String): String =
        prefix + ", " + name

def todayGreeting(greeter: Greeter, name: String): IO[String] =
    IO:
        let today = LocalDate.now()
        greeter.greet(name) + " today is " + today.toString()
```

## 20. 字句トークン案

```text
IDENT
INT_LITERAL
FLOAT_LITERAL
STRING_LITERAL
CHAR_LITERAL
NEWLINE
INDENT
DEDENT
EOF

module import as
let strict var def fn
type record class interface
extends implements
if elif else then
match
while for in
try catch finally raise throw
lazy force seq deepForce
IO
public private protected internal
static abstract final override
true false null
```

## 21. EBNF スケッチ

この EBNF は実装開始用の骨格であり、インデント処理は字句解析器側で `INDENT` / `DEDENT` として扱う。

lexer/parser 実装時は `LEXER_PARSER_SPEC.md` の文法を優先する。この節は構文全体を読むための要約である。

```ebnf
file          ::= moduleDecl? importDecl* topDecl* EOF
moduleDecl    ::= "module" qualifiedName NEWLINE
importDecl    ::= "import" importPath ("as" IDENT)? NEWLINE

topDecl       ::= functionDecl
                | typeDecl
                | recordDecl
                | classDecl
                | interfaceDecl
                | letDecl

functionDecl  ::= annotations? "def" IDENT typeParams? params returnType? "=" suiteOrExpr
params        ::= "(" paramList? ")"
paramList     ::= param ("," param)* ","?
param         ::= ("!" | "strict")? IDENT ":" type
returnType    ::= ":" type

letDecl       ::= "let" pattern typeAnn? "=" expr NEWLINE
varDecl       ::= "var" IDENT typeAnn? "=" expr NEWLINE
typeAnn       ::= ":" type

typeDecl      ::= "type" IDENT typeParams? "=" NEWLINE INDENT constructor+ DEDENT
constructor   ::= "|" IDENT constructorFields? NEWLINE
constructorFields ::= "(" paramList? ")"

recordDecl    ::= "record" IDENT typeParams? ":" NEWLINE INDENT fieldDecl+ DEDENT
fieldDecl     ::= "var"? IDENT ":" type NEWLINE

classDecl     ::= modifiers? "class" IDENT typeParams? params?
                  extendsClause? implementsClause? ":" NEWLINE INDENT classMember* DEDENT
interfaceDecl ::= "interface" IDENT typeParams? ":" NEWLINE INDENT interfaceMember* DEDENT

expr          ::= ifExpr
                | matchExpr
                | lambda
                | listLiteral
                | tryExpr
                | assignment

ifExpr        ::= "if" expr ":" suite ("elif" expr ":" suite)* ("else" ":" suite)?
matchExpr     ::= "match" expr ":" NEWLINE INDENT matchCase+ DEDENT
matchCase     ::= "|" pattern guard? "->" suiteOrExpr
guard         ::= "if" expr

lambda        ::= "fn" lambdaParams "->" suiteOrExpr
listLiteral   ::= "[" (expr ("," expr)* ","?)? "]"
tryExpr       ::= "try" ":" suite catchClause+ finallyClause?

suite         ::= NEWLINE INDENT block DEDENT
suiteOrExpr   ::= expr NEWLINE | suite
block         ::= (statement NEWLINE)* expr? NEWLINE?
statement     ::= letDecl | varDecl | expr
```

## 22. 採用する構文上の決定

このドラフトでは以下を採用する。

- ブロックは `{}` ではなくインデント。
- 行コメントは `#`。
- 通常関数は `def name(args): Type = body`。
- ラムダは `fn x -> expr`。
- ADT は `type Option[T] = | Some(...) | None`。
- パターンマッチは `match value:` と `| Pattern -> expr`。
- 正格引数・正格フィールドは `!name: Type`。
- 副作用は `IO:` ブロックに閉じ込める。
- Java 呼び出し構文は通常のドットアクセスと同じ。
