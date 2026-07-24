# 第1章 やさしい入門

新しいプログラミング言語を身につける方法は、昔からひとつしかありません。それでプログラムを書くことです。この章では、Lune のプログラムを書いて、動かして、壊してみます。細かい規則の説明はあとの章に任せて、まず言語の全体を1周しましょう。

ひとつだけ、この本の流儀を先に伝えておきます。**エラーを恐れないでください**。Lune のコンパイラは、エラーを「失敗の通知」ではなく「教材」として設計されています。この章の後半では、わざとエラーを起こして、コンパイラに教わる練習をします。

## 1.1 REPL で計算する

Lune には REPL（対話環境）があります。式を打ち込むと、その場で評価して結果を返してくれます。まずはここから始めましょう。

```console
$ lune --repl
Lune v0.1 REPL. Type :help or :quit.
lune>
```

> **表記について** — この本では、シェルのコマンドは `$` で、REPL への入力は `lune>` で示します。`lune` コマンドは、リポジトリの `./bin/lune` に日本語診断オプションを付けた **`./bin/lune --lang ja`** を指します（`alias lune='./bin/lune --lang ja'` としておくと本書のとおりに打てます）。エラーを母語で読めるのは Lune の看板機能で、本書の診断表示はすべて日本語です。REPL は `lune --repl` で起動します。

数を打ち込んでみます。

```text
lune> 1 + 2
3 : Int
lune> 40 + 2
42 : Int
```

結果は `値 : 型` の形で表示されます。`3` が値、`Int` が型です。Lune ではすべての式が型を持ち、REPL はそれをいつも教えてくれます。

文字列は `"` で囲みます。`+` でつなげられます。

```text
lune> "hello, " + "world"
"hello, world" : String
```

REPL を抜けるには `:quit`（または `:q`）です。

```text
lune> :quit
bye
```

`:help` でコマンドの一覧が見られます。REPL は本書全体を通して最良の実験室です。疑問がわいたら、いつでも打ち込んで確かめてください。

## 1.2 let で名前を付ける

値に名前を付けるには `let` を使います。

```text
lune> let x = 41
ok
lune> x + 1
42 : Int
```

宣言に対して REPL は `ok` とだけ答えます。値が表示されないことに注意してください。これは手抜きではありません。**Lune の `let` は、名前を付けた時点ではまだ計算をしていない**のです。

> **予告: 計算はまだ起きていない** — REPL の `:thunks` コマンドを使うと、束縛が評価済みかどうかを（評価を起こさずに）覗けます。
>
> ```text
> lune> let x = 1 + 1
> ok
> lune> :thunks x
> x : unevaluated
> lune> x
> 2 : Int
> lune> :thunks x
> x : evaluated = 2
> ```
>
> `1 + 1` は、`x` を使った瞬間に初めて計算されました。これが **遅延評価** — Lune の設計の心臓部です。第4章でじっくり扱います。いまは「`let` は計算の約束を書くもの」とだけ覚えて先へ進んでください。

## 1.3 プログラムをファイルに書く

REPL は実験室ですが、プログラムはファイルに書いて残します。エディタで `hello.lune` を作ってください。

```lune
module hello

def greet(name: String): String =
    "hello, " + name

let main = println(greet("world"))
```

上から順に読みます。

- `module hello` — このファイルがモジュール `hello` であることを宣言します。Lune のソースファイルは必ずこの宣言から始まります。
- `def greet(name: String): String = ...` — 関数定義です。引数 `name` の型が `String`、戻り値の型も `String`。本体はインデントして書きます。
- `let main = println(greet("world"))` — トップレベルの束縛です。`println` は値を表示する組み込み関数です。

まず、型が合っているかだけを検査してみます。

```console
$ lune --check hello.lune
type check OK
```

次に実行します。Lune v0.1 の実行モデルは「**トップレベルの束縛をひとつ選んで評価する**」です。`--eval` に束縛の名前を渡します。

```console
$ lune --eval main hello.lune
hello, world
()
```

2行表示されました。1行目は `println` が出力した文字列です。2行目の `()` は `main` 自体の値 — `println` の戻り値である `Unit` 値です（`--eval` は評価した束縛の値を最後に表示します）。

`println` は `String` を**生の内容のまま**出力します。引用符は付かず、`"a\nb"` のようなエスケープは実際の改行として出力されます。一方、`String` 以外の値は Lune の標準表示形式（`show` 形式）で表示されます。文字列を引用符付きの `show` 形式で表示したいときは `println(show(value))` と書きます。表示の規則は第2章で整理します。

