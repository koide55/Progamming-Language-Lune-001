# 第9章 命令的に書く — var・while・for・IO

気づいていたでしょうか。ここまでの8つの章で、あなたは**一度も変数を書き換えていません**。温度換算表も、無限の素数列も、じゃんけんの判定も、すべて「値に名前を付けて、式で組み合わせる」だけで書けました。

それでも、カウンタを回したい場面、途中経過を書き換えたい場面はあります。Lune の答えは現実的です — **命令的な書き方も、小さく使うぶんには良い道具**。この章では可変束縛 `var`、ループ `while` と `for`、出力の置き場所 `IO:` を学びます。合言葉は「**命令はブロックに閉じ込め、外へは値を返す**」です。

## 9.1 ブロック慣用句 — 命令の島

まず Lune 流の「命令的コードの置き方」を見てください。`counter.lune`:

```lune
module counter

# var と while はブロックの中で使い、最後の式で結果を返す。
let answer =
    var i = 0
    var total = 0
    while i < 5:
        total = total + i
        i = i + 1
    total
```

```console
$ lune --eval answer counter.lune
10
```

ブロックの中では変数が書き換わり、ループが回っています。しかし**外から見れば、`answer` はただの `Int`** です。第2章のブロック `let` と同じ形で、最後の式 `total` がブロック全体の値になります。命令的な過程は島の中に閉じ、島の外は今までどおり式の世界 — この形を保つ限り、命令的なコードはプログラムの残りを汚しません。

ついでに第4章の住人として一言: この `let answer = ...` も遅延です。誰かが `answer` を使うまで、ループは一周も回りません。

## 9.2 var — 正格な可変束縛

書き換えられる束縛は `var` で作ります。

```lune
var count = 0
count = count + 1
```

`let` との違いは2つあります。**可変**であること、そして**正格**（束縛した瞬間に右辺を評価する）であることです。`tick()`（第4章）で確かめられます。

```text
lune> var t = tick()
ok
lune> tickCount()
1 : Int
```

束縛しただけでカウンタが進みました — `let` なら 0 のままだったはずです。書き換わる変数の値が「いつ評価されるか分からない」のでは推論できないので、`var` は遅延しない、と覚えてください。

| | `let` | `var` |
| --- | --- | --- |
| 再代入 | 不可（不変） | 可 |
| 評価 | 遅延（使うまで計算しない） | 正格（束縛時に計算する） |

代入できるのは名前だけです。`i = i + 1` と書くほかに、複合代入 `+= -= *= /= //= %=` も使えます（`i += 1` は `i = i + 1` とまったく同じ意味です）。ひとつ落とし穴があって、`/` は常に真の除算なので `Int` の変数への `x /= 2` は型エラーになります（`Double` になってしまうため）。整数を整数のまま割りたいときは、床除算の `x //= 2` を使ってください（`//` は 13.3 節）。

> **v0.1 の既知のバグ** — 実は現在の実装は、**`let` への代入を検査し損ねます**。
>
> ```text
> lune> let a = 1
> ok
> lune> a = 2
> 2 : Int
> lune> a
> 2 : Int
> ```
>
> 不変のはずの `a` が黙って書き換わってしまいました。本来は型エラーになるべき見落としで、修正待ちです。それまでは「**代入してよいのは `var` だけ**」を自分の規約として守ってください。

## 9.3 while — 最小のループ

`while 条件:` は、条件が `Bool` である間ブロックを繰り返します。9.1節の `counter.lune` がすべてです — 条件は**毎周**評価され、`while` 式全体の値は常に `Unit`。つまり `while` は値を作る道具ではなく、`var` を書き換えるための道具です。

`break` と `continue` はありません。途中で抜けたければ、その条件をループ条件に織り込みます（`while i < 5 && not(done):` のように）。それが煩わしくなってきたら、それはたいてい**再帰か `fold` で書くべき合図**です（第3・8章）。

## 9.4 for — リストを歩く

リストの全要素に何かしたいだけなら、`for` が簡潔です。`fortotal.lune`:

```lune
module fortotal

let pairs = [(1, 10), (2, 20)]

# for のパターンには、let と同じく反駁不能なものが書ける。
let total =
    var result = 0
    for (left, right) in pairs:
        result = result + left + right
    result
```

