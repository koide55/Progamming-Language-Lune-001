# Lune 標準ライブラリ最小仕様

Version: 0.1 draft  
Related: `LANGUAGE_SPEC.md`, `TYPE_CHECKER_SPEC.md`, `LAZY_EVALUATION_SPEC.md`, `REPL_SPEC.md`

この文書は Lune v0.1 で利用可能にする標準ライブラリの最小セットを定義する。

## 1. 目的

v0.1 標準ライブラリは、サンプルや小さなプログラムを毎回自前定義なしで書けるようにするための最小 API である。

目標:

- `Option`、`Result`、`List` を組み込みで使える。
- `map`、`filter`、`fold` などの基本操作を提供する。
- 文字列と数値の最小変換を提供する。
- `Console.println` 相当の出力を提供する。
- Python 実装の v0.1 evaluator/typechecker で実装しやすい形にする。

非目標:

- 完全なコレクションライブラリ。
- 遅延ストリームの本格実装。
- ファイル、ネットワーク、並行処理。
- Java 標準ライブラリの型付きラッパー。

## 2. 提供方式

v0.1 では標準ライブラリを evaluator/typechecker の初期環境に組み込みで登録する。

将来は `std/*.lune` として Lune 自身で実装し、compiler/interpreter が起動時に読み込む方式へ移行する。

ユーザーは import なしで以下の名前を利用できる。

```text
Option, Some, None
Result, Ok, Err
List, Cons, Nil
true, false
print
println
show
length
map
filter
fold
take
drop
head
tail
isEmpty
range
```

## 3. モジュール構成

将来の標準モジュール名は以下とする。

```text
std.core
std.option
std.result
std.list
std.console
```

v0.1 ではすべて prelude として暗黙 import する。

## 4. Option

定義:

```lune
type Option[T] =
    | Some(value: T)
    | None
```

関数:

```lune
def isSome[T](option: Option[T]): Bool
def isNone[T](option: Option[T]): Bool
def getOrElse[T](option: Option[T], defaultValue: T): T
def optionMap[T, U](option: Option[T], f: T -> U): Option[U]
```

意味:

- `Some(value)` は値あり。
- `None` は値なし。
- `getOrElse(Some(x), d)` は `x`。
- `getOrElse(None, d)` は `d`。
- `optionMap(Some(x), f)` は `Some(f(x))`。
- `optionMap(None, f)` は `None`。

遅延評価:

- `Some(value)` の `value` はデフォルト遅延フィールドである。
- `getOrElse(None, defaultValue)` は `defaultValue` を必要になった時だけ評価する。
- `optionMap(None, f)` は `f` を呼ばない。

## 5. Result

定義:

```lune
type Result[T, E] =
    | Ok(value: T)
    | Err(error: E)
```

関数:

```lune
def isOk[T, E](result: Result[T, E]): Bool
def isErr[T, E](result: Result[T, E]): Bool
def resultMap[T, U, E](result: Result[T, E], f: T -> U): Result[U, E]
def unwrapOr[T, E](result: Result[T, E], defaultValue: T): T
```

意味:

- `Ok(value)` は成功。
- `Err(error)` は失敗。
- `resultMap(Ok(x), f)` は `Ok(f(x))`。
- `resultMap(Err(e), f)` は `Err(e)`。
- `unwrapOr(Ok(x), d)` は `x`。
- `unwrapOr(Err(e), d)` は `d`。

## 6. List

定義:

```lune
type List[T] =
    | Cons(head: T, tail: List[T])
    | Nil
```

リストは `Cons(1, Cons(2, Nil))`、`range`、またはリストリテラルで作る。

```lune
let numbers = [1, 2, 3]
let empty: List[Int] = []
```

関数:

```lune
def isEmpty[T](list: List[T]): Bool
def head[T](list: List[T]): Option[T]
def tail[T](list: List[T]): Option[List[T]]
def length[T](list: List[T]): Int
def map[T, U](list: List[T], f: T -> U): List[U]
def filter[T](list: List[T], predicate: T -> Bool): List[T]
def fold[T, U](list: List[T], initial: U, f: (U, T) -> U): U
def take[T](list: List[T], count: Int): List[T]
def drop[T](list: List[T], count: Int): List[T]
def range(start: Int, end: Int): List[Int]
```

意味:

- `isEmpty(Nil)` は `true`。
- `isEmpty(Cons(_, _))` は `false`。
- `head(Nil)` は `None`。
- `head(Cons(x, _))` は `Some(x)`。
- `tail(Nil)` は `None`。
- `tail(Cons(_, xs))` は `Some(xs)`。
- `length` はリスト長を返す。
- `map` は各要素に関数を適用する。
- `filter` は predicate が true の要素だけを残す。
- `fold` は左畳み込み。
- `take(list, count)` は先頭から最大 `count` 個を返す。`count <= 0` なら `Nil`。
- `drop(list, count)` は先頭から最大 `count` 個を捨てた残りを返す。`count <= 0` なら元のリストを返す。
- `range(start, end)` は `start <= x < end` の整数リストを返す。
- REPL / `show` / `repr` では有限リストを Lisp 風に表示する。例: `[1, 2]` と `range(1, 3)` は `(1 2)`、`Nil` は `()`。

遅延評価:

- `Cons(head, tail)` の両フィールドはデフォルト遅延である。
- リストリテラルの要素も遅延される。`head([1, crash()])` は 2 番目の要素を評価しない。
- `head(Cons(x, crash()))` は tail を評価しない。
- `map` は v0.1 では結果リストの spine を必要に応じて構築してよい。実装都合で eager に spine を作ってもよいが、要素値は可能な限り遅延を保つ。
- `take(list, 0)` は `list` を評価しない。
- `take` は返したリストの tail を遅延する。
- `drop` は捨てる範囲の spine を評価するが、残りの要素値は評価しない。

## 7. Console / IO

v0.1 では副作用モデルの完全実装はまだ行わない。以下を builtin として提供する。

```lune
def print(value: Any): Unit
def println(value: Any): Unit
```

意味:

- `print` は改行なしで標準出力へ出力する。
- `println` は改行ありで標準出力へ出力する。
- 値は `show` によって文字列化される。

将来:

```lune
Console.print(value)
Console.println(value)
Console.readLine(prompt)
```

を `std.console` に移動する。

## 8. Core

基本関数:

```lune
def show(value: Any): String
def id[T](value: T): T
def const[T, U](value: T, ignored: U): T
def not(value: Bool): Bool
```

意味:

- `show` は値を Lune の標準表示形式にする。詳細は `VALUE_DISPLAY_SPEC.md` を参照する。
- 例: `show("Ada")` の結果文字列は `"Ada"`、`show([1, 2])` は `(1 2)`、`show(Some("ok"))` は `Some("ok")`。
- `id(x)` は `x`。
- `const(x, y)` は `x`。
- `not(x)` は真偽値を反転する。

## 9. 型チェッカ登録

v0.1 typechecker は初期環境へ以下を登録する。

```text
Some       : [T] (T) -> Option[T]
None       : [T] () -> Option[T]
Ok         : [T, E] (T) -> Result[T, E]
Err        : [T, E] (E) -> Result[T, E]
Cons       : [T] (T, List[T]) -> List[T]
Nil        : [T] () -> List[T]

isSome     : [T] (Option[T]) -> Bool
isNone     : [T] (Option[T]) -> Bool
getOrElse  : [T] (Option[T], T) -> T
optionMap  : [T, U] (Option[T], (T) -> U) -> Option[U]

isOk       : [T, E] (Result[T, E]) -> Bool
isErr      : [T, E] (Result[T, E]) -> Bool
resultMap  : [T, U, E] (Result[T, E], (T) -> U) -> Result[U, E]
unwrapOr   : [T, E] (Result[T, E], T) -> T

isEmpty    : [T] (List[T]) -> Bool
head       : [T] (List[T]) -> Option[T]
tail       : [T] (List[T]) -> Option[List[T]]
length     : [T] (List[T]) -> Int
map        : [T, U] (List[T], (T) -> U) -> List[U]
filter     : [T] (List[T], (T) -> Bool) -> List[T]
fold       : [T, U] (List[T], U, (U, T) -> U) -> U
take       : [T] (List[T], Int) -> List[T]
drop       : [T] (List[T], Int) -> List[T]
range      : (Int, Int) -> List[Int]

print      : (Any) -> Unit
println    : (Any) -> Unit
show       : (Any) -> String
id         : [T] (T) -> T
const      : [T, U] (T, U) -> T
not        : (Bool) -> Bool
```

v0.1 の型チェッカは表面構文の関数型注釈に限定対応であるため、builtin の関数型は内部表現で登録する。

## 10. Evaluator 登録

v0.1 evaluator は初期環境へ以下を登録する。

- `Some`, `None`, `Ok`, `Err`, `Cons`, `Nil` をコンストラクタ値として登録する。
- `print`, `println`, `show`, `id`, `const`, `not` を builtin 関数として登録する。
- `isSome`, `isNone`, `getOrElse`, `optionMap` を builtin 関数として登録する。
- `isOk`, `isErr`, `resultMap`, `unwrapOr` を builtin 関数として登録する。
- `isEmpty`, `head`, `tail`, `length`, `map`, `filter`, `fold`, `take`, `drop`, `range` を builtin 関数として登録する。

注意:

- v0.1 の builtin は Python 実装のランタイム値を直接扱ってよい。
- `print` / `println` 以外は原則として純粋関数として扱う。
- 遅延値を受け取る builtin は必要な分だけ `force` する。

## 11. 名前衝突

ユーザーが同名のトップレベル宣言を行った場合、v0.1 ではユーザー宣言が標準ライブラリ名を上書きできる。

将来は import と名前空間によって、prelude の shadowing に警告を出す。

## 12. エラー

部分関数は避け、失敗する可能性がある操作は `Option` または `Result` を返す。

例:

- `head(Nil)` は runtime error ではなく `None`。
- `tail(Nil)` は runtime error ではなく `None`。

`fold`、`map`、`filter` に関数でない値を渡した場合は型エラーまたは runtime error とする。

## 13. v0.1 で保留するもの

- infix cons 演算子 `::` の evaluator 実装。
- `String.split` などの文字列詳細 API。
- `Map` / `Set`。
- ファイル IO。
- 例外と `Result` の自動変換。
- Java コレクションとの変換。