## 1.4 if は式である

Lune の `if` は、値を返す**式**です。C や Python の「文」の感覚とは少し違います。

```text
lune> if 5 > 3 then "big" else "small"
"big" : String
```

式なので、結果をそのまま `let` に束縛したり、関数の本体にしたりできます。値が要る場面では `else` を省略できません — 条件が偽のときの値がなくなってしまうからです。

本体が長くなるときは、ブロック形も使えます。REPL は行末が `=` や `:` で終わると継続入力になります（`...` が継続のプロンプトです。空行で確定します）。

```text
lune> def abs(x: Int): Int =
...     if x < 0:
...         -x
...     else:
...         x
...
ok
lune> abs(-5)
5 : Int
```

## 1.5 リストで遊ぶ — 温度換算表

C の入門書は、伝統的に華氏-摂氏の温度換算表を最初に作ります。敬意を表して、この本でも作りましょう。ただし Lune 流に — ループの代わりに**リスト**で。

リストは `[` `]` で書きます。表示は Lisp 風の `( )` 区切りです。

```text
lune> [1, 2, 3]
(1 2 3) : List[Int]
lune> range(0, 5)
(0 1 2 3 4) : List[Int]
```

`range(start, end)` は `start` 以上 `end` 未満の整数リストを作ります。リストを加工する基本の道具は 3 つ、`map`（全要素に関数を適用）、`filter`（条件を満たす要素だけ残す）、`fold`（畳み込んで 1 つの値にする）です。

```text
lune> map(range(1, 6), fn x -> x * 2)
(2 4 6 8 10) : List[Int]
lune> filter(range(1, 10), fn x -> x % 2 == 0)
(2 4 6 8) : List[Int]
lune> fold([1, 2, 3, 4], 0, fn acc x -> acc + x)
10 : Int
```

`fn x -> x * 2` は名前のない小さな関数（ラムダ）です。引数の型を書いていないのに動くのは、`map` が期待する型からコンパイラが推論してくれるからです（第3章）。

道具が揃いました。温度換算表を作ります。ファイル `temperature.lune`:

```lune
module temperature

# 華氏 0〜300 度を 20 度刻みで摂氏に換算した対応表を作る。
def toCelsius(f: Int): Double =
    (f - 32) * 5 / 9

let fahrenheits = map(range(0, 16), fn i -> i * 20)

let table = map(fahrenheits, fn f -> (f, toCelsius(f)))
```

`#` から行末まではコメントです。`toCelsius` の戻り値が `Double` になっているのは、Lune の `/` が**常に `Double` を返す**からです。C の整数除算のような切り捨ての罠はありません（そのかわり `Int` と `Double` を混ぜて足すことはできません — 第2章で詳しく）。

`fn f -> (f, toCelsius(f))` の `(f, toCelsius(f))` は**タプル**、2 つの値の組です。実行してみます。

```console
$ lune --eval table temperature.lune
((0, -17.77777777777778) (20, -6.666666666666667) (40, 4.444444444444445) (60, 15.555555555555555) (80, 26.666666666666668) (100, 37.77777777777778) (120, 48.888888888888886) (140, 60.0) (160, 71.11111111111111) (180, 82.22222222222223) (200, 93.33333333333333) (220, 104.44444444444444) (240, 115.55555555555556) (260, 126.66666666666667) (280, 137.77777777777777) (300, 148.88888888888889))
```

華氏と摂氏の対応表が、`(華氏, 摂氏)` のタプルのリストとして得られました。ループも、カウンタ変数も、途中経過を入れる変数もありません。「0 から 15 までの番号を 20 倍して華氏のリストを作り、それぞれを摂氏との組に写す」— プログラムが仕様書のように読めます。これが Lune の基本的な書き味です。

## 1.6 最初のエラー — コンパイラと対話する

さて、お待ちかねの時間です。**わざと間違えましょう**。`hello.lune` を少し書き換えて、`typo.lune` を作ります。`greeting` と書くべきところを `greting` と打ち間違えたことにします。

```lune
module hello

let greeting = "hello, world"

let main = println(greting)
```

```console
$ lune --check typo.lune
```

```text,diagnostic
error[TYP0001]: 未定義の名前: greting
  --> typo.lune:5:20
  |
5 | let main = println(greting)
  |                    ^^^^^^^ この名前は定義されていない
   = hint: もしかして `greeting` ですか?
   = help: 詳しくは `lune explain TYP0001 --lang ja` を実行してください
```

この表示を上から解剖します。Lune の診断はすべてこの形です。

