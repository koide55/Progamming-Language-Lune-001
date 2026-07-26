# 第10章 モジュール

プログラムが育つと、1つのファイルに収まらなくなります。この章では Lune のプログラムを複数ファイルに分ける方法 — **モジュール**を学びます。

v0.1 のモジュール機構は意図的に小さいものです。パッケージ管理も、公開/非公開の制御も、名前空間アクセスもありません。あるのは「ファイルを分けて、読み込む」だけ。それでも、この最小の道具立てには覚えるべき規則が4つあり、間違えたときにはちゃんと専用の診断（`MOD` 族、第11章）が出ます。

## 10.1 module 宣言 — ファイルの名札

第1章から書き写してきた1行目を、ようやく主役にします。

```lune
module geometry
```

Lune のソースファイルは、自分がどのモジュールなのかを宣言します。そして**宣言はファイルの位置と一致していなければなりません** — `geometry.lune` なら `module geometry`、`util/text.lune` なら `module util.text` です。ドットがディレクトリの区切りに対応します。

```lune
module util.text

def shout(s: String): String =
    s + "!"
```

つまりモジュール名は、ファイルへの道順そのものです。名札が中身と食い違っていると、読み込む側で叱られます（10.5節）。

なお、`--eval` や `--check` に直接渡す**入口のファイル**だけは、宣言とパスの一致を求められません（本書がこれまで `module hello` を色々な場所に置けたのはこのためです）。

## 10.2 import — 名前を持ってくる

読む側は `import` です。`main.lune`:

```lune
module main
import geometry
import util.text

let area = circleArea(1.0)

let banner = shout("area")
```

```console
$ lune --eval area main.lune
3.14159
$ lune --eval banner main.lune
"area!"
```

`import geometry` と書くと、`geometry.lune` のトップレベル宣言（`def`・`let`・`type`・`record`）が**そのまま自分の環境に入ります**。`geometry.circleArea(...)` ではなく `circleArea(...)` と、非修飾で呼べていることに注目してください。

修飾して呼ぶことは、v0.1 ではできません。

```text,diagnostic
lune> let a = geometry.circleArea(1.0)
error[TYP0001]: 未定義の名前: geometry
   = help: 詳しくは `lune explain TYP0001 --lang ja` を実行してください
```

`geometry` という名前の値は存在しない — import が運んでくるのは中身の名前だけ、というわけです。裏を返せば、**別々のモジュールが同じ名前を定義していると衝突します**。v0.1 では名前を短くしすぎない（`total` より `cartTotal`）のが自衛策です。

`module` 宣言と `import` の行は、間に空行を挟まず続けて書くのが正準形です（`lune fmt` がこの形に整えます。第12章）。

## 10.3 分け方の作法

どう分けるか。v0.1 の道具立てで実際に効くのは、次の2つの発想です。

**データとその操作をまとめる**。レコードや ADT の定義と、それを扱う関数を同じモジュールに置きます。演習 10-2 で作る `shop/items.lune` がこの形です。

```lune
module shop.items

record Item:
    name: String
    price: Int

def priceOf(item: Item): Int =
    item.price

def total(items: List[Item]): Int =
    fold(map(items, priceOf), 0, fn a x -> a + x)
```

**汎用の道具を切り出す**。文字列や数値のユーティリティのように、どこからでも呼ばれるものを `util.text` のような場所へ。

逆に、v0.1 では**やらないほうがよい**分け方もあります。「実装を隠すために分ける」— 公開/非公開の制御がないので、分けても全部見えます。「循環しそうな相互参照を分ける」— 次節のとおり、循環は禁止です。

## 10.4 循環 import は検出される

`cycle_a` が `cycle_b` を import し、`cycle_b` が `cycle_a` を import したらどうなるか。

```console
$ lune --check cycle_a.lune
```

```text,diagnostic
error[MOD0002]: モジュールの循環 import を検出しました: cycle_a.lune -> cycle_b.lune -> cycle_a.lune
  --> cycle_b.lune:2:1
  |
2 | import cycle_a
  | ^^^^^^ この import が循環を閉じている
   = help: 詳しくは `lune explain MOD0002 --lang ja` を実行してください
```

診断が**循環の経路をそのまま**（`cycle_a → cycle_b → cycle_a`）見せ、しかも「輪を閉じた import」を名指ししてくれます。どこを切ればよいか一目で分かる形です。

