# 第13章 プログラムを組み立てる — ケーススタディ

部品はすべて揃いました。この章では3つの小さなプログラムを、**設計から完成まで通しで**書きます。新しい構文は出てきません。代わりに、これまで別々に学んだ道具がどう噛み合うのかを見ます。

どれも同じ手順で進めます。**型を決める → 骨組みを書く → コンパイラの witness に導かれて埋める → `fmt` と `--check` で仕上げる**。第11章のエラー駆動開発を、実物で3回繰り返すわけです。

## 13.1 テキスト統計 — fold とレコードで1パス集計

K&R の入門書は文字を数えるプログラムから始まります。敬意を表して、単語の統計を作りましょう。

**まず断りを一つ**。v0.1 の文字列には `length` と `+`（連結）しかなく、文字列を単語に分割する道具がありません。そこで入力は「すでに分割された単語のリスト」`List[String]` とします。分割はプログラムの外の仕事、という設計です。

**型を決める**。欲しい結果は「単語数・総文字数・最長の単語」の3つ組。名前を付けて運びたいので、レコードです（第6章）。

```lune
record Stats:
    count: Int
    totalChars: Int
    longest: String
```

**骨組みを書く**。リストを1つの値に畳むのだから `fold`（第8章）。ということは「途中の `Stats` と次の単語から、新しい `Stats` を作る」関数があればいい。`stats.lune`:

```lune
module stats

record Stats:
    count: Int
    totalChars: Int
    longest: String

let empty = Stats(count = 0, totalChars = 0, longest = "")

def step(s: Stats, w: String): Stats =
    let n = length(w)
    let longer = if n > length(s.longest) then w else s.longest
    Stats(count = s.count + 1, totalChars = s.totalChars + n, longest = longer)

def summarize(words: List[String]): Stats =
    fold(words, empty, step)

def averageLength(s: Stats): Double? =
    if s.count == 0 then null else s.totalChars / s.count

let words = ["the", "quick", "brown", "fox", "jumps"]

let summary = summarize(words)

let average = averageLength(summary)

let emptyAverage = averageLength(summarize([]))
```

```console
$ lune --eval summary stats.lune
{ count = 5, totalChars = 21, longest = "quick" }
$ lune --eval average stats.lune
4.2
$ lune --eval emptyAverage stats.lune
null
```

設計上の判断が3つ入っています。

**リストを1回しか歩かない**。3つの統計を別々に計算すれば `fold` を3回書くことになりますが、レコードをアキュムレータにすれば1回で済みます。`fold` の「途中結果」は数値でなくてよい — これが `fold` の本当の使い方です。

**平均を `Double?` にした**。単語が0個のときの平均は存在しません。0 を返すのは嘘なので、`null` を返します（第7章）。呼び出し側は `?? 0.0` で着地するか `match` で場合分けするかを選べます。

**`step` を独立した関数にした**。`fn` で書けばラムダに埋め込めますが、名前を付けておくと REPL で単体で試せます（`step(empty, "hi")`）。テストしたいものには名前を付ける、が実務の勘所です。

## 13.2 家計簿 — ADT・Result・モジュール分割

次はもう少し「業務っぽい」お題です。収入と支出を記録して、残高を出します。

**型を決める**。項目は収入か支出のどちらか — 直和型の出番です（第5章）。データとその操作はモジュールにまとめます（第10章）。`ledger/entry.lune`:

```lune
module ledger.entry

type Entry =
    | Income(label: String, amount: Int)
    | Expense(label: String, amount: Int)

def signedAmount(e: Entry): Int =
    match e:
        | Income(_, amount) -> amount
        | Expense(_, amount) -> 0 - amount

def labelOf(e: Entry): String =
    match e:
        | Income(label, _) -> label
        | Expense(label, _) -> label

def validate(e: Entry): Result[Entry, String] =
    if signedAmount(e) == 0 then Err("amount must not be zero: " + labelOf(e)) else Ok(e)
```

ここが設計の心臓部です。**符号を型で持たない**という判断をしました。`Expense` の `amount` は正の数で持ち、符号は `signedAmount` が付けます。こうすると「支出をマイナスで記録するのか?」という混乱が起きません — 型と関数のどちらに意味を持たせるかの、小さいけれど本質的な選択です。

`validate` は失敗を**値として**返します（第5章）。例外を投げないので、呼び出し側は失敗を無視できません。`ledger_main.lune`:

```lune
module ledger_main
import ledger.entry

let entries = [Income("salary", 3000), Expense("rent", 1200), Expense("food", 400)]

let balance = fold(map(entries, signedAmount), 0, fn a x -> a + x)

let expenses = filter(entries, fn e: Entry -> signedAmount(e) < 0)

let rejected = validate(Expense("zero", 0))

let accepted = validate(Income("bonus", 500))
```

```console
$ lune --eval balance ledger_main.lune
1400
$ lune --eval expenses ledger_main.lune
(Expense("rent", 1200) Expense("food", 400))
$ lune --eval rejected ledger_main.lune
Err("amount must not be zero: zero")
$ lune --eval accepted ledger_main.lune
Ok(Income("bonus", 500))
```