```console
$ lune --eval total fortotal.lune
33
```

`for パターン in リスト:` の形で、パターンには `let` と同じ規則（第5章）が適用されます — タプルのような**反駁不能**なパターンは分解でき、失敗しうるパターンは弾かれます。

```text,diagnostic
lune> for Some(x) in [Some(1), Some(2)]:
...     println(x)
...
error[TYP0008]: for の束縛に反駁可能パターンは使えません: Some(x)
  --> <repl:1>:1:24
  |
1 | for Some(x) in [Some(1), Some(2)]:
  |                        ^^^^ このパターンはマッチに失敗し得る
   = hint: このパターンは None をカバーしていません
   = hint: `match` を使って Option[Int] の全ケースを場合分けしてください
   = help: 詳しくは `lune explain TYP0008 --lang ja` を実行してください
```

走査できるのは `List[T]` だけです。`badfor.lune` のようにリスト以外を渡すと、専用の診断が出ます。

```text,diagnostic
error[TYP0006]: for の対象は List でなければなりませんが、Int でした
  --> badfor.lune:5:14
  |
5 |     for x in 42:
  |              ^^ 走査対象は List[T] でなければならない
   = help: 詳しくは `lune explain TYP0006 --lang ja` を実行してください
```

`for` もまた `Unit` です。そして背骨を1歩ずつ force しながら進むので、**無限リストに `for` すると帰ってきません** — 第8章の「消費し切る道具」の仲間だと思ってください。

## 9.5 IO — 出力と遅延の付き合い方

`println` はこれまで何度も使ってきましたが、遅延の世界には出力ならではの罠があります。見てください。

```text
lune> let p = println("hi")
ok
lune> p
hi
() : Unit
```

`let` の行では**何も出力されません**。`println("hi")` はサンクに包まれ、`p` を使った瞬間に初めて実行されたのです。つまり遅延の世界では、「出力がいつ起きるか」は「値がいつ要るか」で決まる — 画面に順番どおり文字を出したいプログラムにとって、これは困った性質です。

だから出力は **`IO:` ブロックに集めます**。`io.lune`:

```lune
module io

# 出力は IO ブロックに集め、上から順に実行させる。
def report(): Unit =
    IO:
        println("one")
        println("two")

let run = report()
```

```console
$ lune --eval run io.lune
one
two
()
```

`IO:` ブロックの中の文は、ブロックが実行されるとき**上から順に**走ります。「順序が意味を持つ副作用はここにあります」という宣言でもあり、読み手への目印でもあります（v0.1 の `IO:` は型システム上の厳密なエフェクト管理ではなく、この「置き場所」の規約です — 将来仕様では強化が予定されています）。

作法としてはこう覚えてください。**計算は純粋な関数で、出力は IO の中で**。判定ロジックを `String` を返す関数に切り出し、`IO:` の `for` で流し込む — この分離の練習が演習 9-2（FizzBuzz）です。

## 9.6 raise / throw — 最後の手段

実行時エラーを自分で起こす式もあります。

```text,diagnostic
lune> let bad = raise "failed"
ok
lune> bad
error[RUN0006]: failed
   = help: 詳しくは `lune explain RUN0006 --lang ja` を実行してください
```

`raise 式`（同義の `throw` もあります）は評価されると実行時エラーを送出します。例によって `let` は遅延なので、束縛しただけでは何も起きず、使った瞬間に爆発します — `crash()` の自作版だと思えばだいたい正しいです。

そして重要な注意: **`try`/`catch` はありません**。つまり `raise` したエラーをプログラムの中で受け止める方法はないのです。回復可能な失敗は、第5章の単相の結果型や `Result`、第7章の `T?` — **失敗を値として返す**道具で表してください。`raise` の出番は「ここに来たらプログラムを止めるのが正しい」という、本当に例外的な場面だけです。

## まとめ

