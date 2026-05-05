# Lune 将来言語仕様

Version: future draft  
Target implementation: JVM first, self-hosting optional later  
Current implementation reference: `LANGUAGE_SPEC.md`

この文書は Lune の長期的な目標仕様を定義する。現時点で利用できる機能は `LANGUAGE_SPEC.md` を正とする。

## 1. 設計目標

Lune は、遅延評価を中心にした関数型プログラミングと、Java 互換のオブジェクト指向モデルを同じ言語内で扱うためのプログラミング言語である。

主な目標:

- 遅延評価を標準の評価戦略にする。
- 純粋関数、代数的データ型、パターンマッチを第一級機能として提供する。
- クラス、インターフェース、メソッド、継承、委譲をサポートする。
- JVM 上で動作し、Java ライブラリを直接呼び出せる。
- ガーベジコレクションは JVM GC を利用し、言語仕様として所有権や手動解放を要求しない。
- 実装初期段階では、コンパイラまたはインタプリタのどちらでも実装できる単純なコア言語を持つ。

非目標:

- Java との完全な構文互換。
- C/C++ のような手動メモリ管理。
- 初期仕様でのマクロシステム、依存型、ネイティブコード生成。

## 2. 評価戦略

Lune はデフォルトで非正格、つまり遅延評価を行う。

式は必要になるまで評価されず、評価結果はメモ化される。同じ遅延値を複数回参照しても計算は原則 1 回だけ行われる。

ただし、以下は正格に評価される。

- JVM/Java への外部呼び出し。
- `strict` で明示された引数、変数、フィールド。
- 条件分岐の条件部。
- パターンマッチに必要な外側のコンストラクタ判定。
- `seq`、`force`、`deepForce` によって明示的に強制された式。

副作用は `IO[T]` 型で表現する。ファイル操作、標準入出力、ネットワーク、現在時刻、乱数、Java メソッド呼び出しのうち副作用を持つものは `IO` の中で扱う。

初期実装では Java メソッドの純粋性を静的に完全判定しない。Java 呼び出しは原則 `IO` 扱いとし、ユーザーが `@pure` アノテーションで明示的に純粋扱いへ昇格できる。

## 3. 型システム

基本型:

```text
Bool
Int
Long
Float
Double
Char
String
Unit
Nothing
Any
```

`Unit` は値を返さない処理の結果を表す。値は `()`。

`Nothing` は正常に値を返さない式の型である。例: 例外送出、無限ループ。

通常の参照型は null 非許容である。

```lune
let name: String = "Ada"
let missing: String? = null
```

`T?` は null 許容型である。

関数型:

```lune
Int -> Int
(Int, Int) -> Int
String -> IO[Unit]
```

関数は第一級値であり、クロージャと部分適用をサポートする。

```lune
let add = fn x y -> x + y
let inc = add(1)
```

ジェネリクス:

```lune
def identity[T](x: T): T = x
```

初期 JVM 実装では JVM の型消去を採用する。将来、特殊化による最適化を許可する。

型推論:

- ローカル変数、ラムダ、関数戻り値には型推論を行う。
- 公開 API、Java から呼び出される関数、再帰関数の戻り値には型注釈を推奨し、コンパイラ警告の対象とする。

## 4. 束縛と関数

不変束縛:

```lune
let x = expensiveComputation()
```

`let` は不変束縛であり、デフォルトでは遅延値である。

可変束縛:

```lune
var count = 0
count = count + 1
```

`var` は正格評価される。可変状態はクラス内部や `IO` の中で使うことを推奨する。

正格束縛:

```lune
strict let size = file.length()
```

通常関数:

```lune
def square(x: Int): Int =
    x * x
```

関数引数はデフォルトで遅延される。

```lune
def choose(cond: Bool, a: Int, b: Int): Int =
    if cond then a else b
```

正格引数:

```lune
def sum(strict a: Int, strict b: Int): Int =
    a + b
```

パイプライン:

```lune
users
    |> filter(fn u -> u.active)
    |> map(fn u -> u.name)
```

`x |> f` は `f(x)` と等価である。

## 5. 制御構文

`if` は式である。

```lune
let label =
    if score >= 80 then "pass" else "fail"
```

`match` は式である。代数的データ型に対する網羅性チェックを行う。

```lune
match value:
    | Some(x) -> x
    | None -> 0
```

