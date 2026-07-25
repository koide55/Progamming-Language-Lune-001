# 第5章 代数的データ型とパターンマッチ

ここまでの型は、数・文字列・タプルといった「素材」でした。この章では、**自分のプログラムのための型**を作ります。道具は2つ。データの形を宣言する**代数的データ型**（ADT）と、形に沿って分解する **`match`** です。

この2つを覚えると、プログラムの書き方が変わります。「値をチェックしてフラグで分岐する」代わりに、「ありうる形をぜんぶ型に書き、コンパイラにケース漏れを見張らせる」ようになるのです。ケースが漏れたときに Lune が**反例つき**で教えてくれるところまで、この章で体験します。

## 5.1 「形」を型で表す

図形を扱うプログラムを考えます。図形は、円か、長方形か、そのどちらかだとしましょう。Lune ではその「どちらか」をそのまま書けます。

```lune
type Shape =
    | Circle(radius: Double)
    | Rect(width: Double, height: Double)
```

`Shape` 型の値は、`Circle` か `Rect` のどちらかの**コンストラクタ**で作られます。それ以外の形はありえません。

```text
lune> Circle(1.0)
Circle(1.0) : Shape
lune> Rect(3.0, 4.0)
Rect(3.0, 4.0) : Shape
```

フィールドには名前を付けて宣言します（`radius: Double`）。この名前は宣言の読みやすさのためのもので、作るときは位置で渡します。

フィールドを持たないコンストラクタも作れます。信号の色のような「ただの選択肢」です。

```lune
type Color =
    | Red
    | Green
    | Blue
```

```text
lune> let g = Green()
ok
lune> g
Green : Color
```

v0.1 では、フィールドなしのコンストラクタも**呼び出して**値にします（`Green()`）。例外はプレリュードの `None` と `Nil`（リストの終端、第8章）で、これらは最初から値として登録されているため裸で使えます。

> **用語メモ** — `Shape` のような「どれか一つ」の型を**直和型**と呼びます。タプルやレコードのような「全部持つ」型（直積型）と対になる概念で、両方を組み合わせて作る型がいわゆる代数的データ型です。設計の使い分けは第6章の終わりで整理します。

## 5.2 match — 形に沿って分解する

ADT の値を使う側は `match` です。第1章から予告していた本命の構文をきちんと見ます。

```lune
def area(s: Shape): Double =
    match s:
        | Circle(r) -> r * r * 3.14159
        | Rect(w, h) -> w * h
```

`match` は対象の値の**形**を上から順に調べ、最初に合った腕の式を評価します。`Circle(r)` のようなパターンは、形を確かめると同時に、中身を `r` という名前で**取り出します**。検査と分解が一度に済む — これがパターンマッチの気持ちよさです。

`match` も式なので、値を返します。腕の本体が長ければ複数行にできます（インデントして書きます）。

パターンには色々な形が置けます。まとめて見ましょう。

```text
lune> def sign(n: Int): String =
...     match n:
...         | 0 -> "zero"
...         | x if x < 0 -> "negative"
...         | _ -> "positive"
...
ok
lune> sign(0)
"zero" : String
lune> sign(-5)
"negative" : String
lune> sign(3)
"positive" : String
```

- **リテラルパターン** `0` — その値ちょうどに合う
- **名前パターン** `x` — 何にでも合い、値に名前を付ける
- **ガード** `x if x < 0` — パターンに追加の条件を付ける
- **ワイルドカード** `_` — 何にでも合い、名前も付けない

タプルも分解できます。

```text
lune> def where(p: Tuple[Int, Int]): String =
...     match p:
...         | (0, 0) -> "origin"
...         | (x, 0) -> "x-axis"
...         | _ -> "elsewhere"
...
ok
lune> where((3, 0))
"x-axis" : String
```

ガードは `Shape` のような ADT と組み合わせると表現力を発揮します。`shape.lune`:

```lune
# ガード: パターンに追加の条件を付ける。
def describe(s: Shape): String =
    match s:
        | Circle(_) -> "circle"
        | Rect(w, h) if w == h -> "square"
        | Rect(_, _) -> "rectangle"
```

```console
$ lune --eval squareness shape.lune
"square"
```

## 5.3 網羅性 — コンパイラが反例をくれる

ここからが Lune の見せ場です。`match` は**網羅的**でなければなりません。つまり、ありうる形をすべてカバーしていなければ型エラーです。しかも Lune は「何が足りないか」を**具体的な反例**（witness）で教えてくれます。

`Color` のケースを1つ書き忘れてみます。

