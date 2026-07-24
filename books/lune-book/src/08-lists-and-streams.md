# 第8章 リストとストリーム

第4章の遅延評価が「データ構造の設計」に化ける章です。前半は第1章から使ってきたリストをきちんと学び直します。後半はその同じリストが**無限**になります — 新しい型は登場しません。Lune のリストは、生まれつき無限になれるのです。

## 8.1 リストの正体 — Cons と Nil

`[1, 2, 3]` は糖衣構文です。リストの正体は、プレリュードに定義されたただの ADT — 第5章の道具で書ける、2つのコンストラクタです。

```text
lune> :type Cons
Cons : [T] T -> List[T] -> List[T]
lune> :type Nil
Nil : List[T]
lune> Cons(1, Cons(2, Nil))
(1 2) : List[Int]
```

`Nil` が空リスト、`Cons(先頭, 残り)` が「先頭の値と、残りのリスト」。`[1, 2]` は `Cons(1, Cons(2, Nil))` のことです（`Nil` はプレリュードの `None` と同じく、値として登録されています）。

ここで第4章を思い出してください。**コンストラクタのフィールドはデフォルトで遅延**でした。つまり `Cons` の「残り」は、必要になるまで計算されないサンクです。この一点が、この章の後半のすべてを支えます。

## 8.2 基本の道具 — 開ける・数える・変換する

まず開ける道具。`head`（先頭）と `tail`（残り）は **`Option` を返します**。

```text
lune> head([1, 2, 3])
Some(1) : Option[Int]
lune> head([])
None : Option[T]
lune> tail([1, 2, 3])
Some((2 3)) : Option[List[Int]]
lune> isEmpty([])
true : Bool
```

空リストに先頭はありません。「ないかもしれない」答えを `Option` で返すのは第5章で学んだ設計そのものです。とはいえ、リストを開けるいちばん良い方法は `Option` を剥がすことではなく、**`match` で直接分解する**ことです。8.6節の実例で使います。

変換の道具は第1章以来おなじみの `map` / `filter` / `fold`、それに `take` / `drop` / `range` / `length` です。復習を兼ねて型だけ整理しておきます — すべて「リストが先、道具が後」の引数順です。

| 関数 | 型（要約） | 一言 |
| --- | --- | --- |
| `map(xs, f)` | `List[T] -> (T -> U) -> List[U]` | 全要素に `f` |
| `filter(xs, p)` | `List[T] -> (T -> Bool) -> List[T]` | `p` が真の要素だけ |
| `fold(xs, init, f)` | `List[T] -> U -> ((U, T) -> U) -> U` | 畳み込み |
| `take(xs, n)` / `drop(xs, n)` | | 先頭 `n` 個を取る / 捨てる |
| `head` / `tail` | | `Option` で返す |
| `length` / `isEmpty` / `range` | | 長さ / 空か / 整数列 |

## 8.3 tail は遅延している — リストは無限になれる

本題です。`Cons` の tail はサンクでした。ということは、「残りのリスト」の計算が**永遠に終わらなくても構わない**はずです。プレリュードには、まさにそういうリストを作る関数があります。

```lune
naturalsFrom(n)   # [n, n+1, n+2, ...]
iterate(f, x)     # [x, f(x), f(f(x)), ...]
repeat(x)         # [x, x, x, ...]
cycle(xs)         # xs を無限に繰り返す
```

`:thunks` で、無限リストの中身を覗いてみましょう（`:thunks` は評価を起こさないので、無限リストでも安全です）。

```text
lune> let nat = naturalsFrom(1)
ok
lune> :thunks nat
nat : unevaluated
lune> head(nat)
Some(1) : Option[Int]
lune> :thunks nat
nat : evaluated = Cons(1, <thunk>)
lune> take(nat, 5)
(1 2 3 4 5) : List[Int]
lune> :thunks nat
nat : evaluated = Cons(1, Cons(2, Cons(3, Cons(…))))
```

`Cons(1, <thunk>)` — 先頭の 1 だけが計算され、残り全部は「まだ約束のまま」。`take` で 5 個要求すると、その分だけ評価が進みました。**無限リストとは、必要な分だけ実体化する数列**です。どこまで実体化したかが `:thunks` でそのまま見える — 第4章の観察道具は、ここで最大の見せ場を迎えます。

`take` と組み合わせれば、無限リストは普通の値として扱えます。`infinite.lune`:

```lune
module infinite

# List の tail は遅延している。だからリストは無限になれる。
let firstFive = take(naturalsFrom(1), 5)

let powersOfTwo = take(iterate(fn x: Int -> x * 2, 1), 6)

let threeSevens = take(repeat(7), 3)

let pattern = take(cycle([1, 2, 3]), 7)
```

```console
$ lune --eval powersOfTwo infinite.lune
(1 2 4 8 16 32)
$ lune --eval pattern infinite.lune
(1 2 3 1 2 3 1)
```

## 8.4 遅延コンビネータ — 無限のまま加工する

