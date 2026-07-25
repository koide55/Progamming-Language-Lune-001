# 第4章 遅延評価 — Lune の心臓部

ほとんどのプログラミング言語は、書いた順に計算します。`let x = 重い計算` と書けば、その行で重い計算が走る — これを**正格評価**といいます。Lune は違います。**値は、必要になるまで計算されません**。これを**遅延評価**といい、Lune のあらゆる設計判断の根にある性質です。

遅延評価は「初学者の罠」と言われることがあります。いつ計算が走るのか見えないからです。Lune の答えは、隠すことではなく**見えるようにする**ことでした。この章では REPL の `:thunks` と `:trace` という2つの観察道具を使って、評価が起きる瞬間を自分の目で確かめながら進みます。信じる必要はありません。すべてその場で観察できます。

## 4.1 let は約束である

第1章で、`let` に対して REPL が `ok` としか言わないのを見ました。値を表示しないのは、**まだ値がない**からです。確かめましょう。ここで観察用の組み込み関数 `crash()` を紹介します。評価されると必ず実行時エラーになる、いわば地雷です。

```text
lune> let boom = crash()
ok
lune> boom
error[RUN0006]: crash() が評価されました
   = help: 詳しくは `lune explain RUN0006 --lang ja` を実行してください
```

地雷を束縛した行では、何も起きませんでした。爆発したのは `boom` を**使った**瞬間です。

`let name = 式` は「命令」ではなく「約束」です — 「`name` の値が必要になったら、この式で計算する」という。正格な言語の `let` が領収書だとすれば、Lune の `let` は注文票です。

## 4.2 サンク — 約束の中身

この「まだ計算していない式」の入れ物を**サンク**（thunk）と呼びます。サンクは式とその環境を閉じ込めていて、次の3つの状態のどれかにあります。

| 状態 | 意味 |
| --- | --- |
| `unevaluated` | まだ一度も必要とされていない |
| `evaluated = 値` | 計算済み。値を記憶している |
| `failed = エラー` | 計算したら失敗した。失敗を記憶している |

REPL の `:thunks` コマンドは、束縛の状態を**評価を一切起こさずに**覗きます。サンクの一生を観察しましょう。

```text
lune> let x = 1 + 1
ok
lune> :thunks x
x : unevaluated
lune> x
2 : Int
lune> :thunks x
x : evaluated = 2
```

`1 + 1` は、`x` を参照した瞬間に計算されました。先ほどの `boom` はどうなっているでしょう。

```text
lune> :thunks boom
boom : failed = error[RUN0006] crash() が評価されました
```

失敗も記憶されています。この意味はあとで（4.5節）はっきりします。

> **用語** — サンクを評価させることを「**force する**（強制する）」といいます。「`x` を force する」＝「`x` の約束を今すぐ果たさせる」です。

## 4.3 いつ評価されるのか — :trace で見る

では、force はいつ起きるのでしょうか。`:trace on` を打つと、REPL は force が起きるたびに実況してくれます。

```text
lune> :trace on
trace on
lune> let x = 1 + 1
ok
lune> x + 1
force x + 1
  force 1 + 1
  => 2
=> 3
3 : Int
```

読み方はこうです。

- `force 式` — その式のサンクの評価に入った（インデントは入れ子の深さ）
- `=> 値` — 対応する force が完了した

`let x = 1 + 1` の行ではトレースに**何も出ていない**ことに注目してください。宣言は force を起こさないのです。`x + 1` を打った瞬間、まず式全体が force され、その中で `x` の中身 `1 + 1` が force されました。

もう一度 `x` を使うと、3つ目のイベントが現れます。

```text
lune> x
force x
  memo 1 + 1 => 2
=> 2
2 : Int
```

`memo` は「計算済みの値に当たったので、再計算せずそれを使った」という印です。

