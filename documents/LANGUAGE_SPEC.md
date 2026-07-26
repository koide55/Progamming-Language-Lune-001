# Lune v0.1 現状仕様

Version: 0.1 current  
Implementation: `lune_v0_1` Python prototype  
Future target reference: `LANGUAGE_FUTURE_SPEC.md`

この文書は、現在の実装で実際に利用できる Lune v0.1 の言語仕様をまとめる。長期的な目標仕様は `LANGUAGE_FUTURE_SPEC.md` を参照する。

詳細仕様:

- 構文詳細: `SYNTAX_SPEC.md`
- lexer/parser 詳細: `LEXER_PARSER_SPEC.md`
- 遅延評価: `LAZY_EVALUATION_SPEC.md`
- 型チェッカ: `TYPE_CHECKER_SPEC.md`
- 関数型注釈: `FUNCTION_TYPE_SPEC.md`
- REPL: `REPL_SPEC.md`
- エラー表示: `ERROR_DIAGNOSTICS_SPEC.md`
- 値表示: `VALUE_DISPLAY_SPEC.md`
- 標準ライブラリ: `STANDARD_LIBRARY_SPEC.md`
- リストリテラル: `LIST_LITERAL_SPEC.md`
- モジュール読み込み: `MODULE_LOADING_SPEC.md`
- レコード / フィールドアクセス追加仕様: `RECORD_FIELD_SPEC.md`
- while ループ: `WHILE_LOOP_SPEC.md`
- for 式: `FOR_LOOP_SPEC.md`

## 1. 目的

Lune v0.1 は、Python 風の layout 構文と ML 風の関数・ADT・match を持つ小さな遅延評価言語である。

実装済みの中心機能:

- layout-aware lexer/parser。
- `let`、`var`、`def`、`fn`。
- デフォルト遅延評価、明示 `strict`、`lazy`、`force`、`seq`、`deepForce`。
- ADT とコンストラクタ。
- `match` とパターン束縛。
- レコードとフィールドアクセス。
- リストリテラル。
- `while` ループ。
- `for` 式。
- ユーザー定義関数、ラムダ、コンストラクタの部分適用。
- 小さな型チェッカ。
- prelude 標準ライブラリ。
- ファイルモジュール読み込み。
- REPL。

非目標:

- JVM バイトコード生成。
- 実 Java ライブラリ呼び出し。
- class/interface/継承などの OO。
- 完全な Hindley-Milner 型推論。
- パッケージ管理。

## 2. ソースファイル

ファイル拡張子は `.lune` とする。

1 ファイルは次の構造を持つ。

```lune
module app.main

import math
import java.time.LocalDate

def add(x: Int, y: Int): Int =
    x + y

let answer = add(20, 22)
```

`module` 宣言は任意である。`import` は top-level 宣言より前に置く。

## 3. コメント

行コメント:

```lune
# comment
```

ブロックコメント:

```lune
###
multi-line comment
###
```

`//` と `/* ... */` は v0.1 の現行実装ではコメントではない。

## 4. Layout

ブロックはインデントで表す。

```lune
def abs(x: Int): Int =
    if x < 0:
        -x
    else:
        x
```

タブによるインデントはエラーである。スペースを使う。

## 5. リテラル

利用可能なリテラル:

```lune
42
3.14
"hello"
'x'
true
false
null
()
```

整数は `Int`、小数は `Double`、文字列は `String`、`()` は `Unit` として扱う。

`'x'` は字句上は専用のトークンで、中身がちょうど 1 文字でなければ `LXL0002` になるが、**型は `String`** である。v0.1 に文字型はない（`Char` については 6 節を参照）。

## 6. 型

基本型:

```text
Bool
Int
Double
String
Unit
Any
Nothing
Null
```

上記が v0.1 の基本型の全部である。**`Long` / `Float` / `Char` は存在しない** — 数値は `Int`（任意精度）と `Double` の2つ、文字は `String` で表す。文字リテラル `'x'` の型も `String` であり、`Char` を生む式も、文字を扱う標準ライブラリ関数もない。