`map` や `filter` も tail の遅延を保つので、**無限リストを無限リストのまま**加工できます。仕上げに `take` で必要な分だけ受け取ります。

```text
lune> take(map(naturalsFrom(1), fn n: Int -> n * n), 5)
(1 4 9 16 25) : List[Int]
lune> takeWhile(naturalsFrom(1), fn x -> x < 4)
(1 2 3) : List[Int]
lune> take(dropWhile(naturalsFrom(1), fn x -> x < 10), 3)
(10 11 12) : List[Int]
lune> take(zip(naturalsFrom(1), cycle(["a", "b"])), 4)
((1, "a") (2, "b") (3, "a") (4, "b")) : List[Tuple[Int, String]]
lune> take(zipWith(naturalsFrom(1), naturalsFrom(10), fn a: Int b: Int -> a + b), 3)
(11 13 15) : List[Int]
```

- `takeWhile` / `dropWhile` — 条件が続く間だけ取る / 捨てる
- `zip(a, b)` — 2本のリストをタプルの列に束ねる（短い方で止まる）
- `zipWith(a, b, f)` — 束ねながら `f` で合成する

無限どうしを `zip` しても平気です。結果も無限リストになり、使う分しか計算されないからです。

## 8.5 止まらない操作 — 消費し切る関数たち

ただし、道具には「リストを**最後まで**消費するもの」があります。`fold`・`length`・`drop` の仲間です。無限リストに使うと、最後は永遠に来ないので**止まりません**。

```text
lune> length(naturalsFrom(1))
```

これを打つとプロンプトは帰ってきません（Ctrl-C で中断してください）。エラーにならないのがポイントです — 1つずつ数え続けること自体は正しい計算で、終わらないだけなのです。

見分け方は単純です。**答えを出すのに全要素が要るか?** `take`/`map`/`filter`/`takeWhile`/`zip` は要らない（遅延を保つ）。`fold`/`length` は要る（消費し切る）。`filter` にも罠が一つあって、条件を満たす要素が二度と現れないと、次の1個を探して走り続けます。

> **v0.1 の既知のバグ** — 無限リストに `drop` した結果を `take` すると、診断ではなく内部エラー（`error: 'LazyValue' object has no attribute 'fields'`）が出ます（`take(drop(naturalsFrom(1), 1), 3)` で再現）。修正待ちの実装バグです。`dropWhile` は正常なので、当面はそちらを使ってください。

## 8.6 実例集 — 無限リストで考える

**フィボナッチ数列**。「状態 `(a, b)` を `(b, a+b)` に進め続ける」と読めます。`iterate` の出番です。`fib.lune`:

```lune
module fib

# 状態 (a, b) を一歩進める: (0,1) -> (1,1) -> (1,2) -> (2,3) -> ...
def step(p: Tuple[Int, Int]): Tuple[Int, Int] =
    match p:
        | (a, b) -> (b, a + b)

def fst(p: Tuple[Int, Int]): Int =
    let (a, _) = p
    a

# フィボナッチ数列そのもの（無限リスト）。
let fibs = map(iterate(step, (0, 1)), fst)

let first10 = take(fibs, 10)
```

```console
$ lune --eval first10 fib.lune
(0 1 1 2 3 5 8 13 21 34)
```

`fibs` は「10個のフィボナッチ数」ではなく、**フィボナッチ数列そのもの**に付けた名前です。何個使うかは、使う側があとで決める。生成と消費の分離 — 無限リストの設計上の本当の御利益はこれです。

**エラトステネスの篩**。素数の無限リストを作ります。`primes.lune`:

```lune
module primes

# エラトステネスの篩。先頭 p を素数として採り、
# p で割り切れるものを残りから漉して、続きは必要になったら計算する。
def sieve(xs: List[Int]): List[Int] =
    match xs:
        | Cons(p, rest) -> Cons(p, sieve(filter(rest, fn n: Int -> n % p != 0)))
        | Nil -> xs

let primes = sieve(naturalsFrom(2))

let first10 = take(primes, 10)
```

```console
$ lune --eval first10 primes.lune
(2 3 5 7 11 13 17 19 23 29)
```

3行に注目ポイントが詰まっています。

- リストを `match` で直接 `Cons(p, rest)` に分解しています（`head`/`tail` より素直です）。
- 返す `Cons(p, ...)` の第2引数 — 再帰呼び出し `sieve(...)` — は**遅延フィールドに入る**ので、無限の再帰なのに止まりません。次の素数は、誰かが要求したときに初めて漉されます。
- `| Nil -> xs` は第5章の既知の制限への実戦的な回避です。裸の `Nil` を返すと型変数が確定できないので、「空リストならその空リスト自身を返す」ことで型を `List[Int]` に保っています。

> **壊してみよう** — `take` の引数順を間違えると、型がすぐに教えてくれます。
>
> ```text,diagnostic
> lune> take(5, naturalsFrom(1))
> error[TYP0003]: expected List[T], got Int
>    = help: run `lune explain TYP0003` for a detailed explanation
> ```
>
> リストが先、個数が後。「リスト系の関数はリストが第1引数」という規約（8.2節の表）を思い出してください。

