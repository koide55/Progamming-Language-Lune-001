# 第6章 レコード

タプル（第2章）は値を「束ねる」道具でしたが、`(36, "Ada")` の 36 が年齢なのか背番号なのかは、書いた本人しか知りません。値に**名前**を付けて束ねたくなったら、**レコード**の出番です。第5章の ADT が「どれか一つ」（直和）を表すのに対し、レコードは「全部持つ」（直積）を名前付きで表します。

## 6.1 宣言と構築 — 名前で作る

```lune
record User:
    name: String
    age: Int
```

フィールドの名前と型を並べるだけです。作るときは**必ずフィールド名を指定**します。

```text
lune> let ada = User(name = "Ada", age = 36)
ok
lune> ada
{ name = "Ada", age = 36 } : User
```

表示も `{ フィールド = 値 }` の形です。位置で渡すことはできません。

```text,diagnostic
lune> User("Ada", 36)
error[REC0006]: User の構築には名前付きフィールドが必要です
  --> <repl:2>:1:25
  |
1 | User("Ada", 36)
  |                         ^^^^^ フィールド = 値 の形で書く
   = help: 詳しくは `lune explain REC0006 --lang ja` を実行してください
```

ここは ADT のコンストラクタ（位置渡し、第5章）と対照的です。レコードはフィールドが増えがちで、`User("Ada", 36)` の 36 が何かは型が同じ限り機械にも人にも判別できない — だから名前を強制する、という設計です。おかげで構築まわりの間違いは、すべて名指しで叱ってもらえます。足りなければ `REC0003`（missing field）、知らない名前なら `REC0005`、同じ名前を2回書けば `REC0004` です。

## 6.2 フィールドアクセスと遅延

読み出しは `.` です。

```text
lune> ada.name
"Ada" : String
lune> ada.age + 1
37 : Int
```

タイポにも did-you-mean が効きます。`typofield.lune`:

```console
$ lune --check typofield.lune
```

```text,diagnostic
error[REC0002]: 存在しないレコードフィールド: User.nmae
  --> typofield.lune:9:12
  |
9 | let oops = ada.nmae
  |            ^^^ このレコードにそのフィールドは宣言されていない
   = hint: もしかして `name` ですか?
   = help: 詳しくは `lune explain REC0002 --lang ja` を実行してください
```

そして第4章の住人ならもう予想がつくはずです — **フィールドも遅延されます**。

```text
lune> let ghost = User(name = "Ghost", age = crash())
ok
lune> ghost.name
"Ghost" : String
lune> :thunks ghost
ghost : evaluated = { name = "Ghost", age = <thunk> }
```

`age` に地雷を入れたまま `name` は平気で読めました。`:thunks` のプレビューでは、触っていないフィールドが `<thunk>` のまま見えています。

構築の時点で評価してほしいフィールドには `strict` を付けます。

```text
lune> record Tagged:
...     strict tag: Int
...     note: String
...
ok
lune> let t = Tagged(tag = crash(), note = "n")
ok
lune> t.note
error[RUN0006]: crash() が評価されました
   = help: 詳しくは `lune explain RUN0006 --lang ja` を実行してください
```

`note` を読んだだけなのに `tag` の地雷が爆発しました。`t` を最初に force した瞬間にレコードが構築され、strict フィールドはそのとき評価されるからです。「不正な値を抱えたレコードを存在させない」— 第4章で予告した設計道具です。

## 6.3 ジェネリックなレコード

型引数も取れます。第5章の ADT と同じ書き方です。

```text
lune> record Box[T]:
...     value: T
...
ok
lune> Box(value = 42)
{ value = 42 } : Box[Int]
```

フィールドの値から `T = Int` が推論されました。関数側も型引数付きで書けます（演習 6-3 で、型が入れ替わる `swap` を作ります）。

## 6.4 タプル・ADT・レコードの使い分け

「値をまとめる」道具が3つ揃いました。整理しておきます。

| 道具 | 向いている場面 | 例 |
| --- | --- | --- |
| タプル | その場限りの2〜3個の組。名前を付けるほどでもない | `zip` の結果、`(商, 余り)` |
| レコード | 同じ形を何度も使う。フィールドに名前が要る | `User`、設定、集計結果 |
| ADT | 「どれか一つ」の選択肢がある | `Shape`、`Option`、状態 |

組み合わせるのが普通です。レコードのリストを第1章以来の道具で加工する例を見ましょう。`items.lune`:

```lune
module items

record Item:
    name: String
    price: Int

let items = [Item(name = "pen", price = 120), Item(name = "note", price = 200)]

let total = fold(map(items, fn i: Item -> i.price), 0, fn a x -> a + x)
```

```console
$ lune --eval total items.lune
320
```

「レコードのリストから、フィールドを `map` で抜き、`fold` で畳む」— 実務の Lune プログラムの背骨になるパターンです。