これら3つは将来仕様（`LANGUAGE_FUTURE_SPEC.md`）側の型とする。型注釈に書いた場合は、宣言されていない他の型名と同じ扱い（不透明な型）になるため `TYP0003` になる。

複合型:

```text
Option[Int]
Result[Int, String]
List[Int]
Lazy[Int]
IO[String]
Tuple[Int, String]
String?
```

`T?` は `Nullable[T]` として AST/type 表現される。代入・引数レベルの null safety を検査する。`null` と非 null の `T` はいずれも `T?` に代入・受け渡しできるが、`null` を非 null 型へ代入することはできず、`T?` を `T` が期待される位置でそのまま使うこともできない（アンラップが必要）。

アンラップ手段（`match` は「11. match」、`??` / `?.` / 比較は「9.1」「9.2」を参照）:

- `match` の `null` パターン。`| null -> …` が null を捕捉し、null を被覆した後の名前束縛は非 null の `T` にナローイングされる。`T?` の match は null と内部 `T` の両方を被覆して初めて exhaustive。
- `??` null 合体演算子。`a ?? b` は `a` が null のとき `b`（短絡評価）。
- `?.` セーフナビゲーション。`x?.m` は `x` が null なら null、そうでなければメンバ `m` を読む。結果は nullable。
- `if x != null` / `if x == null` のフロー・ナローイング。非 null が保証される分岐で `x` が `T` に絞り込まれる。
- `== null` / `!= null` 比較。

ナローイングは単純な `if x (!)= null`（`x` は変数）にのみ働く。複合条件（`&&` 等）、`elif`、`while` のナローイングや、`!!` 断言演算子はまだない。

関数型注釈はカリー化表記を正規形とする。

```text
Int -> Int
Int -> Int -> Int
```

`->` は右結合である。`(Int, Int) -> Int` は `Int -> Int -> Int` の糖衣として扱う。

タプル引数を 1 つ受け取る関数は `Tuple[Int, Int] -> Int` と書く。

## 7. 束縛

### 7.1 let

`let` は不変束縛であり、デフォルトで遅延される。

```lune
let x = expensive()
let y: Int = 42
```

右辺は参照されるまで評価されない。

### 7.2 strict let

`strict let` は束縛時に評価される。

```lune
strict let size = length(xs)
```

`!let` も parser 上は正格 let として扱われる。

### 7.3 var

`var` は可変束縛であり、束縛時に右辺を評価する。

```lune
var count = 0
count = count + 1
count += 1
```

代入対象は名前のみサポートする。

複合代入演算子 `+= -= *= /= //= %=` が使える。`x op= e` は `x = x op e` と同じで、型も実行時の意味も `x op e` に一致する。したがって `x /= 2` の結果は `Double` であり (`/` は常に真の除算)、`Int` の変数に対しては型エラーになる。`Int` の変数を `Int` のまま割るには `x //= 2` を使う (`//` は床除算)。ゼロ除算は `x / 0` / `x // 0` / `x % 0` と同じ `RUN0006` を報告する。詳細は `SYNTAX_SPEC.md` 14.1 節。

### 7.4 パターン束縛

`let` はパターン束縛をサポートする。パターンは反駁不能でなければならない。つまり、あらゆる値に照合するパターンのみ利用できる。

```lune
let (x, y) = (1, 2)
let Wrap(inner) = w   # Wrap が唯一のコンストラクタの場合
```

`Some(value)` のような照合に失敗しうるパターンは型エラー `TYP0008` になる。その場合は `match` を使う。詳細は `MATCH_EXHAUSTIVENESS_SPEC.md` §7 を参照する。

## 8. 関数

### 8.1 def

トップレベル関数を定義できる。

```lune
def add(x: Int, y: Int): Int =
    x + y
```

関数引数には v0.1 では型注釈が必要である。戻り値型は省略可能だが、公開 API 用の完全な推論ではない。

### 8.2 遅延引数と正格引数

関数引数はデフォルトで遅延される。

```lune
def first(a: Int, b: Int): Int =
    a

let answer = first(10, crash())
```

この例では `b` は使われないため `crash()` は評価されない。

