# 第3章 関数

第1章から `def` を使ってきましたが、この章で関数を正面から扱います。目標は一つ、**関数は値である**という感覚を手に入れることです。関数が値なら、変数に入れられ、引数として渡せ、戻り値として返せます。ここから Lune のプログラムは急に伸び伸びし始めます。

## 3.1 def — 定義の解剖

まず復習を兼ねて、部品の名前を確認します。

```lune
def add(x: Int, y: Int): Int =
    x + y
```

`add` が関数名、`x: Int, y: Int` が引数とその型、2つ目の `Int` が戻り値の型、`=` の後のインデントされた部分が本体です。本体は式で、その値がそのまま戻り値になります（`return` はありません — 第2章で見たとおり、`if` も含めてすべてが式だからです）。

引数と戻り値の型は書いてください。v0.1 でも省略できる場面はありますが、書かないと推論が `Any` に落ちて警告が出たり（`TYP0010`、3.3節）、再帰関数ではエラーになったり（`TYP0011`、3.7節）します。何より、型は関数の**看板**です。

## 3.2 関数は値である

定義した関数は、整数や文字列と同じように扱えます。たとえば別の名前に束縛できます。

```text
lune> def inc(n: Int): Int =
...     n + 1
...
ok
lune> let renamed = inc
ok
lune> renamed(41)
42 : Int
```

値である以上、型があります。関数の型は `->` で書きます。

```lune
let inc: Int -> Int = fn x -> x + 1
let addA: Int -> Int -> Int = fn x y -> x + y
let addB: (Int, Int) -> Int = fn x y -> x + y
```

`Int -> Int` は「`Int` を受け取り `Int` を返す」。2引数は `Int -> Int -> Int` とも `(Int, Int) -> Int` とも書けます。`->` は右結合なので、前者は `Int -> (Int -> Int)` — 「`Int` を受け取ると、`Int -> Int` を返す」と読めます。この読み方が 3.5 節の部分適用にそのままつながります。

第1章から使ってきた `map` の型を REPL に聞いてみましょう。

```text
lune> :type map
map : [T, U] List[T] -> (T -> U) -> List[U]
```

先頭の `[T, U]` は「任意の型 `T`, `U` について」という宣言です（ジェネリクス、第5章）。読み下すと「`T` のリストと、`T` を `U` にする関数を受け取り、`U` のリストを返す」。型シグネチャは関数の説明文としてかなり優秀です。

## 3.3 ラムダ — 名前のない関数

`fn 引数 -> 式` で、その場で関数を作れます。

```lune
fn x -> x + 1          # 1引数
fn x y -> x + y        # 2引数（並べるだけ）
fn -> 42               # 0引数
fn x: Int -> x * 2     # 型注釈付き
```

引数の型注釈は、**文脈から分かるときは省略できます**。`map` や `applyTwice`（次節）の引数として渡すときは、受け取る側の型が期待を伝えてくれるからです。第1章の `map(range(1, 6), fn x -> x * 2)` で警告が出なかったのはこのためです。

文脈がない場所では、推論のしようがありません。

```text
lune> let f = fn x -> x * 2
warning[TYP0010]: 引数 x の型を推論できません
  --> <repl:19>:1:12
  |
1 | let f = fn x -> x * 2
  |            ^ 引数の型が Any にフォールバックする
   = hint: 型注釈を追加してください。例: `fn x: Int -> ...`
   = help: 詳しくは `lune explain TYP0010 --lang ja` を実行してください
ok
```

`error` ではなく `warning` です — 束縛は成立し、`x` の型は `Any` に落ちます。動きはしますが型検査の保護が薄くなるので、hint のとおり `fn x: Int -> x * 2` と書くのが習慣です。

## 3.4 高階関数

関数を受け取る関数、返す関数を**高階関数**と呼びます。どちらも普通に書けます。`hof.lune`:

```lune
module hof

def inc(n: Int): Int =
    n + 1

# 関数を受け取る関数。
def applyTwice(f: Int -> Int, x: Int): Int =
    f(f(x))

# 関数を返す関数。
def adder(n: Int): Int -> Int =
    fn x -> x + n

let fortyTwo = applyTwice(inc, 40)

let seven = adder(3)(4)
```

```console
$ lune --eval fortyTwo hof.lune
42
$ lune --eval seven hof.lune
7
```

REPL で遊ぶとこうなります。

```text
lune> applyTwice(fn x -> x * 10, 4)
400 : Int
lune> adder(3)(4)
7 : Int
```