大まかには、**値が「見られる」場所で force が起きます**。算術や比較の引数、`if` の条件、`match` の対象、そして REPL やファイル実行での表示。正確な一覧は付録Aに譲りますが、実務上は `:trace` に聞くのが一番確実です。

同じトレースはファイル実行でも使えます。`trace_demo.lune`:

```lune
module trace_demo

let x = 1 + 1

let answer = x + x
```

```console
$ lune --eval answer --trace trace_demo.lune
force x + x
  force 1 + 1
  => 2
  memo 1 + 1 => 2
=> 4
4
```

`x` は2回使われていますが、計算は1回だけ。2回目は `memo` です（トレースは stderr に出るので、リダイレクトすれば値と分離できます）。

## 4.4 引数も遅延される — 制御構文が自作できる

遅延されるのは `let` だけではありません。**関数の引数も、デフォルトでサンクとして渡されます**。

```text
lune> def first(a: Int, b: Int): Int =
...     a
...
ok
lune> first(10, crash())
10 : Int
```

`crash()` を渡したのに爆発しません。`b` は本体で使われないので、force される機会がなかったのです。

これは単なる省エネ以上の意味を持ちます。**制御構文が普通の関数で書ける**のです。ファイル `myif.lune`:

```lune
module myif

# 引数はデフォルトで遅延される。制御構文を自分で定義できる。
def myIf(c: Bool, a: Int, b: Int): Int =
    if c then a else b

def myAnd(a: Bool, b: Bool): Bool =
    if a then b else false

let taken = myIf(true, 1, crash())

let skipped = myAnd(false, crash())
```

```console
$ lune --eval taken myif.lune
1
$ lune --eval skipped myif.lune
false
```

`myIf` は選ばれなかった側を評価しません。`myAnd` は左が `false` なら右を見ません — 短絡評価です。正格な言語では、`&&` や `if` が短絡するのは言語が特別扱いしているからで、同じものをユーザーが関数として書くことはできません。Lune では、`if` も `&&` も原理的には「ただの関数」で再現できます。言語の芯が小さくて済むのは、遅延評価のおかげです。

## 4.5 メモ化 — 二度は計算しない

4.3節の `memo` をきちんと確かめましょう。ここで2つ目の観察道具、`tick()` を紹介します。呼ばれるたびに内部カウンタを 1 増やしてその値を返す組み込み関数で、相棒の `tickCount()` はカウンタを増やさずに現在値を読みます。「計算が何回走ったか」の目撃者です。

```text
lune> let t = tick()
ok
lune> tickCount()
0 : Int
lune> t
1 : Int
lune> t
1 : Int
lune> tickCount()
1 : Int
```

束縛しただけではカウンタは 0 のまま。`t` を初めて使った時に 1 回だけ走り、2回目の `t` は記憶された値を返しました。**サンクの評価は高々一度**です。

失敗も同じです。4.2節で `failed` 状態が「失敗を記憶している」と言いました。証拠をお見せします。

```text
lune> let bad = tick() + crash()
ok
lune> tickCount()
0 : Int
lune> bad
error[RUN0006]: crash() が評価されました
   = help: 詳しくは `lune explain RUN0006 --lang ja` を実行してください
lune> tickCount()
1 : Int
lune> bad
error[RUN0006]: crash() が評価されました
   = help: 詳しくは `lune explain RUN0006 --lang ja` を実行してください
lune> tickCount()
1 : Int
```

2回目の `bad` も同じエラーを出しましたが、カウンタは 1 のまま — **失敗した計算は再実行されていません**。記憶していた失敗を再送しただけです。

このおかげで、Lune の変数はいつ何度読んでも同じ結果（同じ値、または同じ失敗）になります。「読むタイミングで結果が変わる」ことがないので、遅延がプログラムの意味を壊さないのです。

## 4.6 正格化の道具箱

デフォルトは遅延。でも「今すぐ評価したい」場面はあります。Lune は明示的なオプトアウトの道具を段階別に揃えています。