正格引数:

```lune
def sum(!a: Int, !b: Int): Int =
    a + b
```

`strict a: Int` も正格引数として扱える。

### 8.3 ラムダ

ラムダは `fn` で書く。

```lune
let add = fn x y -> x + y
let inc = fn x: Int -> x + 1
```

複数行 body:

```lune
let f = fn x ->
    let y = x + 1
    y * 2
```

未注釈ラムダ引数の型は文脈から推論される。`let` / `var` の型注釈、`def` の戻り値注釈、関数呼び出しの引数位置に現れるラムダは、期待される関数型から引数型を受け取り、body はその型で検査される。

```lune
let inc: Int -> Int = fn x -> x + 1      # x : Int
let doubled = map([1, 2, 3], fn x -> x * 2)  # x : Int、doubled : List[Int]
```

文脈がない場合、未注釈ラムダ引数は `Any` にフォールバックし、warning `TYP0010` が報告される。詳細は `LOCAL_TYPE_INFERENCE_SPEC.md` を参照する。

### 8.4 部分適用

ユーザー定義関数、ラムダ、コンストラクタは部分適用できる。

```lune
let add = fn x y -> x + y
let inc = add(1)
let answer = inc(41)
```

`answer` は `42` になる。

型付き例:

```lune
let add = fn x: Int y: Int -> x + y
let inc = add(1)
```

`inc` の型は `Int -> Int` である。

組み込み関数の部分適用は v0.1 では未対応である。

## 9. 式

### 9.1 算術・比較・論理

利用可能な演算子:

```text
|>
??
|| &&
== != < <= > >=
+ - * / // %
! - +
```

実用対象:

```lune
1 + 2 * 3
x == y
x < y
cond && other
!flag
```

`+` は数値加算と `String + String` に対応する。

単項の `-` と `+` は同じ優先順位（右結合）である。`-x` は符号反転、`+x` は値をそのまま返す恒等演算で、どちらもオペランドに数値型を要求し、結果型はオペランドの型のままである。`+` を単項として認めるのは、`2 * -3` が書けて `2 * +3` が構文エラーになるという非対称を避けるためで、符号を明示したいときにも使える。

`/` は常に実数除算（true division）を行い、結果型は `Int / Int` の場合も含めて常に `Double` になる。

`//` は床除算（floor division）で、結果型は両辺の型のまま変わらない（`Int // Int` は `Int`、`Double // Double` は `Double`）。整数を整数で割って整数を得る手段はこれである。

```lune
7 // 2        # 3 : Int
7 / 2         # 3.5 : Double
7.0 // 2.0    # 3.0 : Double
```

`//` の丸めは負の無限大方向への切り下げ（floor）とする。ゼロ方向への切り捨て（truncation）ではない。これは `%` が除数の符号に合わせた剰余を返す既存の実装と整合させるためで、両者を合わせると任意の符号について次の除算等式が成り立つ。

```text
a == (a // b) * b + (a % b)
```

```lune
-7 // 2       # -4（-3 ではない）
-7 % 2        # 1
7 // -2       # -4
7 % -2        # -1
```

`/` と `//` と `%` はいずれも右オペランドが 0 のとき実行時エラー `RUN0006`（`division by zero` / 「ゼロ除算です」）を送出する。型検査では捕まらない。

`++` と `::` は parser にあるが、現状の runtime/typechecker では実用対象外である。

`|>` はパイプライン演算子で、`x |> f` は `f(x)` の糖衣である。型検査・評価とも `f(x)` と同一に扱い、部分適用にも対応する（例: `5 |> add` は `add(5)` となり `Int -> Int` を返す）。

`??` は null 合体演算子で、左辺は nullable `T?` でなければならない。`a ?? b` は `a` が null なら `b` を返す（`b` は非 null のとき評価しない＝短絡）。結果型は `b` が非 null なら `T`、`b` も nullable なら `T?`。右結合。`==` / `!=` は `T?` と `null`、および `T?` と内部型 `T` の比較を許可する（`x == null` など）。