例外は JVM 例外と相互運用する。

```lune
try:
    risky()
catch e: java.io.IOException:
    recover(e)
finally:
    cleanup()
```

## 6. 代数的データ型

```lune
type Option[T] =
    | Some(value: T)
    | None

type List[T] =
    | Cons(head: T, tail: List[T])
    | Nil
```

コンストラクタのフィールドはデフォルトで遅延される。正格フィールドは `strict` または `!` を付ける。

```lune
type Point =
    | Point(strict x: Double, strict y: Double)
```

## 7. オブジェクト指向

### 7.1 クラス

```lune
class User(name: String, age: Int):
    def displayName(): String =
        name
```

プライマリコンストラクタの引数は、クラス本体内からフィールドとして参照できる。

### 7.2 可視性

```lune
class Counter:
    private var value = 0

    public def increment(): Unit =
        value = value + 1

    public def get(): Int =
        value
```

可視性:

- `public`: どこからでも参照可能。
- `internal`: 同一モジュール内のみ。
- `protected`: サブクラスから参照可能。
- `private`: 同一クラス内のみ。

デフォルトは `public`。

### 7.3 継承

```lune
abstract class Animal:
    abstract def speak(): String

class Dog extends Animal:
    override def speak(): String =
        "woof"
```

単一継承のみを許可する。

### 7.4 インターフェース

```lune
interface Named:
    def name(): String

class Person(value: String) implements Named:
    override def name(): String =
        value
```

インターフェースは複数実装を許可する。

### 7.5 オブジェクト初期化と遅延

クラスフィールドはデフォルトで遅延評価される。ただし Java 互換フィールド、`var`、`strict` フィールドは正格評価される。

```lune
class Report(source: Source):
    let summary = source.load().summarize()
    strict let createdAt = java.time.Instant.now()
```

## 8. Java 相互運用

import:

```lune
import java.time.LocalDate
import java.util.ArrayList
```

Java クラスの生成:

```lune
let list = new java.util.ArrayList[String]()
list.add("hello")
```

Java static メンバー:

```lune
let now = java.time.LocalDate.now()
let max = java.lang.Math.max(10, 20)
```

Java メソッド呼び出しは正格評価境界である。引数は呼び出し前に強制評価される。

```lune
def printLine(message: String): IO[Unit] =
    java.lang.System.out.println(message)
```

Java 型対応:

| Lune | Java/JVM |
| --- | --- |
| `Bool` | `boolean` / `java.lang.Boolean` |
| `Int` | `int` / `java.lang.Integer` |
| `Long` | `long` / `java.lang.Long` |
| `Float` | `float` / `java.lang.Float` |
| `Double` | `double` / `java.lang.Double` |
| `Char` | `char` / `java.lang.Character` |
| `String` | `java.lang.String` |
| `Unit` | `void` where possible, otherwise `lune.Unit` |
| `T?` | nullable reference |
| `IO[T]` | `lune.runtime.IO<T>` |

Java 連携アノテーション:

```lune
@java.name("com.example.App")
class App:
    @java.static
    def main(args: Array[String]): Unit =
        run(args).unsafeRun()
```

必須候補:

- `@java.name("...")`: JVM 上の完全修飾名を指定する。
- `@java.static`: static メソッドまたはフィールドとして公開する。
- `@java.throws(ExceptionType)`: Java 側へ checked exception 情報を公開する。
- `@pure`: Java 呼び出しや外部関数を純粋扱いする。

## 9. モジュール

```lune
module example.hello

import java.time.LocalDate

export def greeting(name: String): String =
    "Hello, " + name
```

1 ファイル 1 モジュールを推奨する。モジュール名は JVM パッケージ名に対応する。

将来の module system は以下を扱う。

- 明示 export。
- import alias。
- qualified access。
- 可視性と module boundary。
- package metadata。
- incremental compilation。

## 10. 標準ライブラリ

初期標準ライブラリに含めるもの:

- `Option[T]`
- `Result[T, E]`
- `List[T]`
- `Stream[T]`
- `Map[K, V]`
- `Set[T]`
- `IO[T]`
- `Promise[T]`
- `Lazy[T]`
- `Iterator[T]`
- 文字列、数値、コレクション操作
- Java コレクションとの変換

### 10.1 Lazy