## まとめ

| 概念 | 一言で |
| --- | --- |
| `Cons` / `Nil` | リストの正体。`[1, 2]` は `Cons(1, Cons(2, Nil))` |
| tail の遅延 | 「残り」はサンク。だからリストは無限になれる |
| `head` / `tail` | `Option` を返す。分解するなら `match` で `Cons(x, rest)` |
| `naturalsFrom` / `iterate` / `repeat` / `cycle` | 無限リストの作り方4種 |
| 遅延を保つ道具 | `take` / `map` / `filter` / `takeWhile` / `dropWhile` / `zip` / `zipWith` |
| 消費し切る道具 | `fold` / `length` / `drop` — 無限リストには使わない |
| 観察 | `:thunks` は評価せずに「どこまで実体化したか」を見せる |

## 演習問題

**演習 8-1**（★） 結果を予想してから確かめてください。

```text
take(cycle([1, 2]), 5)
takeWhile(naturalsFrom(1), fn x -> x < 4)
take(zip(naturalsFrom(1), cycle(["a", "b"])), 4)
```

<details><summary>解答</summary>

`(1 2 1 2 1)`、`(1 2 3)`、`((1, "a") (2, "b") (3, "a") (4, "b"))`。3つ目は「無限の番号列」と「無限の交互パターン」の zip — どちらも終わらないリストですが、4個しか要求していないので4個分しか計算されません。

</details>

**演習 8-2**（★★） 平方数（1, 4, 9, 16, ...）の無限リストを作り、そのうち**偶数のものだけ**を先頭から5個取り出してください。

<details><summary>解答</summary>

```lune
module answers

# 演習 8-2: 平方数の無限リストから、偶数のものだけを 5 個。
let squares = map(naturalsFrom(1), fn n: Int -> n * n)

let evenSquares = take(filter(squares, fn s: Int -> s % 2 == 0), 5)
```

```console
$ lune --eval evenSquares ex8-2.lune
(4 16 36 64 100)
```

`map` → `filter` → `take` と、無限のまま2段加工してから収穫しています。

</details>

**演習 8-3**（★★） センサーの読み `[1, 4, 7, 10]` について、隣どうしの平均（移動平均）`(2.5 5.5 8.5)` を計算してください。ヒント: リストを1つずらして自分自身と `zipWith`。

<details><summary>解答</summary>

```lune
module answers

# 演習 8-3: 隣どうしの平均（移動平均）。リストを 1 つずらして自分と zip する。
let readings = [1, 4, 7, 10]

let smoothed = zipWith(readings, drop(readings, 1), fn a: Int b: Int -> (a + b) / 2)
```

```console
$ lune --eval smoothed ex8-3.lune
(2.5 5.5 8.5)
```

`zipWith` が短い方（`drop` した側）で止まるので、端の処理を書く必要がありません。

</details>

**演習 8-4**（★★★） リュカ数列（2, 1, 3, 4, 7, ... — フィボナッチと同じ漸化式で、始まりが `(2, 1)`）の無限リストを作り、先頭10個を取り出してください。

<details><summary>解答</summary>

```lune
module answers

# 演習 8-4: リュカ数列。フィボナッチと同じ漸化式で、種だけ (2, 1) に変える。
def step(p: Tuple[Int, Int]): Tuple[Int, Int] =
    match p:
        | (a, b) -> (b, a + b)

def fst(p: Tuple[Int, Int]): Int =
    let (a, _) = p
    a

let lucas = map(iterate(step, (2, 1)), fst)

let first10 = take(lucas, 10)
```

```console
$ lune --eval first10 ex8-4.lune
(2 1 3 4 7 11 18 29 47 76)
```

`fib.lune` との差は `iterate` の種だけ。「漸化式＝`step` 関数、数列＝`iterate`」という対応が掴めれば、この形はどんな漸化式にも使えます。

</details>

**演習 8-5**（★・逆転問題） 「止まらない式」を1つ書いてください。実行はしなくて構いません（するなら Ctrl-C の準備を）。なぜ止まらないのか、8.5節の言葉で説明してください。

<details><summary>解答</summary>

例: `length(naturalsFrom(1))`、`fold(repeat(1), 0, fn a x -> a + x)`、あるいは `takeWhile(naturalsFrom(1), fn x -> x > 0)`（条件が永遠に真）。どれも「答えを出すために全要素が要る」計算です。少し意地悪な例は `head(filter(naturalsFrom(1), fn x -> x < 0))` — `filter` 自体は遅延を保ちますが、最初の1個が永遠に見つかりません。

</details>

---

**より正確には** — `Cons` の遅延フィールドと各関数の遅延特性（どこまで force するか）は `documents/STANDARD_LIBRARY_SPEC.md` §6 に関数ごとに明記されています。`take(list, 0)` が `list` を評価しないことまで仕様です。この章のコード例は `books/examples/ch08/` にあり、すべて実際の CLI で検証されています。