| 道具 | 書く場所 | 意味 |
| --- | --- | --- |
| `strict let x = 式` | 束縛 | 束縛した瞬間に評価する |
| `strict x: T`（略記 `!x`） | 関数の引数 | 呼び出しの瞬間に評価する |
| `strict field: T` | コンストラクタのフィールド | 構築の瞬間に評価する |
| `seq a b` | 式 | `a` を評価してから `b` を返す |
| `deepForce x` | 式 | `x` を中身まで残らず評価する |
| `lazy 式` / `force 式` | 式 | 遅延を型 `Lazy[T]` として持ち歩く |

**strict let** — 束縛時に評価します。`:thunks` で見ると、もはやサンクですらありません。

```text
lune> strict let s = tick()
ok
lune> tickCount()
1 : Int
lune> :thunks s
s : value = 1
```

**strict 引数** — 4.4節の `first` を正格引数で書き直すと、使わない引数でも呼び出し時に評価されます。

```text
lune> def strictFirst(strict a: Int, strict b: Int): Int =
...     a
...
ok
lune> strictFirst(10, crash())
error[RUN0006]: crash() が評価されました
   = help: 詳しくは `lune explain RUN0006 --lang ja` を実行してください
```

**strict フィールド** — コンストラクタのフィールドも通常は遅延です（`Box(crash())` を作っても爆発しない）が、`strict` を付ければ構築時に評価されます。

```lune
module point

# strict 付きの正格フィールドは、構築の時点で評価される。
type Point =
    | Point(strict x: Int, strict y: Int)

let p = Point(crash(), 0)
```

```console
$ lune --eval p point.lune
error[RUN0006]: crash() が評価されました
   = help: 詳しくは `lune explain RUN0006 --lang ja` を実行してください
```

「不正な値を持った `Point` は一瞬たりとも存在させない」— データ型の設計道具として第5〜6章で再登場します。

**seq** — `seq a b` は「`a` を評価してから `b` を返す」。評価の順序だけを制御したいときに使います。

```text
lune> let a = tick()
ok
lune> let answer = seq a 42
ok
lune> answer
42 : Int
lune> :thunks a
a : evaluated = 1
```

`answer` を使った瞬間、値としては関係のない `a` が道連れで評価されました。

**deepForce** — force は普段、値の「外側」までしか評価しません。中身まで残らず評価したいときは `deepForce` です。

```text
lune> let pair = (tick(), tick())
ok
lune> :thunks pair
pair : unevaluated
lune> deepForce pair
(2, 3) : Tuple[Int, Int]
lune> :thunks pair
pair : evaluated = (2, 3)
```

**lazy / force** — 「すべてが遅延なのに、なぜ `lazy` が要るの?」と思うかもしれません。`lazy 式` は遅延を**型として**持ち歩くための道具です。

```text
lune> let delayed = lazy (40 + 2)
ok
lune> :type delayed
delayed : Lazy[Int]
lune> force delayed
42 : Int
```

`Int` と `Lazy[Int]` は別の型です。関数の戻り値やデータ構造のフィールドに `Lazy[T]` と書けば、「これはまだ計算されていないかもしれない」という事実が型シグネチャに現れ、受け取った側は `force` で明示的に開けることになります。暗黙の遅延を、契約に格上げする道具です。

## 4.7 底なしの再帰 — RUN0005

遅延評価の名物トラブルを見ておきましょう。「自分自身を使って自分を定義する」とどうなるか。

```lune
module recursive

let x = x + 1
```

`x` の値を知るには `x` の値が要る — 待っていても答えは出ません。まず型検査は、この素直な形を入り口で弾きます（定義中の名前はまだスコープにないので、未定義名になります）。

```console
$ lune --check recursive.lune
```

```text,diagnostic
error[TYP0001]: 未定義の名前: x
  --> recursive.lune:3:9
  |
3 | let x = x + 1
  |         ^ この名前は定義されていない
   = help: 詳しくは `lune explain TYP0001 --lang ja` を実行してください
```