```text,diagnostic
lune> def label(c: Color): String =
...     match c:
...         | Red -> "warm"
...         | Blue -> "cool"
...
error[TYP0007]: 網羅的でない match: Green のケースがありません
  --> <repl:2>:2:5
  |
2 |     match c:
  |     ^^^^^ パターン Green がカバーされていない
   = hint: Green のケースを追加するか、ワイルドカードケース `| _ -> ...` を追加してください
   = help: 詳しくは `lune explain TYP0007 --lang ja` を実行してください
```

「`Green` が足りない」。この程度なら自分でも気づけそうですが、witness の真価は形が**入れ子**になったときです。`missing.lune`:

```lune
module bad

# Some(false) のケースが漏れている。
def toInt(o: Option[Bool]): Int =
    match o:
        | Some(true) -> 1
        | None -> 0
```

```console
$ lune --check missing.lune
```

```text,diagnostic
error[TYP0007]: 網羅的でない match: Some(false) のケースがありません
  --> missing.lune:5:5
  |
5 |     match o:
  |     ^^^^^ パターン Some(false) がカバーされていない
   = hint: Some(false) のケースを追加するか、ワイルドカードケース `| _ -> ...` を追加してください
   = help: 詳しくは `lune explain TYP0007 --lang ja` を実行してください
```

`Some` は書いたし `None` も書いた — それでも「`Some(false)` が漏れている」とコンパイラは**反例を合成して**指摘します。ここまで来ると、網羅性検査は単なるお目付け役ではなく、**仕様の穴を見つける道具**です。「この関数、こういう入力のこと考えてた?」と、実例つきで聞いてくれるのですから。

2つ注意を。第一に、**ガード付きの腕は網羅性に数えられません**。`| x if x < 0 -> ...` がすべての負数を覆うことをコンパイラは証明できないからです。ガードを使ったら、受け皿になる無条件の腕を必ず置いてください。第二に、`| _ -> ...` は網羅性を一発で満たしますが、**型にケースを足したときに教えてもらえなくなる**という代償があります。列挙できるなら列挙する — 次の演習 5-1 で効果を体験できます。

## 5.4 到達しない腕と、失敗しうる束縛

網羅性の逆向きの検査もあります。**すでに覆われていて絶対に選ばれない腕**は警告になります。`unreachable.lune`:

```lune
def f(c: Color): Int =
    match c:
        | Red -> 1
        | Red -> 2
        | Green -> 3
```

```console
$ lune --check unreachable.lune
```

```text,diagnostic
warning[TYP0009]: 到達しない match ケース: Red
  --> unreachable.lune:10:9
   |
10 |         | Red -> 2
   |         ^ このケースには決して到達しない
   = hint: このケースを削除するか、これをカバーしているケースより前に移動してください
   = help: 詳しくは `lune explain TYP0009 --lang ja` を実行してください
type check OK
```

`warning` なので検査自体は通ります（最後に `type check OK` が出ていることに注目）。CI で警告も落としたい場合の作法は第12章で扱います。

もう一つ。パターンは `let` にも書けました（タプルの分解束縛、第2章）。ただし `let` に置けるのは**失敗しようがない**（反駁不能な）パターンだけです。`refutable.lune`:

```lune
module bad

let Some(x) = Some(1)
```

```console
$ lune --check refutable.lune
```

```text,diagnostic
error[TYP0008]: let の束縛に反駁可能パターンは使えません: Some(x)
  --> refutable.lune:3:5
  |
3 | let Some(x) = Some(1)
  |     ^^^^ このパターンはマッチに失敗し得る
   = hint: このパターンは None をカバーしていません
   = hint: `match` を使って Option[Int] の全ケースを場合分けしてください
   = help: 詳しくは `lune explain TYP0008 --lang ja` を実行してください
```

右辺が `Some(1)` だと分かっていても、です。`Option[Int]` 型の値は `None` かもしれず、「かもしれない」がある限り `let` では受けられません。hint が言うとおり、そういう値は `match` で開けます。タプルパターンが `let` に書けたのは、タプルに「別の形」がないからです。

## 5.5 ジェネリックな ADT — 入れ物を型引数で抽象化する

`Option` を自分で定義すると、こう書けます（実際、プレリュードの定義と同じ構造です）。

```lune
type Option[T] =
    | Some(value: T)
    | None

def getOrElse[T](option: Option[T], defaultValue: T): T =
    match option:
        | Some(value) -> value
        | None -> defaultValue
```

`[T]` は「任意の型 `T` について」— `Option[Int]` にも `Option[String]` にも同じ定義が使えます。関数側も `def getOrElse[T](...)` と型引数を受け取り、`Option[T]` と `T` の関係（中身とデフォルト値は同じ型）を型で約束します。第3章で読んだ `map : [T, U] List[T] -> (T -> U) -> List[U]` と同じ仕組みです。

## 5.6 Option と Result を使う

プレリュードには `Option[T]`（値があるかないか）と `Result[T, E]`（成功か失敗か）が最初から入っています。基本の道具はこの4つです。