なぜ禁止なのか。Lune は依存モジュールを**先に**型検査して評価します（`main` を検査する前に `geometry` を検査する）。循環があると「先」が決められません。第4章で `let x = x + 1` が `RUN0005` になったのと同じ理屈が、ファイルの粒度で現れたものです。

直し方は3つ。共通部分を第3のモジュールに抜き出す、依存の向きを片方だけに直す、あるいは2つを1つのファイルに戻す（同じファイル内の相互参照は問題ありません）。

## 10.5 モジュールが見つからないとき — 探索の順番

`import foo.bar` は `foo/bar.lune` を探します。探す場所は3つ、この順です。

1. 入口ファイルのあるディレクトリ
2. カレントディレクトリ
3. `--module-path` で足したディレクトリ（複数指定可）

3番目が便利なのは、共有ライブラリを別ディレクトリに置きたいときです。`lib/shared.lune`（`module shared`）を `usesshared.lune` から使う例:

```console
$ lune --check usesshared.lune
error[MOD0001]: モジュールが見つかりません: shared
$ lune --module-path lib --check usesshared.lune
type check OK
$ lune --module-path lib --eval answer usesshared.lune
42
```

見つからないときの診断は、**探した場所を教えてくれます**。

```text,diagnostic
error[MOD0001]: モジュールが見つかりません: nothere
  --> missing.lune:2:1
  |
2 | import nothere
  | ^^^^^^ 対応する .lune ファイルが見つからない
   = hint: 検索した場所: .
   = help: 詳しくは `lune explain MOD0001 --lang ja` を実行してください
```

（`検索した場所` は実際には絶対パスで表示されます。紙面では省略しています。）

ファイルは見つかったのに名札が違う場合は、別の診断です。`mismatch.lune` の中身が `module totally.different` だったとき:

```text,diagnostic
error[MOD0003]: module 宣言の不一致: mismatch のはずが totally.different でした
  --> mismatch.lune:1:1
  |
1 | module totally.different
  | ^^^^^^ モジュール名が import パスと一致しない
   = hint: 宣言を `module mismatch` に直すか、`totally.different` として import してください
   = help: 詳しくは `lune explain MOD0003 --lang ja` を実行してください
```

hint が**両方向の直し方**（名札を直す / import を直す）を示していることに注目してください。どちらが正しいかは設計判断なので、機械は決めずに両方を並べる — 第11章で学ぶ「hint は原因と対処」の good example です。

## 10.6 外部 import — java.* と std.*

最後に、Lune のファイルを指さない import があります。

```lune
module basics
import java.time.LocalDate

def today(): String =
    LocalDate.now().toString()
```

`java.*`・`javax.*`・`kotlin.*`・`std.*` で始まる import は**外部 import**として扱われ、ファイル解決されません。型検査は末尾の名前（`LocalDate`）を `Any` として登録するだけなので、この定義は型検査を通ります — が、実際に呼び出せば実行時に失敗します。JVM 連携は将来仕様（付録E）で、v0.1 では「構文だけ受け付ける」段階です。

`Any` として通ってしまう以上、外部 import は型検査の保護が効かない領域です。v0.1 で書くプログラムでは使わないのが賢明です。

> **壊してみよう** — この章の3つの `MOD` 診断のうち、`MOD0001`（見つからない）と `MOD0003`（名札不一致）を自分で出してみてください。片方から他方へ移る実験もできます: `import nothere` のまま `nothere.lune` を作り、中身を `module wrong.name` と書けば、`MOD0001` が `MOD0003` に変わります。
>
> ```text,diagnostic
> error[MOD0003]: module 宣言の不一致: nothere のはずが wrong.name でした
>   --> nothere.lune:1:1
>   |
> 1 | module wrong.name
>   | ^^^^^^ モジュール名が import パスと一致しない
>   = hint: 宣言を `module nothere` に直すか、`wrong.name` として import してください
>   = help: 詳しくは `lune explain MOD0003 --lang ja` を実行してください
> ```
>
> 「ファイルを見つける」と「名札を照合する」が別の段階だと体感できます。なお `module something.else` と書くと `else` が予約語なので構文エラー（`PRS0002`）— モジュール名にキーワードは使えません。

## まとめ