```lune
let x: Lazy[Int] = lazy:
    expensive()

let y = x.force()
```

`Lazy[T]` は明示的な遅延値であり、評価結果をメモ化する。

### 10.2 Stream

```lune
def from(n: Int): Stream[Int] =
    Stream.cons(n, lazy:
        from(n + 1))
```

`Stream` は無限列を扱うための標準データ構造である。

## 11. メモリ管理

Lune の実装はガーベジコレクションを必須とする。

JVM 実装では JVM GC を利用する。言語レベルでは以下を保証する。

- 通常のオブジェクトは明示的に解放しない。
- 到達不能になった遅延サンク、クロージャ、オブジェクトは GC 対象になる。
- `finally`、`AutoCloseable`、`use` により外部リソースを解放できる。

```lune
use reader = java.nio.file.Files.newBufferedReader(path)
reader.readLine()
```

`use` はスコープ終了時に `close()` を呼ぶ。

## 12. ランタイムモデル

遅延式はランタイム上で `Thunk[T]` として表現される。

```text
Thunk state:
  Unevaluated(closure)
  Evaluating
  Evaluated(value)
  Failed(exception)
```

同じサンクの再入評価は実行時エラーとする。

コンパイラは自己再帰の末尾呼び出しをループへ変換することを推奨する。JVM の制約上、一般の相互末尾再帰最適化は必須ではない。

初期仕様では Java のスレッド、Executor、CompletableFuture と相互運用する。将来仕様として軽量タスク、構造化並行性、アクターモデルを検討する。

## 13. 構文例

Hello world:

```lune
module hello

def main(args: Array[String]): IO[Unit] =
    IO.println("Hello, Lune")
```

遅延評価:

```lune
def first(a: Int, b: Int): Int =
    a

let value = first(10, crash())
```

無限列:

```lune
def naturalsFrom(n: Int): Stream[Int] =
    Stream.cons(n, lazy:
        naturalsFrom(n + 1))

let firstTen = naturalsFrom(1).take(10).toList()
```

Java ライブラリ呼び出し:

```lune
import java.time.LocalDate
import java.time.format.DateTimeFormatter

def todayText(): IO[String] =
    IO:
        let today = LocalDate.now()
        today.format(DateTimeFormatter.ISO_DATE)
```

関数型と OO の混在:

```lune
interface Greeter:
    def greet(name: String): String

class FriendlyGreeter(prefix: String) implements Greeter:
    override def greet(name: String): String =
        prefix + ", " + name

def greetAll(greeter: Greeter, names: List[String]): List[String] =
    names.map(fn name -> greeter.greet(name))
```

## 14. コンパイル単位

コンパイラコマンドの仮仕様:

```sh
lune compile src/main.lune -o build/classes
lune run src/main.lune
lune repl
```

## 15. 実装フェーズ

### Phase 0: プロトタイプインタプリタ

- 字句解析、構文解析。
- `let`、リテラル、関数、関数呼び出し。
- 遅延サンクと `force`。
- 基本的な `if`。
- 標準出力用の最小 `IO`。

### Phase 1: 型付きコア

- 基本型。
- 関数型。
- ローカル型推論。
- null 非許容。
- `Option`、`List`。
- パターンマッチ。

### Phase 2: JVM 連携

- Java import。
- Java コンストラクタ呼び出し。
- Java メソッド、static メソッド呼び出し。
- Lune 型と JVM 型の対応。
- JVM バイトコード生成、または Java ソース生成。

### Phase 3: OO 機能

- クラス。
- インターフェース。
- 継承。
- 可視性。
- Java から呼び出せる API 生成。

### Phase 4: 実用化

- モジュールシステムの拡張。
- パッケージ管理。
- formatter。
- LSP。
- テストランナー。
- build tool integration。

## 16. 未決定事項

- デフォルト遅延評価と Java 相互運用の境界をどこまで静的に検査するか。
- `IO` を Haskell 風に厳密に扱うか、Scala/Kotlin 風に軽く扱うか。
- 構文をどこまで ML/Haskell 寄りにするか、どこまで Python/Scala/Kotlin 寄りにするか。
- JVM バイトコードを直接生成するか、Java/Kotlin ソースへトランスパイルするか。
- 型クラスまたは trait 的な抽象を導入するか。
- 部分適用と Java overload resolution をどう整合させるか。