```text
lune> getOrElse(Some(42), 0)
42 : Int
lune> getOrElse(None, 7)
7 : Int
lune> optionMap(Some(2), fn x -> x + 1)
Some(3) : Option[Int]
lune> unwrapOr(Err("boom"), 0)
0 : Int
lune> resultMap(Ok(20), fn x -> x * 2)
Ok(40) : Result[Int, E]
```

`optionMap` は「あれば変換、なければそのまま `None`」、`unwrapOr` は「成功なら中身、失敗ならデフォルト」。例外を投げる代わりに**失敗を値として運ぶ** — これが関数型の定番のエラー処理で、第13章のケーススタディで本格的に使います。

自分の関数から返してみましょう。整数の割り算は 0 では割れないので、結果を「失敗を値として運ぶ」型 `Option[Double]` で包みます。

```text
lune> def maybeDiv(x: Int, y: Int): Option[Double] =
...     if y == 0 then None else Some(x / y)
...
ok
lune> maybeDiv(1, 2)
Some(0.5) : Option[Double]
lune> maybeDiv(1, 0)
None : Option[Double]
```

さりげないコードですが、型検査器が静かに良い仕事をしています。`None` は単体では「中身の型が何か」を知りません。裸のまま打つと、型引数が未確定で残ることが見えます。

```text
lune> None
None : Option[T]
```

先ほどの `resultMap(Ok(20), ...)` の結果に `E` が残っていたのも同じ理由です — `Ok(20)` からは成功側の型しか分かりません。では `maybeDiv` の中の `None` はなぜ `Option[Double]` になれたのか。関数の返り値注釈 `Option[Double]` が**期待型**として `if` の両分岐に配られ、未確定だった `T` をそこで確定させるからです。期待型は `let` の型注釈からも流れます。

```text
lune> let nothing: Option[Double] = None
ok
lune> nothing
None : Option[Double]
```

期待型は `match` の腕にも配られます。0 除算を「理由つきの失敗」として返すなら `Result` で。`maybediv.lune`:

```lune
# match の各腕にも期待型が分配される。Err の T、Ok の E も同様に確定する。
def safeDiv(x: Int, y: Int): Result[Double, String] =
    match y:
        | 0 -> Err("div by zero")
        | _ -> Ok(x / y)
```

```console
$ lune --eval ratio maybediv.lune
Ok(4.5)
```

`Err("div by zero")` からは失敗側の型しか、`Ok(x / y)` からは成功側の型しか分かりませんが、期待型 `Result[Double, String]` が残りの型引数を埋めてくれます。

> **先取り: null 許容型でも同じ** — この「期待型が分岐に配られて合流する」仕組みは、第7章で学ぶ null 許容型 `T?` でも働きます。
>
> ```lune
> # 先取り (第7章): null 許容型でも同じ仕組みで分岐が合流する。
> def nullDiv(x: Int, y: Int): Double? =
>     if y == 0 then null else x / y
> ```
>
> `null` の分岐と `Double` の分岐が `Double?` へ合流して、型検査を通ります。`Option` と `T?` の使い分けは第7章で整理します。

## まとめ

| 概念 | 一言で |
| --- | --- |
| `type T = \| A(...) \| B(...)` | 直和型。値は必ずどれか一つのコンストラクタ |
| フィールドなしコンストラクタ | `Green()` と呼んで値にする（プレリュードの `None` / `Nil` だけは裸で値） |
| `match` | 形の検査と分解を同時に行う式 |
| パターン | リテラル / 名前 / `_` / タプル / コンストラクタ / ガード `if` |
| `TYP0007` | ケース漏れ。**反例つき**で教えてくれる |
| `TYP0009` | 到達しない腕（警告） |
| `TYP0008` | `let` に失敗しうるパターンは置けない |
| `type Option[T] = ...` | ジェネリック ADT。関数側は `def f[T](...)` |
| `Option` / `Result` | プレリュード提供。`getOrElse` / `optionMap` / `unwrapOr` / `resultMap` |
| 期待型 | 返り値注釈や `let` 注釈が分岐へ配られ、`None` / `Err(...)` の型引数を確定 |

## 演習問題

**演習 5-1**（★） 本文の `Color` に `Yellow` を追加してください（`label` はそのまま）。どの診断が出るか予想してから `--check` し、`| _ -> ...` で網羅性を満たした場合との違いを考えてください。

<details><summary>解答</summary>

`error[TYP0007]: 網羅的でない match: Yellow のケースがありません` が `label` に出ます。型にケースを足した瞬間、**その型を match しているすべての場所**をコンパイラが洗い出してくれる — これが「列挙できるなら `_` より列挙」の理由です。`| _ -> "unknown"` と書いてあったら、`Yellow` は黙って `"unknown"` に落ち、誰も気づきません。

