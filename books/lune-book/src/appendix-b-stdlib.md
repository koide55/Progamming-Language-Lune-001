# 付録B 標準ライブラリリファレンス

prelude（前奏曲）に入っている全 41 個の名前です。`import` は要りません。どのファイルでも
REPL でも、最初から見えています。

いま手元の処理系が何を持っているかは、REPL に聞くのがいちばん確かです。

```console
lune> :env
```

各項目は「型シグネチャ / 一行の説明 / 例」で、リストを扱うものには**無限リストに使えるか**を
付けました。Lune ではこれが実用上いちばん効く区別です（第8章）。

> **表の「無限」列** — ○ は `naturalsFrom(1)` のような終わりのないリストに使っても
> 返ってくるもの、× は最後まで辿ろうとして返ってこないものです。この付録の ○×
> は推測ではなく、実際に無限リストへ適用して確かめた結果です。

型の `[T]` は型変数（どんな型でもよい）を表します。

## B.1 Option — 「あるかもしれない」

| 名前 | 型 | 意味 |
| --- | --- | --- |
| `Some` | `[T] T -> Option[T]` | 値がある形を作る |
| `None` | `Option[T]` | 値がない形 |
| `isSome` | `[T] Option[T] -> Bool` | `Some` かどうか |
| `isNone` | `[T] Option[T] -> Bool` | `None` かどうか |
| `getOrElse` | `[T] Option[T] -> T -> T` | 中身を取り出す。`None` なら第2引数 |
| `optionMap` | `[T, U] Option[T] -> (T -> U) -> Option[U]` | 中身にだけ関数を適用する |

```text
lune> Some(3)
Some(3) : Option[Int]
lune> getOrElse(Some(3), 0)
3 : Int
lune> getOrElse(None, 0)
0 : Int
lune> optionMap(Some(3), fn n: Int -> n * 2)
Some(6) : Option[Int]
```

`Option` は第5章、`null` との使い分けは第7章です。

## B.2 Result — 「成功か失敗か」

| 名前 | 型 | 意味 |
| --- | --- | --- |
| `Ok` | `[T, E] T -> Result[T, E]` | 成功の形を作る |
| `Err` | `[T, E] E -> Result[T, E]` | 失敗の形を作る。中身に理由を入れられる |
| `isOk` | `[T, E] Result[T, E] -> Bool` | 成功かどうか |
| `isErr` | `[T, E] Result[T, E] -> Bool` | 失敗かどうか |
| `unwrapOr` | `[T, E] Result[T, E] -> T -> T` | 成功なら中身、失敗なら第2引数 |
| `resultMap` | `[T, U, E] Result[T, E] -> (T -> U) -> Result[U, E]` | 成功のときだけ関数を適用する |

```text
lune> Err("boom")
Err("boom") : Result[T, String]
lune> unwrapOr(Ok(3), 0)
3 : Int
lune> unwrapOr(Err("boom"), 0)
0 : Int
lune> resultMap(Ok(3), fn n: Int -> n * 2)
Ok(6) : Result[Int, E]
```

`Option` と違い、`Err` は**失敗の理由を運べます**。第5章と、第13章の家計簿の例で使います。

## B.3 List — 基本

| 名前 | 型 | 意味 | 無限 |
| --- | --- | --- | --- |
| `Nil` | `List[T]` | 空リスト | — |
| `Cons` | `[T] T -> List[T] -> List[T]` | 先頭に1つ足す | ○ |
| `head` | `[T] List[T] -> Option[T]` | 先頭。空なら `None` | ○ |
| `tail` | `[T] List[T] -> Option[List[T]]` | 先頭を除いた残り。空なら `None` | ○ |
| `isEmpty` | `[T] List[T] -> Bool` | 空かどうか | ○ |
| `length` | `Any -> Int` | 要素数（文字列にも使える） | **×** |
| `range` | `Int -> Int -> List[Int]` | `range(a, b)` は a 以上 b 未満 | — |
| `map` | `[T, U] List[T] -> (T -> U) -> List[U]` | 各要素に関数を適用する | ○ |
| `filter` | `[T] List[T] -> (T -> Bool) -> List[T]` | 条件を満たす要素だけ残す | ○ |
| `fold` | `[T, U] List[T] -> U -> (U -> T -> U) -> U` | 初期値から畳み込む | **×** |
| `take` | `[T] List[T] -> Int -> List[T]` | 先頭から n 個 | ○ |
| `drop` | `[T] List[T] -> Int -> List[T]` | 先頭 n 個を捨てる | ○ |
| `takeWhile` | `[T] List[T] -> (T -> Bool) -> List[T]` | 条件が続く間だけ取る | ○ |
| `dropWhile` | `[T] List[T] -> (T -> Bool) -> List[T]` | 条件が続く間だけ捨てる | ○ |
| `zip` | `[T, U] List[T] -> List[U] -> List[Tuple[T, U]]` | 2本を組にする。短いほうで終わる | ○ |
| `zipWith` | `[T, U, V] List[T] -> List[U] -> (T -> U -> V) -> List[V]` | 組にしながら関数を適用する | ○ |