## 6.5 まだできないこと — update と pattern

v0.1 のレコードには、隣の言語にある2つの機能がまだありません。

**record update**（`{ ada | age = 37 }` のような「一部だけ変えたコピー」）はないので、新しい値は全フィールドを書いて作ります。**record pattern** もないので、`match` でレコードは分解できません。

```text,diagnostic
lune> match ada:
...     | { name = n } -> n
...
error[PRS0001]: パターンが必要ですが、LBRACE が見つかりました
  --> <repl:3>:2:7
  |
2 |     | { name = n } -> n
  |       ^ 予期しないトークン
   = help: 詳しくは `lune explain PRS0001 --lang ja` を実行してください
```

レコードの中身が要るときは `.` で読む、条件分岐はフィールドの値に対して `if`/`match` する、と覚えてください。どちらも将来仕様（付録E）には入っています。

> **壊してみよう** — レコード構築の診断 REC0003（フィールド不足）・REC0004（同じフィールドを2回）・REC0005（知らないフィールド）を、`User` でひとつずつ出してみてください。すべて構築式の上で名指しされることを確認しましょう。第11章で学ぶコード体系のうち、REC 族はこの章がホームグラウンドです。

## まとめ

| 概念 | 一言で |
| --- | --- |
| `record R:` + フィールド宣言 | 直積を名前付きで。構築は `R(field = value)` 必須 |
| `r.field` | 読み出し。タイポは `REC0002` + did-you-mean |
| フィールドの遅延 | デフォルト遅延。`strict field: T` で構築時評価 |
| `record Box[T]:` | ジェネリックレコード |
| 使い分け | その場の組→タプル / 名前つき直積→レコード / どれか一つ→ADT |
| 未対応 | record update / record pattern（読み出しは `.` で） |

## 演習問題

**演習 6-1**（★） `User` の構築を3通りに壊して、`REC0003`・`REC0005`・`REC0006` をそれぞれ出してください（どの壊し方がどのコードになるか、先に予想を）。

<details><summary>解答</summary>

`User(name = "X")` → `REC0003`（age が足りない）、`User(name = "X", years = 1)` → `REC0005`（years は知らない名前）、`User("X", 36)` → `REC0006`（名前なし構築）。ついでに `User(name = "X", name = "Y", age = 1)` で `REC0004` も出せます。

</details>

**演習 6-2**（★★） `items.lune` の品物のうち、150円以上のものの**名前だけ**のリストを作ってください。

<details><summary>解答</summary>

```lune
module answers

# 演習 6-2: 150 円以上の品物の名前だけを取り出す。
record Item:
    name: String
    price: Int

let items = [Item(name = "pen", price = 120), Item(name = "note", price = 200)]

let pricey = map(filter(items, fn i: Item -> i.price >= 150), fn i: Item -> i.name)
```

```console
$ lune --eval pricey ex6-2.lune
("note")
```

`filter` で絞ってから `map` で抜く。逆順（先に名前を抜く）だと価格が消えて絞れなくなる — パイプラインの順序は情報の寿命で決まります。

</details>

**演習 6-3**（★★） ジェネリックなレコード `Pair[A, B]`（`first: A`、`second: B`）と、前後を入れ替える `swap` を書いてください。`swap` の戻り値の型が `Pair[B, A]` になることに注意。

<details><summary>解答</summary>

```lune
module answers

# 演習 6-3: ジェネリックなレコードと、型が入れ替わる swap。
record Pair[A, B]:
    first: A
    second: B

def swap[A, B](p: Pair[A, B]): Pair[B, A] =
    Pair(first = p.second, second = p.first)

let swapped = swap(Pair(first = 1, second = "a"))
```

```console
$ lune --eval swapped ex6-3.lune
{ first = "a", second = 1 }
```

`Pair(first = p.second, ...)` の型引数は渡した値から推論されるので、構築側に型を書く必要はありません。

</details>

**演習 6-4**（★★★） 6.2節の `Tagged`（strict tag）と、`strict` なしの同型レコードを両方作り、`crash()` を `tag` に入れて構築したときの挙動の違いを、`:thunks` も使って説明してください。

<details><summary>解答</summary>

`strict` なしなら `l.note` は `"n"` を返し、`:thunks l` は `{ tag = <thunk>, note = ... }` — 地雷は触るまで無害です。`strict` 付きは `t.note` の時点で `RUN0006` — `t` の force がレコード構築を走らせ、構築が strict フィールドを評価するからです。「遅延の既定 + 明示的な正格化」という第4章の原則が、データ設計にそのまま現れています。

</details>

---

**より正確には** — レコードの構文・型付け・遅延の規則は `documents/RECORD_FIELD_SPEC.md`（update / pattern が §7・§6 で将来対応と明記されています）。この章のコード例は `books/examples/ch06/` にあり、すべて実際の CLI で検証されています。