`?.` はセーフナビゲーション（後置。`.` と同じ位置で使う）。左辺は nullable `T?` でなければならず、`x?.m` は `x` が null なら null に短絡し、そうでなければ内部値のメンバ `m` を読む。結果型は常に nullable（`m` の型 `U` に対し `U?`）。`x?.a?.b` のように連鎖できる。nullable に通常の `.` を使うと型エラーになる。

#### 9.1.1 等価比較の意味論

`==` / `!=` は構造的等価（structural equality）で判定する。同一のオブジェクトかどうか（identity）は言語の意味論に現れない。

- `Int` / `Double` / `Bool` / `String` / `Unit` / `null` は値そのもので比較する。
- タプルは要素数が等しく、対応する要素がすべて `==` のとき等しい。
- リスト・ADT 値はコンストラクタが同じで、対応するフィールドがすべて `==` のとき等しい。
- レコードはレコード型が同じで、対応するフィールドがすべて `==` のとき等しい。

```lune
(1, 2) == (1, 2)              -- true
[1, 2] == [1, 2]              -- true
Some(1) == Some(1)            -- true
[1, 2] == [1, 2, 3]           -- false（長さが違う）
```

関数値・コンストラクタ関数に構造的等価はない。同一の関数値どうしのときのみ true になるが、関数を `==` で比較するコードは書くべきではない。

比較は両辺を左から順に、必要な分だけ force する（`deepForce` 相当まで）。最初の不一致が見つかった時点で残りは評価せずに false を返す。したがって無限リスト同士の `==` は、不一致が見つからない限り停止しない。これは仕様である。詳細は `LAZY_EVALUATION_SPEC.md` §11 を参照。

### 9.2 if

1 行形式:

```lune
let label = if score >= 80 then "pass" else "fail"
```

block 形式:

```lune
let label =
    if score >= 80:
        "pass"
    elif score >= 60:
        "retry"
    else:
        "fail"
```

条件は `Bool` でなければならない。各分岐の型は一致する必要がある。ただし `Nothing` は他の分岐型へ合流できる。

条件が `x != null` または `x == null`（`x` は nullable な変数）のとき、非 null が保証される分岐で `x` は内部型 `T` にフロー・ナローイングされる。`x != null` なら then 節、`x == null` なら else 節。ナローイングは単純なこの形にのみ働き、複合条件や `elif` には及ばない。

```lune
def orOne(x: Int?): Int =
    if x != null then x else 1     # then 節で x は Int
```

### 9.3 let-in

式内 `let` を利用できる。

```lune
let answer = let x = 40 in x + 2
```

### 9.4 lazy / force

```lune
let delayed = lazy (1 + 2)
let answer = force delayed
```

`lazy expr` は `Lazy[T]` を作る。`force Lazy[T]` は `T` を返す。

block 形式:

```lune
let delayed = lazy:
    expensive()
```

### 9.5 seq / deepForce

`seq a b` は `a` を弱頭正規形まで評価し、`b` を返す。

```lune
let answer = seq x 42
```

`deepForce value` はデータ構造の中身を可能な限り評価する。

### 9.6 raise / throw

`raise expr` と `throw expr` は実行時エラーを送出する式として扱う。

```lune
let bad = raise "failed"
```

`try/catch/finally` は未対応である。

### 9.7 IO block

`IO:` block は構文として利用できる。

```lune
def main(): IO[Unit] =
    IO:
        println("hello")
```

v0.1 では厳密な IO effect system ではなく、通常 block 評価に近い。

### 9.8 while

`while` は `var` と代入を使うための最小の反復構文である。

```lune
let answer =
    var i = 0
    var total = 0
    while i < 5:
        total = total + i
        i = i + 1
    total
```

条件は `Bool` でなければならない。条件は各 iteration で評価され、弱頭正規形まで force される。

`while` 式全体の型は常に `Unit` である。`break` / `continue` は未対応である。

### 9.9 for

`for` は `List[T]` を走査するための最小の反復構文である。

```lune
let answer =
    var total = 0
    for x in [1, 2, 3, 4]:
        total = total + x
    total
```

