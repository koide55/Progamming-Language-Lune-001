# 第7章 null 安全

「値がないこと」を表す `null` は、多くの言語で実行時エラーの王様です。null チェックを1箇所忘れただけで、プログラムはある日突然落ちる — 発明者自身が「10億ドルの過ち」と悔やんだ仕掛けです。

Lune は `null` を廃止する代わりに、**型で飼いならす**道を選びました。null が入りうる場所を型 `T?` で宣言させ、確かめる前に使うことをコンパイラが許さない。第5章の `Option` と似た役割ですが、こちらは専用の構文（`??`、`?.`、絞り込み）を持つ軽量版です。使い分けは章の最後に整理します。

## 7.1 T? — null を持てる型

型に `?` を付けると、その型の値**または `null`** を持てるようになります。

```text
lune> let present: Int? = 42
ok
lune> let absent: Int? = null
ok
lune> present
42 : Nullable[Int]
```

表示に出てくる `Nullable[Int]` は `Int?` の内部名です（読み替えてください）。`Int` の値はそのまま `Int?` の場所に入りますが、**逆は許されません**。

```text,diagnostic
lune> def wantsInt(n: Int): Int =
...     n + 1
...
ok
lune> wantsInt(present)
error[TYP0003]: expected Int, got Nullable[Int]
   = help: run `lune explain TYP0003` for a detailed explanation
```

これが null 安全のすべてです。「null かもしれない値」は、null でないことを**確かめるまで**、普通の値として使えない。確かめる方法がこの章の残りです。

## 7.2 match で外す — null の被覆と絞り込み

一番基本の方法は `match` です。`orzero.lune`:

```lune
module orzero

# T? には T の値も null も入る。
let present: Int? = 42

let absent: Int? = null

# null を match で被覆すると、残りの腕の v は Int に絞り込まれる。
def orZero(value: Int?): Int =
    match value:
        | null -> 0
        | v -> v
```

```console
$ lune --eval unwrapped orzero.lune
42
$ lune --eval defaulted orzero.lune
0
```

`| null ->` の腕が null を引き受けた**あと**なので、次の腕の `v` は `Int` に**絞り込まれ**ます（narrowing）。だから `v` をそのまま `Int` として返せるのです。

網羅性検査（第5章）は null もケースとして数えます。`missingnull.lune`:

```lune
module bad

# Bool? の match は true / false だけでは足りない。
def toInt(b: Bool?): Int =
    match b:
        | true -> 1
        | false -> 0
```

```console
$ lune --check missingnull.lune
```

```text,diagnostic
error[TYP0007]: non-exhaustive match: missing case null
  --> missingnull.lune:5:5
  |
5 |     match b:
  |     ^^^^^ pattern null is not covered
   = hint: add a case for null, or a wildcard case `| _ -> ...`
   = help: run `lune explain TYP0007` for a detailed explanation
```

「null チェックを忘れる」というあの事故が、コンパイル時の `missing case null` に変わりました。

一つ注意。名前パターンだけで受けると、網羅性は満たせますが**絞り込まれません**。

```text,diagnostic
lune> def bad(value: Int?): Int =
...     match value:
...         | v -> v
...
error[TYP0003]: return type of bad: expected Int, got Nullable[Int]
  --> <repl:17>:2:5
  |
2 |     match value:
  |     ^^^^^ function body has type Nullable[Int]
   = help: run `lune explain TYP0003` for a detailed explanation
```

`v` が `Int` になるのは、`null` の腕がそれより前にあるときだけです。

## 7.3 ?? — なければこれ

「null ならデフォルト値」は頻出なので、専用の演算子があります。**null 合体演算子** `??` です。

```text
lune> absent ?? 7
7 : Int
lune> present ?? 7
42 : Int
lune> present ?? crash()
42 : Int
```

左が null でなければ左を、null なら右を返します。結果の型は `Int?` ではなく `Int` — 合体した時点で null の可能性は消えるからです。3つ目の例に注目してください。左に値があるとき、**右側は評価すらされません**。第4章の遅延評価が、ここでも当たり前のように効いています。

## 7.4 ?. — 安全にたどる

「`user` が null でなければ `user.name` を読みたい」— これも専用構文があります。**安全ナビゲーション** `?.` です。`nameof.lune`:

```lune
module nameof

record User:
    name: String
    age: Int

# ?. は受け手が null なら null に短絡し、そうでなければフィールドを読む。
def nameOf(user: User?): String? =
    user?.name

let someName = nameOf(User(name = "Ada", age = 36))

let noName = nameOf(null)

let fallback = nameOf(null) ?? "(nobody)"
```

```console
$ lune --eval someName nameof.lune
"Ada"
$ lune --eval noName nameof.lune
null
$ lune --eval fallback nameof.lune
"(nobody)"
```

