# Lune 型チェッカ仕様

Version: 0.1 draft  
Related: `LANGUAGE_SPEC.md`, `SYNTAX_SPEC.md`, `LEXER_PARSER_SPEC.md`, `STANDARD_LIBRARY_SPEC.md`, `RECORD_FIELD_SPEC.md`, `WHILE_LOOP_SPEC.md`

この文書は Lune v0.1 の型チェッカ実装範囲を定義する。

## 1. 方針

v0.1 型チェッカは、完全な Hindley-Milner 型推論ではなく、明示型注釈を軸にした小さな単一化ベースの検査器である。

目標:

- 既存 parser/evaluator が扱える構文を静的に検査する。
- 関数引数と戻り値の型注釈を検査する。
- ADT と `match` の基本的な型整合性を検査する。
- ジェネリック関数とジェネリックコンストラクタの呼び出しで型変数を単一化する。

## 2. v0.1 の型

基本型:

```text
Int
Bool
Double
String
Char
Unit
Any
Nothing
```

複合型:

```text
Option[Int]
Lazy[Int]
IO[String]
Tuple[Int, String]
```

関数型は内部表現として持つが、表面構文の関数型注釈は v0.1 では限定対応とする。

## 3. 型環境

型環境は以下を保持する。

- 値名から型への対応。
- コンストラクタ名からコンストラクタ型への対応。
- 型名から型定義への対応。

import された Java/外部名は v0.1 では `Any` として扱う。

標準ライブラリの型は `STANDARD_LIBRARY_SPEC.md` に従って初期環境へ登録する。

## 4. 関数

関数引数には型注釈が必要である。

```lune
def add(x: Int, y: Int): Int =
    x + y
```

戻り値型がある場合、関数本体の型が戻り値型に代入可能でなければならない。

## 5. let

型注釈あり:

```lune
let answer: Int = 42
```

右辺の型が注釈に代入可能か検査する。

型注釈なし:

```lune
let answer = 42
```

右辺から型を推論して束縛する。

## 6. ADT とコンストラクタ

```lune
type Option[T] =
    | Some(value: T)
    | None
```

この定義から、次のコンストラクタ型を作る。

```text
Some: [T] (T) -> Option[T]
None: [T] () -> Option[T]
```

コンストラクタ呼び出しでは実引数から型変数を単一化する。

## 7. 部分適用

関数呼び出しで渡された引数が関数の arity より少ない場合、typechecker は残り引数を受け取る関数型を返す。

```lune
let add = fn x: Int y: Int -> x + y
let inc = add(1)
```

型:

```text
add: Int -> Int -> Int
inc: Int -> Int
```

コンストラクタにも同じ規則を適用する。

```lune
type Pair =
    | Pair(left: Int, right: Int)

let withOne = Pair(1)
```

型:

```text
Pair: Int -> Int -> Pair
withOne: Int -> Pair
```

arity より多い引数を渡した場合は型エラーにする。

## 7.1 関数型注釈

関数型注釈は `FUNCTION_TYPE_SPEC.md` に従う。

```lune
let addA: Int -> Int -> Int = fn x y -> x + y
let addB: (Int, Int) -> Int = fn x y -> x + y
```

`addA` と `addB` は同じ型であり、表示は正規形に寄せる。

```text
Int -> Int -> Int
```

## 8. match

`match` は scrutinee 型と各パターンの整合性を検査する。

```lune
match option:
    | Some(value) -> value
    | None -> defaultValue
```

コンストラクタパターンは、scrutinee 型とコンストラクタ結果型を単一化し、フィールド型をパターン変数へ束縛する。

各分岐の結果型は一致する必要がある。`Nothing` は任意の分岐型に合流できる。

## 9. Lazy

```lune
let delayed = lazy (1 + 2)
```

`lazy expr` の型は `Lazy[T]` である。

```lune
let value = force delayed
```

`force Lazy[T]` の型は `T` である。v0.1 では `force T` も `T` として許容する。

## 10. while

`while` の条件式は `Bool` でなければならない。

```lune
let loop =
    var i = 0
    while i < 3:
        i = i + 1
```

body は型チェックされるが、body の結果型は捨てられる。`while` 式全体の型は `Unit` である。

## 11. for

`for` の iterable は `List[T]` でなければならない。

```lune
let loop =
    for x in range(1, 4):
        println(x)
```

この例では `x` は `Int` として body 内に束縛される。

`for` の pattern は要素型 `T` に対して型チェックされる。

```lune
for (left, right) in pairs:
    left + right
```

body は型チェックされるが、body の結果型は捨てられる。`for` 式全体の型は `Unit` である。

## 12. リストリテラル

空リスト `[]` は `List[Any]` として推論する。型注釈がある場合は、その型に代入できる。

```lune
let empty: List[Int] = []
```

非空リストは要素型の共通型 `T` から `List[T]` として推論する。

```lune
let numbers = [1, 2, 3]  # List[Int]
```

要素型が一致しない場合は型エラーである。

```lune
let bad = [1, true]
```

## 13. Any

`Any` は v0.1 の逃げ道である。

以下は `Any` になることがある。

- 外部 import。
- 外部 import 由来のメンバー呼び出し。
- 未注釈ラムダ引数。

`Any` は任意の型に代入可能として扱う。これは実用上の暫定措置であり、将来の型チェッカでは段階的に狭める。

## 12. v0.1 の制限

- 完全なローカル型推論は未実装。
- 関数型注釈の本格検査は未実装。
- exhaustiveness check は未実装。
- Java 型の実解決は未実装。
- class/interface の型検査は未実装。
- record update / record pattern / mutable record field は未実装。record の追加仕様は `RECORD_FIELD_SPEC.md` に定義する。
- 型エラーのソース位置表示は未実装。
