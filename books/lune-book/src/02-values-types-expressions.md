# 第2章 値・型・式

第1章では駆け足で言語を1周しました。ここからの第II部では、部品を一つずつ手に取って眺めます。まずは一番小さな部品 — 値と、その型と、それらを組み合わせる式です。

この章でも REPL を開いておいてください。Lune の式はすべて REPL にそのまま打ち込めます。「この式の型は何だろう」と思ったら、打てば答えが返ります。

## 2.1 リテラルと基本型

Lune のリテラルと、対応する型の一覧です。

| リテラル | 型 | 例の表示 |
| --- | --- | --- |
| `42` | `Int` | `42 : Int` |
| `3.14` | `Double` | `3.14 : Double` |
| `"hello"` | `String` | `"hello" : String` |
| `true` / `false` | `Bool` | `true : Bool` |
| `null` | `Null` | `null : Null` |
| `()` | `Unit` | `() : Unit` |
| `(1, "a")` | `Tuple[Int, String]` | `(1, "a") : Tuple[Int, String]` |

いくつか補足します。

**Int は大きさを気にしなくてよい**。v0.1 の `Int` は任意精度で、あふれることがありません。

```text
lune> 9223372036854775807 + 1
9223372036854775808 : Int
```

64ビット整数の限界を超えても平気です（C ならここで音もなく負の数になります）。

**文字列のエスケープ**。`"` の中では `\n`（改行）や `\"` が使えます。表示（`show` 形式）ではエスケープされたまま出るので驚かないでください。

```text
lune> "a\nb"
"a\nb" : String
```

**シングルクォートは String になる**。`'x'` という書き方も受け付けますが、v0.1 に独立した文字型は事実上なく、`"x"` と同じ `String` になります。

```text
lune> 'x'
"x" : String
```

**`null` と `()` は別物**です。`null` は「値がない」ことを表すためだけの値で、null 安全（第7章）の主役です。`()` は `Unit` 型のただ一つの値で、「返すべき意味のある値がない」関数（`println` など）の戻り値に使われます。

## 2.2 演算子 — 算術・比較・論理

算術演算子は `+` `-` `*` `/` `%` と単項の `-` です。優先順位はおおむね数学の直感どおりで、`()` でくくれば変えられます。

```text
lune> 1 + 2 * 3
7 : Int
lune> (1 + 2) * 3
9 : Int
lune> 2 * -3
-6 : Int
```

`/` と `%` には注意が要ります。第1章でも触れたとおり、**`/` は常に `Double` を返します**。整数の割り算の余りが欲しいときは `%`（こちらは `Int`）です。

```text
lune> 7 / 2
3.5 : Double
lune> 7 % 2
1 : Int
```

そして **`Int` と `Double` は黙って混ざりません**。

```text
lune> 1 + 2.0
error[TYP0003]: +: expected Int, got Double
   = help: run `lune explain TYP0003` for a detailed explanation
lune> 1 == 1.0
error[TYP0003]: ==: cannot compare Int and Double
   = help: run `lune explain TYP0003` for a detailed explanation
```

暗黙の型変換で「だいたい合ってる」結果を返すより、書き手にどちらの世界で計算したいのかを決めてもらう — Lune はその立場です。`2.0` か `2` か、リテラルの側を揃えてください。

比較演算子は `==` `!=` `<` `<=` `>` `>=` です。`==` と `!=` は数値・文字列・Bool で使えます。大小比較の `<` 系は数値専用です。

```text
lune> 3 < 5
true : Bool
lune> "a" == "a"
true : Bool
lune> "a" < "b"
error[TYP0003]: <: expected numeric type, got String
   = help: run `lune explain TYP0003` for a detailed explanation
```

> **罠: 複合値の `==` は中身を見ない** — v0.1 の `==` は、タプルやリストのような複合値に対しては**同じ値かどうか（同一性）**を見ます。中身が等しいかではありません。
>
> ```text
> lune> (1, 2) == (1, 2)
> false : Bool
> lune> let t = (1, 2)
> ok
> lune> t == t
> true : Bool
> ```
>
> 同じ書き方をした2つのタプルは「別々に作られた別の値」なので `false`、同じ束縛どうしなら `true` です。リストも同様です。構造の中身を比べたいときは、分解して要素ごとに比べるか、`match`（第5章）を使ってください。この挙動には足をすくわれやすいので、v0.1 を使う間は覚えておきましょう。

論理演算子は `&&`（かつ）と `||`（または）、否定は関数 `not` です。`&&` は `||` より強く結びつきます。そして第4章で見た遅延評価のおかげで、どちらも**短絡**します — 左だけで答えが決まるなら、右は評価されません。

```text
lune> false && crash()
false : Bool
lune> true || crash()
true : Bool
lune> not(true)
false : Bool
```