受け手が null なら結果も null、そうでなければフィールドの値。結果は常に `String?` になるので、最後は `??` や `match` で受け止めます。`?.` で null を運び、`??` で着地させる — この2つはセットで使う道具です。

## 7.5 if で絞り込む

`match` を書くまでもない場面では、`if` の条件でも絞り込めます。

```text
lune> def orOne(x: Int?): Int =
...     if x != null then x else 1
...
ok
lune> orOne(absent)
1 : Int
```

`x != null` が真の分岐では、`x` は `Int` として使えます（`x == null` なら偽の分岐で絞り込まれます）。この絞り込みが効くのは `x != null` / `x == null` という単純な形だけで、`&&` で繋いだ複合条件や `elif` には及びません。凝った条件になったら `match` に切り替えてください。

## 7.6 null を返す関数を書く

ここまでは null を**受け取る**側でした。**返す**側は、素直に書けば通ります。

```text
lune> def maybeDiv(x: Int, y: Int): Double? =
...     if y == 0 then null else x / y
...
ok
lune> maybeDiv(7, 2)
3.5 : Nullable[Double]
lune> maybeDiv(7, 0)
null : Nullable[Double]
```

`null` を返す腕と `Double` を返す腕が、なぜ揉めずに合流できるのか。第5章 §5.6 の先取りボックスで予告した仕組みがここで働いています — 戻り値注釈 `Double?` が**期待型**として `if` の両分岐へ配られ、`null` の腕も `x / y` の腕もそこで `Double?` に揃うのです。`match` の腕でも同じことが起きます。ファイル版の `maybediv.lune`:

```lune
module maybediv

# 期待型 Double? が if の両分岐へ配られ、null の腕と x / y の腕がそこで合流する。
def maybeDiv(x: Int, y: Int): Double? =
    if y == 0 then null else x / y

let some = maybeDiv(7, 2)

let none = maybeDiv(7, 0)

let fallback = maybeDiv(7, 0) ?? 0.0
```

```console
$ lune --eval some maybediv.lune
3.5
$ lune --eval none maybediv.lune
null
$ lune --eval fallback maybediv.lune
0.0
```

`maybeDiv(7, 0)` で 0 除算エラーが出ないのは、`if` が選ばなかった腕を評価しないからです（第4章）。「失敗しうる計算」を else の腕に置いたまま、null で受け流す — `T?` を返す関数の基本形です。

> **こう書いても動く** — 分岐の前に、注釈付き `let` で部品を作っておく書き方もあります。
>
> ```lune
> # 部品を注釈付き let で先に作ってから分岐しても動く。
> # quotient はサンクなので、y == 0 の側では割り算は一度も走らない。
> def maybeDivLet(x: Int, y: Int): Double? =
>     let quotient: Double? = x / y
>     if y == 0 then null else quotient
> ```
>
> `maybeDivLet(7, 0)` もちゃんと `null` を返します。`let quotient: Double? = x / y` を「通って」いるのに 0 除算エラーが出ないのは、`quotient` がサンクのまま一度も force されないから — こちらも第4章の遅延評価です。どちらを選んでも安全なので、普段は分岐を先に書く素直な形で十分です。

「なくてもよい」フィールドの読み出し（`?.`）、デフォルトへの着地（`??`）、そしてこの「なければ null を返す関数」。3点セットで、null は型に守られた普通の道具になります。

## 7.7 Option[T] と T? の使い分け

似た道具が2つある理由と、選び方です。

| | `T?` | `Option[T]` |
| --- | --- | --- |
| 「なし」の表現 | `null` | `None` |
| 専用構文 | `??`、`?.`、if/match の絞り込み | なし（`match` と関数で扱う） |
| 相性 | フィールド・引数・戻り値の「なくてもよい」 | プレリュードのリスト API（`head`/`tail` が返す）、ジェネリック関数 |
| 入れ子の「なし」 | 表せない（`null` は1段） | `Some(None)` と `None` を区別できる |

実用の目安はこうです。**データの形として「ないかもしれない」を書くなら `T?`**（レコードのフィールド、関数の引数と戻り値）。**リスト処理や高階関数のパイプラインの中では `Option`**（プレリュードがそちらを話すからです）。境界では `match` で詰め替えれば行き来できます。

> **壊してみよう** — `orZero` の2つの腕を入れ替えると（`| v -> v` を先に）どうなるでしょう。予想してから試してください。
>
> ```text,diagnostic
> lune> def swapped(value: Int?): Int =
> ...     match value:
> ...         | v -> v
> ...         | null -> 0
> ...
> error[TYP0003]: branch type mismatch: Nullable[Int] vs Int
>    = help: run `lune explain TYP0003` for a detailed explanation
> ```
>
> 到達不能（`TYP0009`）を予想した人が多いはずですが、その手前で捕まりました。先頭の `v` はまだ null が被覆されていないので `Int?` のまま（7.2節の注意）で、`null` の腕の `Int` と型が食い違うのです。絞り込みは「null の腕が**先**」のときだけ働く — 腕の順番は型にまで影響します。