```text
lune> let xs = [1, 2, 3]
ok
lune> head(xs)
Some(1) : Option[Int]
lune> tail(xs)
Some((2 3)) : Option[List[Int]]
lune> range(1, 5)
(1 2 3 4) : List[Int]
lune> map(xs, fn n: Int -> n * 2)
(2 4 6) : List[Int]
lune> filter(xs, fn n: Int -> n % 2 == 1)
(1 3) : List[Int]
lune> fold(xs, 0, fn a: Int n: Int -> a + n)
6 : Int
lune> zip(xs, ["a", "b"])
((1, "a") (2, "b")) : List[Tuple[Int, String]]
lune> zipWith(xs, xs, fn a: Int b: Int -> a * b)
(1 4 9) : List[Int]
```

**`length` と `fold` だけが無限リストに使えません。** どちらも「最後まで行く」ことが
仕事だからです。逆に言えば、それ以外は全部安全に使えます — `map` や `filter` を
無限リストに掛けても、実際に計算されるのは後で取り出した分だけです（第4章・第8章）。

範囲外や空に対しては、例外ではなく素直な値が返ります。

```text
lune> take([1, 2, 3], 10)
(1 2 3) : List[Int]
lune> drop([1, 2, 3], 10)
() : List[Int]
lune> range(5, 1)
() : List[Int]
lune> head(Nil)
None : Option[T]
```

## B.4 List — 終わりのないリストを作る

| 名前 | 型 | 意味 |
| --- | --- | --- |
| `naturalsFrom` | `Int -> List[Int]` | n, n+1, n+2, … と続く |
| `iterate` | `[T] (T -> T) -> T -> List[T]` | 初期値に関数を繰り返し適用し続ける |
| `repeat` | `[T] T -> List[T]` | 同じ値が続く |
| `cycle` | `[T] List[T] -> List[T]` | 与えたリストを繰り返し続ける |

```text
lune> take(naturalsFrom(1), 5)
(1 2 3 4 5) : List[Int]
lune> take(iterate(fn n: Int -> n * 2, 1), 5)
(1 2 4 8 16) : List[Int]
lune> take(repeat("x"), 3)
("x" "x" "x") : List[String]
lune> take(cycle([1, 2]), 5)
(1 2 1 2 1) : List[Int]
```

この4つはそれ自体が無限なので、必ず `take` や `takeWhile` で切って使います。第8章。

## B.5 表示と出力

| 名前 | 型 | 意味 |
| --- | --- | --- |
| `show` | `Any -> String` | 値を Lune の表示形式の**文字列にする** |
| `print` | `Any -> Unit` | 表示する（改行なし） |
| `println` | `Any -> Unit` | 表示して改行する |

```text
lune> show(42)
"42" : String
lune> show([1, 2])
"(1 2)" : String
lune> println("hi")
hi
() : Unit
```

`show` は文字列を**返す**だけで、画面には出しません。出すのは `print` / `println` です。
`show("hi")` が `"\"hi\""` になるのは、文字列を表示形式にすると引用符が付くためです。

## B.6 小さな道具

| 名前 | 型 | 意味 |
| --- | --- | --- |
| `id` | `[T] T -> T` | 引数をそのまま返す |
| `const` | `[T, U] T -> U -> T` | 第1引数を返し、第2引数は無視する |
| `not` | `Bool -> Bool` | 真偽を反転する |

```text
lune> id(7)
7 : Int
lune> const(1, 2)
1 : Int
lune> not(true)
false : Bool
```

`const` の第2引数は遅延されたまま**評価されません**。第4章の「使わないものは計算しない」を
1行で確かめられる関数です。

## B.7 観察用のビルトイン

遅延評価の挙動を目で見るための道具で、**安定した標準 API ではありません**
（`STANDARD_LIBRARY_SPEC.md` 8.1 がそう明言しています）。教材とテスト用です。

| 名前 | 型 | 意味 |
| --- | --- | --- |
| `crash` | `() -> Nothing` | 評価されると実行時エラーになる |
| `tick` | `() -> Int` | 呼ばれるたびに内部カウンタを +1 して返す |
| `tickCount` | `() -> Int` | 現在のカウンタ値。カウンタは増やさない |

`crash` は「評価されなければ何も起きない」ことを示すために使います。`tick` は
**何回評価されたか**を数えるためのもので、`let` が遅延することの証拠になります。

```text
lune> let t1 = tick()
ok
lune> let t2 = tick()
ok
lune> tickCount()
0 : Int
```

2回 `tick()` を束縛したのにカウンタが `0` のままです。`let` は遅延するので、
まだ一度も呼ばれていません。`strict let` にすると `2` になります。第4章。

## B.8 `seq` と `deepForce` は関数ではありません

この2つは prelude の関数ではなく、**言語の構文**です（`lazy` や `force` と同じ仲間で、
`:env` にも出てきません）。

```lune
seq a b          # a を評価してから b を返す
deepForce x      # x を中身まで残らず評価する
```

評価の順序と深さを制御する道具として、第4章 4.6 で扱います。

## この付録の出どころ

型シグネチャは REPL の `:env`（＝処理系が持っている実物）から採りました。説明は
`documents/STANDARD_LIBRARY_SPEC.md` に沿っています。「無限」列は、各関数を実際に
`naturalsFrom(1)` へ適用して返ってくるかどうかを確かめた結果です。