| 概念 | 一言で |
| --- | --- |
| `module a.b` | 名札。`a/b.lune` と一致必須（入口ファイルは例外） |
| `import a.b` | 相手のトップレベル宣言が自分の環境に入る（非修飾で使う） |
| 名前空間アクセス | `a.b.f()` は未対応。名前の衝突には自分で気をつける |
| 正準形 | `module` と `import` は空行を挟まず続ける |
| 循環 | `MOD0002`。依存は先に評価されるので輪は作れない |
| 探索順 | 入口ファイルの場所 → カレント → `--module-path` |
| 診断 | `MOD0001` 見つからない（探した場所つき）/ `MOD0003` 名札不一致（両方向の hint） |
| 外部 import | `java.*` `std.*` などは `Any` 登録のみ。v0.1 では実質使えない |

## 演習問題

**演習 10-1**（★） `import nothere` と書いたファイルを作って `MOD0001` を出し、次に `nothere.lune` を作って中身を `module wrong.name` にして `MOD0003` に変えてください。

<details><summary>解答</summary>

本文 10.5 節と「壊してみよう」の実例そのままです。`MOD0001` の hint は「探した場所」、`MOD0003` の hint は「名札を直す / import を直す」の2択。ファイル解決 → 名札照合の順に検査が進んでいることが、診断の変化から読み取れます。

</details>

**演習 10-2**（★★） 第6章の `Item` レコードと集計処理を `shop/items.lune`（`module shop.items`）に切り出し、別ファイルの `main` から使って合計を求めてください。

<details><summary>解答</summary>

```lune
module shop.items

# 演習 10-2: データとその操作をモジュールに切り出す。
record Item:
    name: String
    price: Int

def priceOf(item: Item): Int =
    item.price

def total(items: List[Item]): Int =
    fold(map(items, priceOf), 0, fn a x -> a + x)
```

```lune
module shop_main
import shop.items

# import した名前は非修飾で使える。Item も priceOf も total も。
let cart = [Item(name = "pen", price = 120), Item(name = "note", price = 200)]

let sum = total(cart)
```

```console
$ lune --eval sum shop_main.lune
320
```

`record Item` も import で運ばれてくるので、使う側は `Item(name = ..., price = ...)` と普通に構築できます。型・関数・値の区別なく、トップレベル宣言はすべて渡ってきます。

</details>

**演習 10-3**（★★） `lib/` ディレクトリに `module shared` のファイルを置き、`--module-path` を使って読み込んでください。`--module-path` を付けない場合との違いも確認すること。

<details><summary>解答</summary>

本文 10.5 節のとおりです。付けなければ `MOD0001`、付ければ通ります。`lib/shared.lune` は `module shared`（`module lib.shared` ではない）である点に注意 — `--module-path lib` は「`lib` を探索の起点にする」という指定なので、`lib` はモジュール名の一部になりません。

</details>

**演習 10-4**（★★★） 2つのモジュールで循環を作って `MOD0002` を出し、そのうえで共通部分を第3のモジュールに抜き出して解消してください。

<details><summary>解答</summary>

`cycle_a` ⇄ `cycle_b` で循環を作れます（本文 10.4 節）。解消は、両者が必要とする定義を `common.lune` に移し、`cycle_a` と `cycle_b` の両方が `common` だけを import する形にします。依存グラフが「輪」から「木」に変わるので、評価順が決まるようになります。診断が経路（`a -> b -> a`）を見せてくれるので、どの辺を切るかの判断はそこから始めるとよいでしょう。

</details>

**演習 10-5**（★） `import java.time.LocalDate` を書いたファイルは型検査を通ります。なぜでしょうか。また、それが安全でないのはなぜでしょうか。

<details><summary>解答</summary>

外部 import は末尾名 `LocalDate` を `Any` として登録するだけで、実体を解決しないからです（10.6節）。`Any` は何にでも使えてしまうので、`LocalDate.nonexistentMethod()` のような誤りも型検査を通り抜け、実行時まで問題が見つかりません。型検査の保護が効かない — v0.1 で外部 import を避ける理由です。

</details>

---

**より正確には** — 探索 root の決定、外部 import の判定、読み込み順と循環検出の規範は `documents/MODULE_LOADING_SPEC.md`。`MOD` 族の診断は `documents/ERROR_INDEX_JA.md` にも収録されています。この章のコード例は `books/examples/ch10/` にあり、すべて実際の CLI で検証されています。