`adder(3)` が返すラムダ `fn x -> x + n` は、作られたときの `n = 3` を**覚えています**。関数が定義時の環境を閉じ込めて持ち歩く — これを**クロージャ**といいます。第4章のサンクが「式と環境」の包みだったのと同じ仕掛けで、Lune の世界は「式＋環境」でできています。

## 3.5 部分適用 — 引数は途中まで渡してよい

第1章の演習で、1引数の関数を `greet()` と0引数で呼んでも型エラーにならない、という不思議を見ました。種明かしがこの節です。

Lune では、**引数が足りない呼び出しはエラーではなく、「残りの引数を待つ関数」を返します**。

```text
lune> def add(x: Int, y: Int): Int =
...     x + y
...
ok
lune> let plusTen = add(10)
ok
lune> :type plusTen
plusTen : Int -> Int
lune> plusTen(32)
42 : Int
```

`add : Int -> Int -> Int` を「`Int` を渡すと `Int -> Int` が返る」と読んだのを思い出してください。`add(10)` はその読み方どおりのことをしただけです。まとめて `add(10, 32)` と渡しても、分けて `add(10)(32)` と渡しても同じ — この柔軟さのおかげで、「既存の関数の引数を一部固定した道具」が一行で作れます。

```text
lune> map([1, 2, 3], plusTen)
(11 12 13) : List[Int]
```

なお、渡し**すぎ**は今までどおりエラーです（`TYP0005`、「引数は**最大** 1 個」という言い回しの理由がこれで分かりますね）。また、部分適用で渡した引数も通常の呼び出しと同じくサンクとして捕まります — 遅延評価は部分適用の中でも一貫しています。

## 3.6 パイプライン |> — データの流れを書く

関数適用が入れ子になると、読み順が実行順と逆になります。`double(inc(inc(5)))` は「5 を inc して、inc して、double する」のに、字面は逆から読まないといけません。**パイプライン演算子** `|>` はこれを直します。`x |> f` は `f(x)` の糖衣です。

```text
lune> 5 |> inc
6 : Int
lune> 5 |> inc |> double
12 : Int
```

左から右へ、データが変換を通り抜けていく順に読めます。さらに、多引数関数へパイプすると**部分適用**になります。`pipeline.lune`:

```lune
module pipeline

def inc(n: Int): Int =
    n + 1

def double(n: Int): Int =
    n * 2

def add(x: Int, y: Int): Int =
    x + y

# x |> f は f(x) の糖衣。左から右へ、データの流れの順に読める。
let result = 5 |> inc |> double

# 多引数関数へのパイプは部分適用になる。
let addFive = 5 |> add

let eleven = addFive(6)
```

```console
$ lune --eval result pipeline.lune
12
$ lune --eval eleven pipeline.lune
11
```

パイプラインは「変換の手順書」を書くための構文です。第8章でリスト処理と組み合わせると本領を発揮します。

## 3.7 再帰

関数が自分自身を呼ぶ — ループの関数型的な書き方です。フィボナッチ数で見ましょう。

```lune
def fib(n: Int): Int =
    if n <= 1 then n else fib(n - 1) + fib(n - 2)
```

```text
lune> fib(10)
55 : Int
```

再帰関数には約束が一つあります。**戻り値の型を書くこと**。書かないとどうなるか、`norettype.lune` で確かめます。

```lune
module bad

def fact(n: Int) =
    if n == 0 then 1 else n * fact(n - 1)
```

```console
$ lune --check norettype.lune
```

```text,diagnostic
error[TYP0011]: 再帰関数には戻り値型の注釈が必要です: fact
  --> norettype.lune:3:1
  |
3 | def fact(n: Int) =
  | ^^^ 型が確定する前に関数が自分自身を呼んでいる
   = hint: 戻り値型を追加してください。例: `def fact(...): T = ...`
   = help: 詳しくは `lune explain TYP0011 --lang ja` を実行してください
```

理由も診断が教えてくれています。本体の型を推論し終わる前に `fact(n - 1)` が現れるので、型検査は `fact` の型を先に知っておく必要があるのです。第4章で見たとおり、再帰していいのは関数だけ（値の再帰は `RUN0005`）、そして再帰関数には型の看板が必須 — この2つで再帰は安全に使えます。

書き方のコツを一つ: **停止条件を先に書く**。`if n == 0 then ... else 再帰` の形をまず作ってから、再帰の側を埋めると、無限再帰を書きにくくなります。

> **壊してみよう** — 関数でない値を呼び出すと、専用の診断が出ます。
>
> ```text,diagnostic
> lune> let x = 42
> ok
> lune> x(1)
> error[TYP0004]: 呼び出せない値です: Int
>   --> <repl:21>:1:20
>   |
> 1 | x(1)
>   |                    ^ この値は呼び出せない
>    = help: 詳しくは `lune explain TYP0004 --lang ja` を実行してください
> ```
>
> 「`Int` は呼べない」— 括弧の付けすぎ（`f(x)(y)` のつもりが `f(x, y)` だった、の逆）で出会うことが多い診断です。