</details>

**演習 5-2**（★★） 信号機の色 `Light`（Red / Yellow / Green）と、「次の色」を返す `next` を書いてください。赤→青→黄→赤の順とします。

<details><summary>解答</summary>

```lune
module answers

# 演習 5-2: 信号機の次の色。網羅性検査が全色の考慮を保証する。
type Light =
    | Red
    | Yellow
    | Green

def next(light: Light): Light =
    match light:
        | Red -> Green()
        | Green -> Yellow()
        | Yellow -> Red()

let afterRed = next(Red())

let afterTwo = next(next(Red()))
```

```console
$ lune --eval afterTwo ex5-2.lune
Yellow
```

パターンでは裸の `Red`、値を作るときは `Red()`。腕を1本消して `TYP0007` を出してみるのも良い復習です。

</details>

**演習 5-3**（★★） 整数を検査して、0以上なら値を、負なら理由を返す仕組みを作ってください。プレリュードの `Result[Int, String]` でも書けますが、ここでは自分用の結果型（型引数なし）を定義すること。コンストラクタ名を自分のドメインの言葉にできる、という ADT の利点を味わう練習です。

<details><summary>解答</summary>

```lune
module answers

# 演習 5-3: 検査の結果を、成功と失敗の両方の情報ごと型にする。
type Checked =
    | Valid(value: Int)
    | Invalid(reason: String)

def check(n: Int): Checked =
    if n >= 0 then Valid(n) else Invalid("negative")

def report(c: Checked): String =
    match c:
        | Valid(v) -> "ok: " + show(v)
        | Invalid(reason) -> "rejected: " + reason

let good = report(check(5))

let bad = report(check(-3))
```

```console
$ lune --eval bad ex5-3.lune
"rejected: negative"
```

「成功にも失敗にも運びたい情報がある」とき、Bool や特別な値（-1 など）ではなく型で表す — ADT 設計のいちばん実用的な型紙です。5.6節の仕組みがあるので `Result[Int, String]` を使う版もそのまま書けますが、自分用の型なら `Valid` / `Invalid` という**ドメインの言葉**が `match` の腕や診断にそのまま現れます。

</details>

**演習 5-4**（★★★） プレリュードを使わずに `MyOption[T]` と `myGetOrElse` を自作し、`MySome(42)` と `MyNone()` の両方で動くことを確かめてください。

<details><summary>解答</summary>

```lune
module answers

# 演習 5-4: ジェネリックな入れ物を自作する。prelude の Option と同じ構造。
type MyOption[T] =
    | MySome(value: T)
    | MyNone

def myGetOrElse[T](option: MyOption[T], defaultValue: T): T =
    match option:
        | MySome(value) -> value
        | MyNone -> defaultValue

let some = myGetOrElse(MySome(42), 0)

let none = myGetOrElse(MyNone(), 0)

# 期待型による確定 (5.6節) は自作のジェネリック ADT にも働く。
let empty: MyOption[Int] = MyNone()
```

```console
$ lune --eval some ex5-4.lune
42
$ lune --eval none ex5-4.lune
0
```

型引数の決まり方が2通り見えます。`MySome(42)` の `T = Int` は**引数から**決まり、`MyNone()` の `T` はもう一方の引数 `0` との単一化で決まります。また、5.6節の期待型による確定は自作のジェネリック ADT にも働くので、`let empty: MyOption[Int] = MyNone()` のように注釈から確定させることもできます。

</details>

**演習 5-5**（★・逆転問題） `TYP0008`（反駁可能パターン）を出す最小のコードを書き、診断の2つの hint がそれぞれ何を教えているか説明してください。

<details><summary>解答</summary>

`let Some(x) = Some(1)`（5.4節）。1つ目の hint「このパターンは None をカバーしていません」は**なぜ**失敗しうるか（覆えていない形の名指し）、2つ目の「`match` を使って全ケースを場合分けしてください」は**どうすればいいか**（代わりの構文）。診断は「原因 → 対処」の順で読む、という第11章の読み方の予行演習です。

</details>

---

**より正確には** — ADT と `match` の構文は `documents/LANGUAGE_SPEC.md` §10–11、網羅性検査と witness の算法は `documents/MATCH_EXHAUSTIVENESS_SPEC.md`、`Option`/`Result` の全 API は `documents/STANDARD_LIBRARY_SPEC.md` §4–5、期待型がコンストラクタの型引数を確定する規則は `documents/LOCAL_TYPE_INFERENCE_SPEC.md` §5.3・§5.6。なお仕様書には OR パターン（`| 0 | 1 ->`）が載っていますが v0.1 では未実装です。この章のコード例は `books/examples/ch05/` にあり、すべて実際の CLI で検証されています。