「`map` で符号付き金額に変換して `fold` で畳む」— 第6章の集計パターンがそのまま効いています。`filter` で支出だけ取り出すのも同じ発想です。

**ここで witness の恩恵を体験してください**。`Entry` に3つ目のケース（たとえば `Transfer`）を足してみると、`signedAmount` と `labelOf` の両方で `TYP0007` が出ます。「振替の符号をどうするか決めていない」ことを、コンパイラが漏れなく指摘してくれる — 第11章で学んだとおりです。仕様変更に強い設計とは、こういうことです。

> **v0.1 の注意** — ADT のコンストラクタは**位置引数**で呼びます（`Income("salary", 3000)`）。`Income(label = "salary", amount = 3000)` のように名前付きで書くと `TYP0012` で弾かれます。コンストラクタは部分適用できる（第3章）ので、`Income(amount = 3000)` は「第1引数が未充填の部分適用」を意味することになり、名前を対応させる先がないためです。**名前付きが必須なのはレコード**で、そちらは逆に位置引数が `REC0006` になります（第6章）— この2つはちょうど裏返しの関係です。

## 13.3 数列の実験室 — 無限リストと評価回数の観察

最後は遅延評価の総合演習です。コラッツ数列（偶数なら半分、奇数なら3倍して1を足す。1に到達するまで続く）を無限リストで作ります。

「偶数なら半分」を書くときは割り算の**種類**に注意します。`/` は常に `Double` を返すので（第2章）、`n / 2` では `Int` になりません。整数のまま割るには床除算 `//` を使います。

```text
lune> 7 // 2
3 : Int
lune> 7 / 2
3.5 : Double
```

`collatz.lune`:

```lune
module collatz

# `//` は整数の床除算。`/` は常に Double を返すので、Int のままにするには `//`。
def next(n: Int): Int =
    if n % 2 == 0 then n // 2 else 3 * n + 1

let fromSix = take(iterate(next, 6), 9)

let fromSeven = takeWhile(iterate(next, 7), fn n: Int -> n != 1)
```

```console
$ lune --eval fromSix collatz.lune
(6 3 10 5 16 8 4 2 1)
$ lune --eval fromSeven collatz.lune
(7 22 11 34 17 52 26 13 40 20 10 5 16 8 4 2)
```

`iterate(next, 6)` は「6 から始まる無限のコラッツ列」です（第8章）。何個見るかは使う側が決める — `take` で9個、あるいは `takeWhile` で「1 になる直前まで」。**数列の定義と、どこまで使うかの分離**がここでも効いています。

そして最後に、遅延評価が本当に働いていることを**数値で確かめます**。`tick()`（第4章）を仕込んだ「重い」計算を用意し、5要素のリストから2個だけ取り出したとき、計算が何回走るかを測ります。`counted.lune`:

```lune
module counted

# tick() を仕込んだ「重い」計算。呼ばれた回数がカウンタに残る。
def costly(n: Int): Int =
    seq tick() (n * 2)

let doubled = map([1, 2, 3, 4, 5], costly)

# 先頭 2 個だけを取り、中身まで評価する。
let firstTwo = deepForce take(doubled, 2)

# そのとき costly が何回走ったか。
let cost = seq firstTwo tickCount()
```

```console
$ lune --eval firstTwo counted.lune
(2 4)
$ lune --eval cost counted.lune
2
```

**5要素に `map` したのに、`costly` は2回しか走りませんでした**。正格な言語なら5回走ってから2個を捨てるところです。第4章から追いかけてきた遅延評価の御利益が、ついに数字で出ました。

`deepForce` が必要な理由も味わっておいてください。`take(doubled, 2)` だけでは背骨（`Cons` の連なり）しか実体化せず、要素はサンクのままです — `:trace` で見ると `Cons(<thunk>, <thunk>)` で止まっているのが分かります（第8章の `:thunks` の観察と同じ景色）。「どこまで評価するか」を選べること自体が、Lune の設計思想の現れです。

## 13.4 3つのケースから学ぶこと

3本を並べると、共通の型紙が見えてきます。

1. **形を型にする**（レコードか ADT か — 直積か直和か）
2. **不変な変換で書く**（`map` / `filter` / `fold`。命令的な部品が要るならブロックに閉じ込める）
3. **「ない」「失敗した」を値で表す**（`T?` / `Result` / 単相の結果型）
4. **コンパイラに漏れを見張らせる**（match の網羅性、witness に導かれて埋める）
5. **確かめる道具を自分で作る**（`costly` と `tick()` のように。「速いはず」ではなく数字で確かめる）

そして、どのプログラムも `lune fmt` で整形し、`lune --check` を通してから完成としています（第12章の CI レシピ）。

## 演習問題

**演習 13-1**（★★） `Stats` に「最短の単語」を足してください。空のリストに対しても壊れないように。

<details><summary>解答</summary>

初期値を `""` にすると「最短」が常に空文字列になってしまうので、「まだ無い」を `null` で表します（第7章）。

```lune
record Stats:
    count: Int
    totalChars: Int
    longest: String
    shortest: String?