## まとめ

| 概念 | 一言で |
| --- | --- |
| `T?` | `T` または `null`。表示名は `Nullable[T]` |
| 型の守り | `T?` を `T` として使うと `TYP0003`。null ケース漏れは `TYP0007` |
| `match` | `\| null ->` を被覆すると、以降の名前パターンは `T` に絞り込み |
| `??` | null ならデフォルト。右辺は必要になるまで評価されない |
| `?.` | null なら null に短絡してフィールドを読む。`??` とセットで |
| `if x != null` | 単純形のみ絞り込み。複雑になったら `match` |
| null を返す | 期待型が分岐へ配られるので、素直に `if`/`match` で書ける（第5章 §5.6 と同じ仕組み） |
| vs `Option` | データの形は `T?`、リスト・高階関数の世界は `Option` |

## 演習問題

**演習 7-1**（★） 結果（値と型）を予想してから確かめてください。`absent: Int? = null`、`present: Int? = 42` とします。

```text
absent ?? 7
present ?? 7
absent == null
present ?? crash()
```

<details><summary>解答</summary>

`7 : Int`、`42 : Int`、`true : Bool`、`42 : Int`。最後の式が爆発しないのは `??` が短絡するからです。型が `Int?` ではなく `Int` になっていることも確認してください。

</details>

**演習 7-2**（★★） 7.5節の `orOne` を、`if` ではなく `match` で書き直してください。

<details><summary>解答</summary>

```text
lune> def orOne(x: Int?): Int =
...     match x:
...         | null -> 1
...         | v -> v
...
ok
lune> orOne(null)
1 : Int
lune> orOne(41)
41 : Int
```

`orZero` と同じ骨組みです。`if x != null` 版と `match` 版はどちらも正解で、分岐が2択なら `if`、増えるなら `match`、が目安です。

</details>

**演習 7-3**（★★） `nameOf` にならって `ageOf` を書き、`ageOf(null) ?? 0` が `0` になることを確かめてください。

<details><summary>解答</summary>

```text
lune> def ageOf(user: User?): Int? =
...     user?.age
...
ok
lune> ageOf(User(name = "Ada", age = 36))
36 : Nullable[Int]
lune> ageOf(null) ?? 0
0 : Int
```

「`?.` で運んで `??` で着地」の型 `User? → Int? → Int` の流れを、`:type` でも追ってみてください。

</details>

**演習 7-4**（★★★） 整数リストの平均を返す `average(xs: List[Int]): Double?` を書いてください。空リストの平均は `null` とします。0 除算を起こさずに書けるでしょうか。

<details><summary>解答</summary>

```lune
module answers

# 演習 7-4: 空リストの平均は「ない」。先に分岐すれば 0 除算には触れない。
def average(xs: List[Int]): Double? =
    if isEmpty(xs) then null else fold(xs, 0, fn a x -> a + x) / length(xs)

let some = average([2, 3, 4])

let none = average([])

let safe = average([]) ?? 0.0
```

```console
$ lune --eval some ex7-4.lune
3.0
$ lune --eval none ex7-4.lune
null
$ lune --eval safe ex7-4.lune
0.0
```

空かどうかを**先に**分岐してしまえば、割り算は空でないリストに対してしか評価されません。`null` の腕と計算の腕が `Double?` へ合流するのは 7.6節のとおりです。合計と割り算を注釈付き `let` で先に定義してから分岐する書き方でも、サンクのまま捨てられるので 0 除算にはなりません（7.6節の「こう書いても動く」）。

</details>

**演習 7-5**（★・逆転問題） 「null かもしれない値を、確かめずに使った」ことを型検査に叱られる最小のコードを書いてください。

<details><summary>解答</summary>

```lune
let present: Int? = 42

let oops = present + 1
```

とすると `error[TYP0003]: +: expected numeric type, got Nullable[Int]` が出ます。関数に渡す形（本文 7.1 節の `wantsInt(present)`）なら `expected Int, got Nullable[Int]`。他言語なら実行時の NullPointerException になっていた事故が、コンパイル時のこの1行に置き換わっている — それが null 安全の価値です。

</details>

---

**より正確には** — `T?` の型付け・narrowing の正確な規則は `documents/LANGUAGE_SPEC.md` §11（match の null パターン）と §9.2（if の絞り込み）、null を含む網羅性は `documents/MATCH_EXHAUSTIVENESS_SPEC.md`、期待型が分岐へ配られる規則は `documents/LOCAL_TYPE_INFERENCE_SPEC.md` §5.3。実例は `samples/nullable.lune` にもあります。この章のコード例は `books/examples/ch07/` にあり、すべて実際の CLI で検証されています。