| 行 | 意味 |
| --- | --- |
| `error[TYP0001]: ...` | 重大度（error）、**診断コード**（TYP0001）、要約 |
| `--> typo.lune:5:20` | 場所 — ファイル名:行:桁 |
| `5 \| let main = ...` と `^^^^^^^` | 問題のソースと、問題の箇所を指す印 |
| `= hint: ...` | 修正の提案。ここでは「もしかして `greeting` ですか?」 |
| `= help: ...` | もっと詳しく知る方法 |

> **表記について** — 診断の `-->` 行に表示されるパスは、実際にはあなたの環境での絶対パスになります。紙面では作業ディレクトリを省略しています。

`help` 行の言うとおりにしてみましょう。**Lune のすべての診断コードには、教材としての解説が付いています。**

```console
$ lune explain TYP0001
```

```text
error[TYP0001]: 未定義の名前

現在のスコープで束縛されておらず、prelude にも import にも見つからない
名前が使われました。

発生する例:

    let y = x + 1      # x はどこにも定義されていない

直し方:
使う前に名前を定義または import してください。綴りも確認してください。
```

何が起きたのか、それを再現する最小の例、直し方。エラーが出るたびにこの解説を読む習慣をつけると、コンパイラが家庭教師になります。

そして今回のようなタイポは、hint が機械的に適用できる修正なので、`lune fix` が直してくれます。

```console
$ lune fix typo.lune
module hello

let greeting = "hello, world"

let main = println(greeting)
```

修正後のソースが出力されました（`--write` を付けるとファイルを直接書き換えます）。

この「**壊す → 診断を読む → `explain` で理解する → 直す**」というループが、本書の学び方の基本です。各章にはこのための「壊してみよう」コーナーがあります。さっそくひとつ。

> **壊してみよう** — REPL で `Int` と `Bool` を足してみてください。
>
> ```text,diagnostic
> lune> 1 + true
> error[TYP0003]: +: Int が必要ですが、Bool が見つかりました
>    = help: 詳しくは `lune explain TYP0003 --lang ja` を実行してください
> ```
>
> `TYP0003`（型の不一致）は、これから最もよく出会う診断です。`:explain TYP0003` で解説を読んでおきましょう（REPL の中では `lune explain` の代わりに `:explain` が使えます）。

## 1.7 ここから先の地図

これで1周です。あなたはもう、Lune のプログラムを書いて、型を検査して、実行して、エラーを読んで直せます。この本の残りは、この章で駆け抜けた風景をゆっくり歩き直します。

- **第2〜3章** — 値・型・式、そして関数。部分適用とパイプライン `|>` という強力な道具が加わります。
- **第4章** — 遅延評価。1.2 節で予告した「計算はまだ起きていない」の全貌。Lune を学ぶ最大の理由がここにあります。
- **第5〜8章** — データの形を型で表す道具たち。代数的データ型、パターンマッチ、レコード、null 安全、そして無限リスト。
- **第9〜10章** — 命令的な書き方と、プログラムの分割。
- **第11〜13章** — コンパイラと道具を使いこなし、少し大きなプログラムを組み立てます。

順に読むのがおすすめですが、第4章まで読めば、あとは気になる章からつまみ食いしても大丈夫です。

## まとめ

| 書いたもの | 意味 |
| --- | --- |
| `let name = 式` | 束縛（計算の約束）。使われた時に評価される |
| `def f(x: T): U = 本体` | 関数定義 |
| `fn x -> 式` | ラムダ（名前のない関数） |
| `if c then a else b` / `if c:` ブロック | 条件分岐。値を返す式 |
| `[1, 2, 3]` | リスト。表示は `(1 2 3)` |
| `(a, b)` | タプル |
| `module m` | モジュール宣言。ファイルの先頭に置く |

| コマンド | 意味 |
| --- | --- |
| `lune` | REPL を起動 |
| `lune --check FILE` | 型検査のみ |
| `lune --eval NAME FILE` | 束縛 NAME を評価して表示 |
| `lune explain CODE` | 診断コードの解説 |
| `lune fix FILE` | 機械適用できる修正を実施 |
| `:quit` `:help` `:thunks` `:explain` | REPL コマンド |

## 演習問題

**演習 1-1**（★） `hello.lune` の挨拶を、自分の名前と好きな挨拶に変えて動かしてください。ついでに `greet` の本体の `+` を `-` に変えて、どんな診断が出るか見てみましょう。

<details><summary>解答</summary>

`"hello, " - name` は型エラーになります。