`for pattern in iterable:` の `iterable` は `List[T]` でなければならない。`pattern` は各要素に対して照合され、body 内で利用できる。`let` と同様に、パターンは反駁不能でなければならない。照合に失敗しうるパターンは型エラー `TYP0008` になる。

```lune
for (left, right) in pairs:
    println(left + right)
```

`for` はリストの spine を iteration ごとに force する。body の結果値は捨てられ、`for` 式全体の型は常に `Unit` である。`break` / `continue` は未対応である。

## 10. ADT

ADT は `type` で定義する。

```lune
type Option[T] =
    | Some(value: T)
    | None
```

複数フィールド:

```lune
type Pair =
    | Pair(left: Int, right: Int)
```

正格フィールド:

```lune
type Point =
    | Point(!x: Double, !y: Double)
```

コンストラクタフィールドはデフォルトで遅延される。正格フィールドは生成時に評価される。

コンストラクタも部分適用できる。

```lune
let withOne = Pair(1)
let pair = withOne(41)
```

### 10.1 コンストラクタ引数は位置引数のみ

ADT のコンストラクタは**位置引数だけ**を受け取る。宣言でフィールドに名前が付いていても、呼び出し側でその名前を使って渡すことはできない。

```lune
type Entry =
    | Income(label: String, amount: Int)

let a = Income("a", 1)             # OK
let b = Income(label = "a")        # error[TYP0012]
```

`名前 = 値` の形で構築できるのはレコードだけである（§13、`RECORD_FIELD_SPEC.md`）。この非対称は意図的で、根拠は部分適用にある。コンストラクタと関数は curry されるため（§8.4）、`Income(amount = 1)` は「第 1 引数が未充填の部分適用」となり、ラベルを対応させる先が存在しない。名前付き引数と curry 化を両立させるには OCaml のラベル付き引数に相当する機構が必要で、v0.1 の範囲外である。レコードは curry されず全フィールドを一度に与える構築なので、名前付き必須（`REC0006`）が無理なく成立する。

ラベルは**黙って無視されない**。以前は無視されて位置で解釈されていたため、同じ型のフィールドが並ぶ場合に値が診断なしで入れ違った（`Point(y = 1, x = 2)` が `Point(1, 2)` になる）。現在は `TYP0012` で拒否する。

同じ理由から、ユーザー定義関数・ラムダ・組み込み関数の呼び出しでも名前付き引数は `TYP0012` になる。

## 11. match

`match` は式である。

```lune
let answer =
    match value:
        | Some(x) -> x
        | None -> 0
```

複数行 case body:

```lune
match value:
    | Some(x) ->
        let y = x + 1
        y * 2
    | None -> 0
```

guard:

```lune
match n:
    | x if x < 0 -> -x
    | x -> x
```

対応パターン:

- `_`
- 名前
- リテラル
- `null`（nullable `T?` の null 値にマッチ）
- タプル
- コンストラクタ
- OR パターン
- 型付きパターン

`match` は網羅的でなければならない。ケース漏れは型エラー `TYP0007` として報告され、欠落パターンの例が表示される。guard 付きケースは網羅性に寄与しない。scrutinee 型が `Any` または型変数の場合は検査しない。

先行ケースに完全に覆われて到達できないケースは warning `TYP0009` として報告される。詳細は `MATCH_EXHAUSTIVENESS_SPEC.md` を参照する。

nullable `T?` を match する場合、`null` パターンは null 値のみに、それ以外のパターン（名前・リテラル・コンストラクタ等）は非 null の内部値（型 `T`）にマッチする。`null` を被覆した後に現れるトップレベルの名前束縛は非 null の `T` にナローイングされる。

```lune
def orZero(value: Int?): Int =
    match value:
        | null -> 0
        | v -> v          # v は Int（非 null）
```

網羅性は null の被覆と内部 `T` の網羅の両方を要求する。`| null -> …` が無ければ欠落パターン `null` として `TYP0007`、内部が網羅されていなければ内部の欠落パターンとして `TYP0007` になる。

タプル式:

```lune
let pair = (1, "one")
```

タプルパターン:

```lune
let (x, name) = pair
```

内部的には `__tuple__` builtin を使う。