| 概念 | 一言で |
| --- | --- |
| ブロック慣用句 | 命令的コードは `let 名前 =` のブロックに閉じ、最後の式で値を返す |
| `var` | 可変・**正格**。代入は名前への `=` のみ |
| `while 条件:` | 条件は毎周評価。式全体は `Unit`。break/continue はない |
| `for パターン in リスト:` | `List[T]` 専用（`TYP0006`）。パターンは反駁不能（`TYP0008`） |
| 出力の順序 | 遅延に流されないよう `IO:` ブロックに集めて上から実行 |
| 分離の作法 | 計算は純粋な関数、出力は IO の中 |
| `raise` / `throw` | 受け止める手段はない。回復可能な失敗は値で返す |

## 演習問題

**演習 9-1**（★） `while` で 1 から 10 までの積（10!）を計算してください。

<details><summary>解答</summary>

```lune
module answers

# 演習 9-1: while で 1 から 10 までの積（10!）。
let product =
    var i = 1
    var acc = 1
    while i <= 10:
        acc = acc * i
        i = i + 1
    acc
```

```console
$ lune --eval product ex9-1.lune
3628800
```

</details>

**演習 9-2**（★★） FizzBuzz を書いてください。1〜15 について、3 の倍数なら `Fizz`、5 の倍数なら `Buzz`、両方なら `FizzBuzz`、それ以外は数を1行ずつ出力します。判定と出力を分けること。

<details><summary>解答</summary>

```lune
module answers

# 演習 9-2: FizzBuzz。判定は純粋な関数に、出力は IO の for に分ける。
def fizzbuzz(n: Int): String =
    if n % 15 == 0:
        "FizzBuzz"
    elif n % 3 == 0:
        "Fizz"
    elif n % 5 == 0:
        "Buzz"
    else:
        show(n)

def main(): Unit =
    IO:
        for i in range(1, 16):
            println(fizzbuzz(i))

let run = main()
```

`fizzbuzz` は純粋な関数なので、REPL で単体テストできます（`fizzbuzz(15)` → `"FizzBuzz"`）。出力の都合と判定のロジックが混ざらない — 9.5節の分離の作法です。

</details>

**演習 9-3**（★★） `let t = tick()` と `var v = tick()` を1つずつ定義して、`tickCount()` と併せて `let` と `var` の評価タイミングの違いを説明してください。

<details><summary>解答</summary>

定義直後の `tickCount()` は 1 — 進んだのは `var` の分だけです。`let t` のサンクはまだ眠っていて、`t` を初めて使った瞬間に 2 になります。第4章の `strict let` と同じタイミング、と整理できます（`var` = 可変 + 正格、`strict let` = 不変 + 正格）。

</details>

**演習 9-4**（★★★） 9.1節の `counter.lune`（0〜4 の和）を、`var` もループも使わずに書き直してください。そのうえで、どちらが読みやすいか自分の言葉で論じてください。

<details><summary>解答</summary>

```text
lune> fold(range(0, 5), 0, fn a x -> a + x)
10 : Int
```

1行です。「積み上げる計算」は `fold` の独壇場で、ループ版の4行（カウンタ2本と更新2式）が背負っていた「i と total を取り違えない責任」が消えます。一方、途中で条件により打ち切るような制御は `while` が素直なこともあります。目安: **データを一巡して集計するなら `fold`、状態機械を回すなら `while`**。

</details>

**演習 9-5**（★・逆転問題） `TYP0006` と `TYP0008` を、それぞれ `for` を使った最小のコードで出してください。

<details><summary>解答</summary>

`for x in 42: println(x)`（TYP0006 — 42 は List ではない）と `for Some(x) in [Some(1)]: println(x)`（TYP0008 — Some(x) は失敗しうるパターン）。どちらも本文 9.4 節に実物があります。TYP0008 の hint が第5章の `let` のときと同じ言い回しであることも見ておいてください — `for` の束縛は `let` の親戚です。

</details>

---

**より正確には** — `var` と代入は `documents/LANGUAGE_SPEC.md` §7.3、`while` は `documents/WHILE_LOOP_SPEC.md`、`for` は `documents/FOR_LOOP_SPEC.md`（spine の force 規則も）、`raise`/`throw` と `IO:` は `documents/LANGUAGE_SPEC.md` §9.6–9.7。この章のコード例は `books/examples/ch09/` にあり、すべて実際の CLI で検証されています。