しかし循環は、静的検査をすり抜けて実行時に初めて現れることもあります。v0.1 の `--eval` は型検査を通さず直接実行するので、このファイルで体験できます。無限ループになるでしょうか?

```console
$ lune --eval x recursive.lune
```

```text,diagnostic
error[RUN0005]: 再帰的なサンク評価: この値の定義が自分自身の結果に依存しています
   = hint: 再帰的な値は計算できません。再帰関数 (`def`) として書くか、参照の循環を断ち切ってください
   = help: 詳しくは `lune explain RUN0005 --lang ja` を実行してください
```

なりません。**即座に検出されます**。仕組みは 4.2 節のサンク状態にあります。サンクは評価に入る時、内部的に「評価中」の印を付けます。評価の途中で同じサンクをもう一度 force しようとしたら、それは定義が自分自身に戻ってきたということ — 待つだけ無駄だと分かるので、その場で `RUN0005` を報告するのです。`lune explain RUN0005` がこの仕組みごと解説してくれます。

> **コラム: `<<loop>>`** — 遅延評価の本家 Haskell（GHC）も同種の検出を持っていますが、報告は `<<loop>>` という素っ気ない一言で、しかも検出できず本当にループすることもあります。Lune はこの検出を診断コード付きの教材にしました。「なぜ無限ループせずに済むのか」まで `explain` で学べます。

なお、**再帰関数は問題ありません**。

```text
lune> def fact(n: Int): Int =
...     if n == 0 then 1 else n * fact(n - 1)
...
ok
lune> fact(5)
120 : Int
```

`def` の本体は呼ばれるまで走らないので、`fact(n - 1)` は自分の定義を force しません。存在できないのは再帰的な**値**です。

## 4.8 遅延とどう付き合うか

道具は揃いました。最後に使いどころの指針です。

**遅延が効く場面:**

- **使わないかもしれない値** — デフォルト値、エラーメッセージ、分岐の片側。書くだけならタダです。
- **自作の制御構文・短絡するロジック**（4.4節）。
- **無限のデータ構造** — 遅延評価の白眉です。第8章をお楽しみに。

**正格を選ぶべき場面:**

- **順序が大事な副作用** — 出力が「表示に必要になった順」に走ると混乱します。IO は正格に（第9章）。
- **計測とデバッグ** — 「この行の実行時間」を測りたいのに計算が後ろへ逃げていく、という時は `strict let` や `seq` で釘を刺します。
- **サンクの積み上がり** — ループで巨大な「未評価の計算の塔」を育ててしまうことがあります。第8章の `fold` で再訪します。

そして迷ったら、**`:thunks` と `:trace` に聞く**。この章であなたが使った道具は、そのまま実戦のデバッグ道具です。

> **壊してみよう** — `0` で割る式を束縛して、サンクの一生を観察してください。
>
> ```text,diagnostic
> lune> let half = 1 / 0
> ok
> lune> half
> error[RUN0006]: ゼロ除算です
>    = hint: `/` の右オペランドが 0 に評価されました
>    = help: 詳しくは `lune explain RUN0006 --lang ja` を実行してください
> lune> :thunks half
> half : failed = error[RUN0006] ゼロ除算です
> ```
>
> 束縛では何も起きず（遅延）、使うと失敗し（force）、失敗が記憶されました（メモ化）。この章の全部が3行に入っています。

## まとめ

| 概念 | 一言で |
| --- | --- |
| 遅延評価 | 値は必要になるまで計算されない |
| サンク | 未評価の式の入れ物。`unevaluated` / `evaluated` / `failed` |
| force | サンクに評価を強制すること。値が「見られる」場所で起きる |
| メモ化 | 評価は高々一度。成功も失敗も記憶される |
| `:thunks` / `:trace` | 状態を覗く / force を実況する。迷ったらこれ |
| `strict let` / `strict 引数` / `strict フィールド` | 遅延のオプトアウト |
| `seq` / `deepForce` | 評価の順序と深さの制御 |
| `lazy` / `force` と `Lazy[T]` | 遅延を型で明示する |
| `RUN0005` | 再帰的な値は存在できない。関数にせよ |