```text,diagnostic
error[TYP0003]: -: 数値型が必要ですが、String が見つかりました
   = help: 詳しくは `lune explain TYP0003 --lang ja` を実行してください
```

`+` は文字列の連結に使えますが、`-` は数値専用です。診断が「`-` には数値型が必要なのに `String` が来た」と、演算子の側の都合を主語にして説明していることに注目してください。

ところで、呼び出しの引数を消して `greet()` にしても、実は型エラーに**なりません**（`lune --check` は通ります）。Lune の関数は引数を途中まで渡せるからです — これは部分適用といって、第3章の主役のひとつです。

</details>

**演習 1-2**（★） `temperature.lune` を逆向きにした、摂氏 → 華氏の換算表を作ってください（0〜100 度を 20 度刻み）。換算式は `F = C × 9/5 + 32` です。

<details><summary>解答</summary>

```lune
module answers

# 演習 1-2: 摂氏 → 華氏の換算表（0〜100 度を 20 度刻み）。
def toFahrenheit(c: Int): Double =
    c * 9 / 5 + 32.0

let table = map(range(0, 6), fn i -> (i * 20, toFahrenheit(i * 20)))
```

```console
$ lune --eval table ex1-2.lune
((0, 32.0) (20, 68.0) (40, 104.0) (60, 140.0) (80, 176.0) (100, 212.0))
```

ひとつ罠があります。`+ 32` と書くと `TYP0003`（`+: Double が必要ですが、Int が見つかりました`）になります。`c * 9 / 5` は `/` のせいで `Double` になっているので、足す方も `32.0` と書く必要があります。Lune は `Int` と `Double` を黙って混ぜません。

</details>

**演習 1-3**（★★） `temperature.lune` の `fahrenheits` について、`fold` を使って合計を、さらに `length` と組み合わせて平均を求めてください。

<details><summary>解答</summary>

```lune
module answers

# 演習 1-3: fold で華氏温度の合計と平均を求める。
let fahrenheits = map(range(0, 16), fn i -> i * 20)

let total = fold(fahrenheits, 0, fn acc f -> acc + f)

let average = total / length(fahrenheits)
```

```console
$ lune --eval total ex1-3.lune
2400
$ lune --eval average ex1-3.lune
150.0
```

`fold(リスト, 初期値, fn 途中結果 要素 -> 新しい途中結果)` の形を覚えてください。`average` が `150.0`（`Double`）になるのは、`/` が常に `Double` を返すからです。

</details>

**演習 1-4**（★★） `temperature.lune` の表から、摂氏で氷点下になる華氏温度だけを `filter` で取り出してください。

<details><summary>解答</summary>

```lune
module answers

# 演習 1-4: 摂氏で氷点下になる華氏温度だけを残す。
def toCelsius(f: Int): Double =
    (f - 32) * 5 / 9

let fahrenheits = map(range(0, 16), fn i -> i * 20)

let freezing = filter(fahrenheits, fn f -> toCelsius(f) < 0.0)
```

```console
$ lune --eval freezing ex1-4.lune
(0 20)
```

華氏 0 度と 20 度だけが氷点下でした。比較の右辺が `0` ではなく `0.0` なのは、演習 1-2 と同じ理由です。

</details>

**演習 1-5**（★） `lune explain` を「呼び出す前」に自分で診断を予想する練習です。`greet("world", "again")` のように引数を 2 つ渡すと何が起きるでしょうか。予想してから実行し、`lune explain TYP0005` を読んでください。

<details><summary>解答</summary>

```text,diagnostic
error[TYP0005]: 引数は最大 1 個ですが、2 個渡されました
  --> arity.lune:6:20
  |
6 | let main = println(greet("world", "again"))
  |                    ^^^^^ 引数の個数が違う
   = help: 詳しくは `lune explain TYP0005 --lang ja` を実行してください
```

「**最大** 1 個」という言い方に注目してください。Lune の関数は引数を途中まで渡すこと（部分適用、第3章）ができるので、「少ない」のは必ずしもエラーではなく、「多い」ことが確実なエラーなのです。

</details>

---

**より正確には** — この章で登場した機能の正確な仕様は次にあります: 構文とリテラルは `documents/LANGUAGE_SPEC.md` §5–9、REPL の表示は `documents/REPL_SPEC.md` と `documents/VALUE_DISPLAY_SPEC.md`、診断の形式は `documents/ERROR_DIAGNOSTICS_SPEC.md`。この章のコード例は `books/examples/ch01/` にあり、すべて実際の CLI で検証されています。