## 13. レコード / メンバーアクセス / インデックス

レコードは `record` で定義する。

```lune
record User:
    name: String
    age: Int

let ada = User(name = "Ada", age = 36)
let name = ada.name
```

record construction は named argument のみをサポートする。field の指定順は宣言順と異なってもよいが、すべての field をちょうど 1 回指定する必要がある。位置引数での構築は `REC0006` で拒否する。

`名前 = 値` が意味を持つのはこのレコード構築だけである。ADT のコンストラクタと関数呼び出しでは位置引数のみが有効で、名前付き引数は `TYP0012` になる（§10.1）。

generic record:

```lune
record Box[T]:
    value: T

let box = Box(value = 42)
let value = box.value
```

record field は immutable である。record update、record pattern、mutable field は未対応である。

通常 field は遅延される。正格 field は `!` または `strict` を付ける。

```lune
record Point:
    !x: Double
    !y: Double
```

`String.length()` は runtime/typechecker で特別扱いされる。

```lune
let n = "hello".length()
```

外部 import 由来など `Any` のメンバーアクセスは型上 `() -> Any` として扱う。

次は現状では実用対象外である。

```lune
object.method()
list[0]
```

データコンストラクタのフィールドアクセスは未実装であり、`match` を使う。レコードとフィールドアクセスの詳細は `RECORD_FIELD_SPEC.md` に定義する。

## 14. モジュール

ローカルモジュール:

```lune
module main
import math

let answer = add(40, 2)
```

`import math` は探索 root 上の `math.lune` に解決される。`import util.numbers` は `util/numbers.lune` に解決される。

探索 root:

1. entry file の親ディレクトリ。
2. カレントワーキングディレクトリ。
3. CLI の `--module-path PATH`。

v0.1 では imported module のトップレベル名を同じグローバル環境へ直接登録する。qualified access は未対応である。

```lune
math.add(1, 2) # 未対応
```

外部 import:

```lune
import java.time.LocalDate
```

`java.*`、`javax.*`、`kotlin.*`、`std.*` はファイル解決せず、型チェッカでは末尾名または alias を `Any` として登録する。実 Java 呼び出しは未対応である。

## 15. 標準ライブラリ

prelude として import なしで利用できる。

ADT:

```text
Option[T] : Some(value), None
Result[T, E] : Ok(value), Err(error)
List[T] : Cons(head, tail), Nil
```

関数:

```text
print
println
show
id
const
not
isSome
isNone
getOrElse
optionMap
isOk
isErr
resultMap
unwrapOr
isEmpty
head
tail
length
map
filter
fold
take
drop
range
```

リストは `Cons` / `Nil`、`range(start, end)`、またはリストリテラルで作れる。

```lune
let numbers = [1, 2, 3]
let sameNumbers = (1 2 3)
let empty: List[Int] = []
```

`(1 2 3)` は表示互換の Lisp 風リストリテラルである。`()` は空リストではなく `Unit` のままなので、空リストには `[]` を使う。

リストリテラルの要素は同じ型でなければならない。`[1, true]` は型エラーである。

要素式は遅延される。たとえば `head([1, crash()])` は `Some(1)` を返し、2 番目の要素は評価しない。

リスト操作の基本形:

```lune
let numbers = [1, 2, 3, 4, 5]
let doubled = map(numbers, fn x -> x * 2)
let evens = filter(numbers, fn x -> x % 2 == 0)
let total = fold(numbers, 0, fn acc x -> acc + x)
let firstTwo = take(numbers, 2)
let rest = drop(numbers, 2)
let first = head(numbers)
let tailValue = tail(numbers)
```

実装確認用の builtin として、現状は次も初期環境に存在する。

```text
crash
tick
tickCount
```

これらは遅延評価やメモ化の挙動をテストするための補助機能であり、安定した標準 API としてはまだ扱わない。

## 16. 型チェッカ

v0.1 typechecker は、完全な型推論ではなく小さな単一化ベースの検査器である。

検査対象:

- `let` / `var` 型注釈。
- 関数引数と戻り値。
- 基本演算。
- `if` 分岐型。
- `while` 条件型。
- ADT コンストラクタ呼び出し。
- record construction と field access。
- `match` パターンと分岐型。
- `match` 網羅性 (`MATCH_EXHAUSTIVENESS_SPEC.md`)。
- `lazy` / `force`。
- 関数・コンストラクタ部分適用。
- 標準ライブラリ関数の型。

`Any` は v0.1 の逃げ道であり、任意の型に代入可能として扱う。

制限:

- 期待型伝播によるローカル型推論あり (`LOCAL_TYPE_INFERENCE_SPEC.md`)。body 制約からの単一化推論と let 多相は未実装。
- 関数型注釈の本格検査は未実装。
- Java 型解決は未実装。
- class/interface の型検査は未実装。

## 17. 評価モデル

Lune v0.1 はデフォルト遅延評価である。

遅延されるもの:

- 通常 `let` の右辺。
- 通常関数引数。
- 通常コンストラクタフィールド。
- 通常 record field。
- `lazy expr` の body。

評価される境界:

- 変数参照。
- `force`。
- `seq` の第 1 引数。
- `deepForce`。
- 条件式の条件。
- `while` の条件。
- 二項演算に必要な引数。
- `match` の scrutinee 外側コンストラクタ。
- リテラルパターン比較。
- 正格引数。
- `strict let`。
- 正格コンストラクタフィールド。
- 正格 record field。

サンクは成功・失敗ともにメモ化される。再入評価は実行時エラーである。

## 18. REPL

起動:

```sh
./bin/lune
```

コマンド:

```text
:help
:quit
:q
:env
:type NAME
```

式入力は値と型を表示する。

```text
lune> 1 + 2
3 : Int
lune> "Ada"
"Ada" : String
lune> [1, 2, 3]
(1 2 3) : List[Int]
```

REPL の `import` は v0.1 では `Any` 登録に留まり、ファイルモジュール読み込みはしない。

## 19. CLI

parse:

```sh
./bin/lune samples/option.lune
```

tokens:

```sh
./bin/lune --tokens samples/basics.lune
```

type check:

```sh
./bin/lune --check samples/option.lune
```

evaluate a top-level binding:

```sh
./bin/lune --eval answer samples/modules/main.lune
```

module path:

```sh
./bin/lune --module-path lib --check src/main.lune
```

サブコマンド:

```sh
./bin/lune explain TYP0007          # 診断コードの詳解を表示（詳細は ERROR_DIAGNOSTICS_SPEC.md §4.1）
./bin/lune fmt --write src/main.lune   # 正準スタイルに整形（詳細は FORMATTER_SPEC.md）
./bin/lune fix --write src/main.lune   # 提案された修正を自動適用（詳細は ERROR_DIAGNOSTICS_SPEC.md §9.5）
```

`fmt` / `fix` は `--write`（その場書き換え）と `--check`（未整形/修正候補があれば終了コード 1）を持つ。引数なし（またはグローバル `--lang` のみ）の `./bin/lune` は REPL を起動する。診断の既定言語は環境変数 `LUNE_LANG` で設定でき、`--lang` フラグが優先する（`REPL_SPEC.md` §1.1）。

## 20. エラー表示

lexer/parser/typechecker/runtime/module loader のエラーは diagnostic として表示される。

例:

```text
error[TYP0001]: undefined name: x
  --> sample.lune:1:9
1 | let y = x
  |         ^ name is not defined
```

## 21. 現状未対応

未対応または実用対象外:

- JVM バイトコード生成。
- 実 Java ライブラリ呼び出し。
- `class` / `interface` / `extends` / `implements`。
- `this` / `super` / `new` の意味処理。
- `try` / `catch` / `finally`。
- `return` / `break` / `continue`。
- `export`。
- annotation。
- `use` / resource management。
- record update / record pattern / mutable record field。
- `Stream` / `Map` / `Set` / `Promise` / `Iterator`。
- package manager。
- LSP。

一部 token や AST は将来機能用に存在するが、この文書では現行 evaluator/typechecker/CLI で動かせるものを v0.1 の利用可能機能とする。