## 演習問題

**演習 4-1**（★） 次を順に打つと、それぞれの行で何が表示されるでしょう。予想してから確かめてください。

```text
lune> let u = tick()
lune> let v = tick()
lune> v
lune> :thunks
lune> u
```

<details><summary>解答</summary>

```text
lune> let u = tick()
ok
lune> let v = tick()
ok
lune> v
1 : Int
lune> :thunks
u : unevaluated
v : evaluated = 1
lune> u
2 : Int
```

先に定義した `u` が 2 で、後から定義した `v` が 1 です。カウンタは**定義した順**ではなく**使った順**に増えます。評価の順序を決めるのは、プログラムの字面ではなく需要（demand）である — 遅延評価の核心です。

</details>

**演習 4-2**（★★） `myAnd`（4.4節）にならって、左が `true` なら右を評価せずに `true` を返す `myOr` を書いてください。`myOr(true, crash())` が爆発しないことが合格条件です。

<details><summary>解答</summary>

```lune
module answers

# 演習 4-2: 左が true なら右を評価せずに短絡する myOr。
def myOr(a: Bool, b: Bool): Bool =
    if a then true else b

let shortCircuited = myOr(true, crash())
```

```console
$ lune --eval shortCircuited ex4-2.lune
true
```

`if` が評価するのは条件 `a` だけ。選ばれた枝が `true`（リテラル）なら、`b` のサンクは触られもしません。

</details>

**演習 4-3**（★★） `let t = tick()` と `strict let s = tick()` を1つずつ定義し、`tickCount()` と `:thunks` で両者の違いを説明してください。

<details><summary>解答</summary>

定義直後に `tickCount()` を読むと 1 — `strict let` の分だけが走っています。`:thunks` で見ると `t : unevaluated` に対し `s : value = 1`。`s` はサンクを経由せず、束縛の時点で値になっています。`t` が計算されるのは、この後 `t` を初めて使った瞬間です。

</details>

**演習 4-4**（★★） リストの要素も遅延されます。では `let xs = [crash(), 1, 2]` に対して `length(xs)` は成功するでしょうか。予想してから確かめてください。

<details><summary>解答</summary>

```text
lune> let xs = [crash(), 1, 2]
ok
lune> length(xs)
3 : Int
```

成功します。`length` が数えるのはリストの**背骨**（要素の連なり）だけで、各**要素**の中身は force しません。「構造だけ評価して中身は評価しない」という区別は、第8章の無限リストを支える仕掛けそのものです。

</details>

**演習 4-5**（★★★・逆転問題） `RUN0005` を実際に出してください。そのうえで、同じファイルが `--check` では `RUN0005` ではなく `TYP0001` になる理由を説明してください。

<details><summary>解答</summary>

最小の再現は `let x = x + 1` を含むファイルを `--eval x` で実行することです（4.7節）。`--check` で `TYP0001` になるのは、型検査が「定義の右辺を検査する時点では、定義しようとしている名前はまだスコープにない」という規則で、自己参照を**未定義名**として入り口で弾くからです。型検査は名前の循環を静的に防ぎ、評価器は実行時に現れた循環を `RUN0005` で検出する — 二段構えの防御になっています。

</details>

---

**より正確には** — サンクの状態遷移と force 境界の完全な一覧は `documents/LAZY_EVALUATION_SPEC.md`、`:thunks` / `:trace` の表示仕様は `documents/REPL_SPEC.md` §5.1–5.2。`crash` / `tick` / `tickCount` は `documents/STANDARD_LIBRARY_SPEC.md` §8.1 の観察用ビルトインです。この章のコード例は `books/examples/ch04/` にあり、すべて実際の CLI で検証されています。