## まとめ

| 概念 | 一言で |
| --- | --- |
| `def f(x: T): U = 本体` | 関数定義。型は看板、再帰なら戻り値型は必須 |
| 関数型 | `Int -> Int`。`->` は右結合で、部分適用の読み方と一致 |
| `fn x -> 式` | ラムダ。文脈があれば型注釈は省略可、なければ `TYP0010` |
| 高階関数 | 関数を受け取る/返す関数。返したラムダは環境を覚える（クロージャ） |
| 部分適用 | 引数が足りない呼び出しは「残りを待つ関数」 |
| `x \|> f` | `f(x)` の糖衣。多引数関数へは部分適用 |
| `:type f` | 関数の型を確認する習慣 |

## 演習問題

**演習 3-1**（★） `double(inc(inc(5)))` をパイプラインに書き換えてください（`inc`・`double` は本文のもの）。

<details><summary>解答</summary>

```text
lune> 5 |> inc |> inc |> double
14 : Int
```

`double(inc(inc(5)))` も `14 : Int`。同じ計算ですが、パイプ版は実行の順（5 → +1 → +1 → ×2）のまま読めます。

</details>

**演習 3-2**（★★） 2つの関数を合成する `compose` を書いてください。`compose(f, g)` は「`g` を適用してから `f` を適用する」1つの関数を返すものとします。

<details><summary>解答</summary>

```lune
module answers

# 演習 3-2: 関数合成。compose(f, g) は「g してから f」。
def compose(f: Int -> Int, g: Int -> Int): Int -> Int =
    fn x -> f(g(x))

def inc(n: Int): Int =
    n + 1

def double(n: Int): Int =
    n * 2

let incThenDouble = compose(double, inc)

let answer = incThenDouble(5)
```

```console
$ lune --eval answer ex3-2.lune
12
```

返すラムダが `f` と `g` を覚えている — クロージャ（3.4節）の練習でもあります。

</details>

**演習 3-3**（★★） `fib` を自分で書いて `fib(10)` を確かめてください。そのあと戻り値型 `: Int` を消して、どの診断が出るか予想してから `--check` してください。

<details><summary>解答</summary>

```lune
module answers

# 演習 3-3: 再帰でフィボナッチ数。戻り値型 Int は必須（TYP0011）。
def fib(n: Int): Int =
    if n <= 1 then n else fib(n - 1) + fib(n - 2)

let answer = fib(10)
```

```console
$ lune --eval answer ex3-3.lune
55
```

戻り値型を消すと `TYP0011`（3.7節と同じ診断）が出ます。

</details>

**演習 3-4**（★★★） `applyTwice` を一般化して、関数 `f` を `n` 回適用する `applyN(f, n, x)` を書いてください。`applyN(double, 3, 1)` が `8` になれば正解です。

<details><summary>解答</summary>

```lune
module answers

# 演習 3-4: applyTwice の一般化。f を n 回適用する。
def applyN(f: Int -> Int, n: Int, x: Int): Int =
    if n == 0 then x else applyN(f, n - 1, f(x))

def double(n: Int): Int =
    n * 2

let answer = applyN(double, 3, 1)
```

```console
$ lune --eval answer ex3-4.lune
8
```

高階関数と再帰の合わせ技です。停止条件（`n == 0` なら `x` をそのまま返す）を先に書き、再帰側では「1回適用して、残り回数を減らす」と読めるようにします。

</details>

**演習 3-5**（★・逆転問題） `TYP0004`（呼び出せない値です）を出す最小のコードを書いてください。

<details><summary>解答</summary>

最小は `42(1)` です（`error[TYP0004]: 呼び出せない値です: Int`）。数値・文字列・タプルなど、関数でない値に `(...)` を付ければ出ます。逆に `greet()` のような**引数不足**が `TYP0004` にも `TYP0005` にもならない理由を説明できれば、この章は卒業です。

</details>

---

**より正確には** — 関数定義・ラムダ・部分適用は `documents/LANGUAGE_SPEC.md` §8、関数型の構文は `documents/FUNCTION_TYPE_SPEC.md`、部分適用と遅延の関係は `documents/LAZY_EVALUATION_SPEC.md` §7、ラムダの型推論は `documents/LOCAL_TYPE_INFERENCE_SPEC.md`。この章のコード例は `books/examples/ch03/` にあり、すべて実際の CLI で検証されています。
