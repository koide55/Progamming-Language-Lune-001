# Lune 関数型注釈仕様

Version: 0.1 draft  
Related: `LANGUAGE_SPEC.md`, `TYPE_CHECKER_SPEC.md`, `LEXER_PARSER_SPEC.md`

この文書は Lune v0.1 の関数型注釈仕様を定義する。

## 1. 基本方針

Lune の関数型は、部分適用と相性のよいカリー化表記を正規形とする。

```lune
Int -> Int
Int -> Int -> Int
```

`->` は右結合である。

```lune
Int -> Int -> Int
# Int -> (Int -> Int)
```

## 2. 複数引数の糖衣

複数引数関数型は、カリー化された型と同じ意味として扱う。

```lune
(Int, Int) -> Int
```

これは次の糖衣構文である。

```lune
Int -> Int -> Int
```

型表示では正規形に寄せる。

```text
add : Int -> Int -> Int
```

## 3. タプル引数との区別

`(Int, Int) -> Int` は 2 引数関数型であり、タプルを 1 つ受け取る関数型ではない。

タプル引数を 1 つ受け取りたい場合は `Tuple[Int, Int]` を使う。

```lune
Tuple[Int, Int] -> Int
```

## 4. 0 引数関数

```lune
() -> Int
```

は 0 引数関数である。

```lune
Unit -> Int
```

は `Unit` 値を 1 つ受け取る関数であり、`()` とは区別する。

## 5. 注釈例

```lune
let inc: Int -> Int = fn x -> x + 1
let addA: Int -> Int -> Int = fn x y -> x + y
let addB: (Int, Int) -> Int = fn x y -> x + y
```

`addA` と `addB` は同じ型である。

```text
Int -> Int -> Int
```

高階関数:

```lune
def applyTwice(f: Int -> Int, x: Int): Int =
    f(f(x))
```

fold に渡す関数:

```lune
def sumWith(f: Int -> Int -> Int, xs: List[Int]): Int =
    fold(xs, 0, f)
```

## 6. 実行時適用

関数が関数を返し、呼び出し側に引数が残っている場合、残りの引数を返された関数へ続けて適用してよい。

```lune
let add = fn x -> fn y -> x + y
let answer = add(20, 22)
```

この例で `answer` は `42` である。

## 7. 制限

- v0.1 では関数型自体の type params は導入しない。
- 関数型注釈に正格性は含めない。正格性は `def f(!x: Int)` や `fn !x -> ...` の parameter 側で指定する。
- 名前つき引数関数型は導入しない。