このほかに null 合体の `??`（第7章）とパイプライン `|>`（第3章）があります。全演算子の優先順位表は付録Aにまとめます。

## 2.3 if は式 — then/else と elif

第1章の復習から。`if` は値を返す式で、1行形式とブロック形式があります。

```text
lune> if 5 > 3 then "big" else "small"
"big" : String
```

式である以上、守るべき規則が2つあります。**条件は `Bool`**、そして**分岐の型は一致**です。

```text
lune> if 1 then 2 else 3
error[TYP0003]: if condition: expected Bool, got Int
   = help: run `lune explain TYP0003` for a detailed explanation
lune> if true then 1 else "a"
error[TYP0003]: branch type mismatch: Int vs String
   = help: run `lune explain TYP0003` for a detailed explanation
```

C のように「0 は偽」ではありません。`if x % 2` ではなく `if x % 2 == 1` と書きます。

分岐が増えるときは、ブロック形式の `elif` が使えます。`grade.lune`:

```lune
module grade

# if は式。block 形式では elif で分岐を足せる。
def grade(score: Int): String =
    if score >= 80:
        "pass"
    elif score >= 60:
        "retry"
    else:
        "fail"

let result = grade(75)
```

```console
$ lune --eval result grade.lune
"retry"
```

どんなに分岐しても、`grade` は必ず `String` を一つ返します。「どの経路を通っても値がある」ことを型検査が保証してくれる — 式指向の安心感です。

## 2.4 let-in — 式の中の束縛

`let` はトップレベルだけのものではありません。**式の中**で一時的な名前が欲しいときは `let ... in ...` が使えます。

```text
lune> let answer = let x = 40 in x + 2
ok
lune> answer
42 : Int
```

`in` の右側が式全体の値になり、`x` はその中でだけ見えます。名前を2つ以上付けたいときは、ブロック形式で `let` を並べるのがきれいです。

```lune
module answers

# 演習 2-3: ブロック形式の let で中間値に名前を付けて BMI を計算する。
let bmi =
    let h = 1.7
    let w = 62.0
    w / (h * h)
```

```console
$ lune --eval bmi ex2-3.lune
21.453287197231838
```

インデントされたブロックの中に `let` を並べ、最後に置いた式がブロック全体の値になります。`lune fmt` もこの形を正準としています。

## 2.5 型注釈 — 書く場所と省ける場所

`let` には型注釈を付けられます。

```lune
let y: Int = 42
```

注釈と実際の型が食い違えば、もちろん型エラーです。`annot.lune`:

```lune
module bad

let n: Int = "hello"
```

```console
$ lune --check annot.lune
```

```text,diagnostic
error[TYP0003]: let annotation: expected Int, got String
  --> annot.lune:3:14
  |
3 | let n: Int = "hello"
  |              ^^^^^^^ this expression has type String
   = help: run `lune explain TYP0003` for a detailed explanation
```

では、どこで注釈を書き、どこで省けるのか。v0.1 の目安はこうです。

| 場所 | 注釈 |
| --- | --- |
| `let` の右辺が明らか | 省略できる（右辺から推論される） |
| `def` の引数と戻り値 | 書く（再帰関数の戻り値型は必須 — `TYP0011`） |
| ラムダ `fn x -> ...` の引数 | 文脈から推論されることが多い（第3章） |

注釈は機械のためだけのものではありません。`let total: Double = ...` と書いておけば、読む人への宣言になり、右辺を書き間違えた瞬間に上のような診断が出ます。**迷ったら書く、確かめたいときは `:type`** — これが実務の感覚です。

## 2.6 タプル — 型の違う値の組

リスト（第8章）の要素はすべて同じ型ですが、**タプル**は型の違う値を決まった個数だけ束ねます。

```text
lune> let pair = (1, "a")
ok
lune> pair
(1, "a") : Tuple[Int, String]
```

タプルから値を取り出すのは**分解束縛**です。`.1` のようなアクセサはありません — 名前を付けて開けます。

```text
lune> let (a, b) = (10, 20)
ok
lune> a
10 : Int
lune> b
20 : Int
```

第1章の温度換算表では `(華氏, 摂氏)` のタプルのリストを作りました。「2つの値をとりあえず束ねて運ぶ」のがタプルの仕事です。束ねた値に名前を付けたくなったら、それはレコード（第6章)の出番です。