def pickShortest(current: String?, w: String): String =
    if current == null:
        w
    elif length(w) < length(current):
        w
    else:
        current
```

```console
$ lune --eval summary ex13-1.lune
{ count = 5, totalChars = 21, longest = "quick", shortest = "the" }
```

`pickShortest` の1行目で `current == null` を確かめた後は `current` が `String` に絞り込まれるので、`length(current)` が書けます（第7章の narrowing）。なお 1行形式の `if ... then ... elif` は書けません — `elif` はブロック形式専用です。

</details>

**演習 13-2**（★★） `Entry` に `Transfer(label: String, amount: Int)`（口座間の振替で、残高に影響しない）を足してください。コンパイラが何を要求してくるか観察すること。

<details><summary>解答</summary>

`type` に1行足すだけで、`signedAmount` と `labelOf` の**両方**に `TYP0007`（網羅的でない match）が出ます。`signedAmount` では `| Transfer(_, _) -> 0`（残高に影響しない）、`labelOf` では `| Transfer(label, _) -> label` を足せば通ります。

型を1箇所変えると、影響を受ける全箇所をコンパイラが挙げてくれる — これが `_ -> ...` のワイルドカードを避ける理由です（演習 5-1）。ワイルドカードで書いていたら、`Transfer` は黙って支出扱いになっていたかもしれません。

</details>

**演習 13-3**（★★） `counted.lune` の `take(doubled, 2)` を `take(doubled, 5)` に変えると `cost` はいくつになるでしょう。`deepForce` を外したらどうなるでしょう。予想してから確かめてください。

<details><summary>解答</summary>

`5` になります（5要素すべてを評価するので）。`deepForce` を外すと `cost` は `0` — `take` は背骨だけ実体化し、要素のサンクには触らないからです。「リストがある」ことと「中身が計算済みである」ことは別、という第8章の教訓が数字で確認できます。

</details>

**演習 13-4**（★★★） `-7 // 2` は `-4` になります。`-3` ではありません。なぜそうなるのかを、`-7 % 2` の値と合わせて説明してください。まず予想し、REPL で確かめてから答えること。

<details><summary>解答</summary>

まず両方の値を見ます。

```text
lune> -7 // 2
-4 : Int
lune> -7 % 2
1 : Int
```

`//` の丸めは**負の無限大方向への切り下げ**（floor）で、ゼロ方向への切り捨て（truncation）ではありません。`-7 / 2` は `-3.5` なので、floor すると `-4` になります。

なぜ `-3` ではないのか。`//` と `%` は無関係な2つの演算ではなく、**組で辻褄が合っていなければならない**からです。商と余りの関係は、どんな符号でもこの等式で結ばれています。

```text
a == (a // b) * b + (a % b)
```

確かめてみます。

```text
lune> (-7 // 2) * 2 + (-7 % 2)
-7 : Int
```

もし `//` がゼロ方向切り捨てで `-3` を返したとすると、`%` の側（`1`）はそのままなので:

```text
lune> (-3) * 2 + (-7 % 2)
-5 : Int
```

`-7` に戻りません。つまり `-3` を選ぶと `//` と `%` が互いに矛盾し、「商と余り」と呼べなくなってしまいます。`%` が除数の符号に合わせた余りを返す（`-7 % 2` が `-1` ではなく `1`）と決めた時点で、`//` は floor でなければならないのです。片方だけを見て決められる話ではない、というのがこの演習の眼目です。

コラッツ数列には正の数しか出てこないので、`next` を書く限りこの違いは表に出ません。負の数を割るときに初めて効いてきます。丸め方向は `documents/LANGUAGE_SPEC.md` の 9.1 節に規定があります。

</details>

**演習 13-5**（★★★・総合） 3つのケーススタディのどれかを選んで拡張してください。例: テキスト統計に「n 文字以上の単語だけ」の絞り込みを足す / 家計簿に月ごとの集計を足す（`record Month` と `filter` の組み合わせ）/ コラッツ列の「1 に到達するまでの歩数」を求める関数を書く。

<details><summary>解答</summary>

例として3つ目（歩数）は、`takeWhile` の結果の `length` に1を足せば求められます。

```text
lune> length(takeWhile(iterate(next, 7), fn n: Int -> n != 1)) + 1
17 : Int
```

無限リストに `length` を使っていますが、`takeWhile` が先に有限化しているので止まります（第8章 8.5節）。「無限のまま加工して、有限化してから消費する」— この順序を守れているかが、遅延評価を使いこなせているかの試金石です。

</details>

---

**より正確には** — この章は新しい機能を使っていません。各節が依拠する仕様は、レコードが `documents/RECORD_FIELD_SPEC.md`、ADT と match が `documents/MATCH_EXHAUSTIVENESS_SPEC.md`、リストと遅延コンビネータが `documents/STANDARD_LIBRARY_SPEC.md` §6、`seq`/`deepForce` が `documents/LAZY_EVALUATION_SPEC.md` §9–10。この章のコード例は `books/examples/ch13/` にあり、すべて実際の CLI で検証されています。