> **壊してみよう** — 型検査より前の段階、字句とレイアウトのエラーも見ておきましょう。どちらも第11章で学ぶ診断コード体系の「LXL」「PRS」族です。
>
> `let x = $1` と書くと、Lune の知らない文字でエラーになります。
>
> ```text,diagnostic
> error[LXL0001]: unexpected character '$'
>   --> lex.lune:3:9
>   |
> 3 | let x = $1
>   |         ^ unexpected character
>    = help: run `lune explain LXL0001` for a detailed explanation
> ```
>
> 理由なく行頭を字下げすると、レイアウト規則に引っかかります。
>
> ```text,diagnostic
> error[PRS0001]: expected top-level declaration, got INDENT
>   --> indent.lune:4:1
>   |
> 4 |   let b = 2
>   | ^ unexpected token
>    = help: run `lune explain PRS0001` for a detailed explanation
> ```
>
> Lune のインデントは Python と同じく構文の一部です。ブロックを作るのは `=` や `:` の後だけ、と覚えてください。

## まとめ

| 事実 | 一言で |
| --- | --- |
| 基本型 | `Int`（任意精度）/ `Double` / `String` / `Bool` / `Null` / `Unit` / `Tuple[...]` |
| `/` と `%` | `/` は常に `Double`、余りは `%` |
| `Int` と `Double` | 暗黙には混ざらない。リテラルの側を揃える |
| `==` | 数値・文字列・Bool は値で比較。複合値は同一性（罠!） |
| `&&` `||` | 短絡する。`&&` が先に結びつく |
| `if` | 条件は `Bool`、分岐の型は一致。`elif` で多分岐 |
| `let ... in` / ブロック `let` | 式の中の一時的な名前 |
| 型注釈 | `let` では省略可、`def` では書く。確認は `:type` |
| タプル | `(a, b)` で束ね、`let (x, y) = ...` で開ける |

## 演習問題

**演習 2-1**（★） 次の式の値と型を予想してから、REPL で確かめてください。

```text
19 / 4
19 % 4
1 + 2 * 3 - 4
2 * -3
true && false || true
```

<details><summary>解答</summary>

`4.75 : Double`（`/` は常に Double）、`3 : Int`、`3 : Int`、`-6 : Int`、`true : Bool`（`&&` が先に評価されて `false`、次に `|| true`）。

</details>

**演習 2-2**（★） `grade.lune` に「90 点以上は "excellent"」の分岐を足してください。分岐を**どこに**足すかで結果が変わることを、`grade(95)` で確かめてください。

<details><summary>解答</summary>

`if score >= 90: "excellent"` を**先頭**に置きます。`elif score >= 80: ...` より後ろに置くと、95 点は先に `score >= 80` に捕まって `"pass"` になってしまいます。`if`/`elif` は上から順に試される — 条件の並び順は仕様の一部です。

</details>

**演習 2-3**（★★） 身長 1.7 m、体重 62.0 kg の BMI（体重 ÷ 身長²）を、ブロック形式の `let` で中間値に名前を付けながら計算してください。

<details><summary>解答</summary>

```lune
module answers

# 演習 2-3: ブロック形式の let で中間値に名前を付けて BMI を計算する。
let bmi =
    let h = 1.7
    let w = 62.0
    w / (h * h)
```

```console
$ lune --eval bmi ex2-3.lune
21.453287197231838
```

`1.7` を `1` にすると `TYP0003` が出ます。`Int` と `Double` の分離は、こういう単位の混同を早めに捕まえてくれます。

</details>

**演習 2-4**（★★） 分解束縛を使って、タプル `(1, 2)` の2つの値を入れ替えた `(2, 1)` を作ってください。

<details><summary>解答</summary>

```lune
module answers

# 演習 2-4: タプルの分解束縛で 2 値を入れ替える。
let (x, y) = (1, 2)

let swapped = (y, x)
```

```console
$ lune --eval swapped ex2-4.lune
(2, 1)
```

一時変数は要りません。「開けて、逆順に束ね直す」だけです。

</details>

**演習 2-5**（★★） `(1, 2) == (1, 2)` は `true` と `false` のどちらでしょう。予想してから確かめ、その理由を説明してください。

<details><summary>解答</summary>

`false` です（2.2節の罠）。2つの `(1, 2)` はそれぞれ別に作られた値で、v0.1 の `==` は複合値の中身ではなく同一性を比べます。同じ束縛なら `let t = (1, 2)` として `t == t` は `true`。中身を比べたいなら分解して `a1 == a2 && b1 == b2` のように要素ごとに比較します。

</details>

---

**より正確には** — リテラルと型は `documents/LANGUAGE_SPEC.md` §5–6、演算子の全優先順位表は `documents/SYNTAX_SPEC.md` §14（`::` `++` など将来分を含むため、実装済みかは `LANGUAGE_SPEC.md` を正とします）、`if`/`let-in` は `documents/LANGUAGE_SPEC.md` §9。値の表示規則は `documents/VALUE_DISPLAY_SPEC.md`。この章のコード例は `books/examples/ch02/` にあり、すべて実際の CLI で検証されています。
