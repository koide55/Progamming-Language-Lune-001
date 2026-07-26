# 第12章 REPL・整形・検査

第11章では診断との対話を学びました。この章は道具そのものの話です — REPL のコマンド一覧、正準フォーマッタ `lune fmt`、CLI の検査系フラグ、そしてそれらを CI に並べるレシピ。

一つ確認しておきたいことがあります。Lune の道具はどれも**答え合わせのための道具**です。型が分からなければ `:type`、評価の順序が怪しければ `:trace`、整形で揉めたら `fmt`。頭の中で考え込む代わりに機械に聞く癖をつけると、Lune は驚くほど素直な言語になります。

## 12.1 REPL コマンド全一覧

`:help` が全部教えてくれます。

```text
lune> :help
commands: :help, :quit, :q, :env, :type NAME, :thunks [NAME], :trace [on|off], :lang [en|ja], :explain CODE [en|ja]
```

| コマンド | 何をするか | 学んだ章 |
| --- | --- | --- |
| `:help` | この一覧 | — |
| `:quit` / `:q` | 終了 | 第1章 |
| `:env` | いま見えている名前と型を全部並べる | 本章 |
| `:type NAME` | 名前の型を答える | 本章 |
| `:thunks [NAME]` | 束縛の評価状態を、評価せずに見せる | 第4章 |
| `:trace [on\|off]` | force の実況中継を切り替える | 第4章 |
| `:lang [en\|ja]` | 診断の言語を切り替える | 第1章 |
| `:explain CODE` | 診断コードの解説 | 第11章 |

複数行の入力は、行末が `=` や `:` や `->` で終わると継続に入り（`...` プロンプト）、空行で確定します。第1章から使ってきたあの動きです。

端末で起動していれば、readline 風の行編集と履歴（上下矢印）も効きます。環境が対応していれば履歴は `~/.lune_history` に保存され、前のセッションの実験を呼び戻せます。

## 12.2 :type と :env — 型に聞く

`:type` は本書で最も使われた道具かもしれません。定義した関数にも、プレリュードの関数にも効きます。

```text
lune> def add(a: Int, b: Int): Int =
...     a + b
...
ok
lune> :type add
add : Int -> Int -> Int
```

レコードのコンストラクタに聞くと、フィールド名まで含んだ形が返ります。

```text
lune> :type User
User : (name: String, age: Int) -> User
```

第6章で「レコードは名前付き構築が必須」と学びましたが、その事実が型そのものに書かれているわけです。

`:env` はいま見えている名前を**全部**並べます。プレリュードも含むので長いリストになりますが、末尾に自分の定義が混ざって見えるのが面白いところです。

```text
lune> let x = 40
ok
lune> :env
Cons : [T] T -> List[T] -> List[T]
Err : [T, E] E -> Result[T, E]
...
take : [T] List[T] -> Int -> List[T]
takeWhile : [T] List[T] -> (T -> Bool) -> List[T]
tick : () -> Int
x : Int
zip : [T] List[T] -> List[U] -> List[Tuple[T, U]]
```

「プレリュードに何があったか」を思い出したいときの手っ取り早い索引です（正式な一覧は付録B）。

知らない名前を聞くと、当然のように叱られます。

```text,diagnostic
lune> :type nosuch
error[TYP0003]: 未定義の名前: nosuch
   = help: 詳しくは `lune explain TYP0003 --lang ja` を実行してください
```

（余談ですが、未定義の名前には専用コード `TYP0001` があるので、ここが `TYP0003` なのは実装の小さな取りこぼしです。診断コードの一貫性も、本来はテストで守るべきものです。）

## 12.3 lune fmt — 議論を終わらせる整形

インデントは2つか4つか、`fn a x -> a+x` に空白を入れるか。この種の議論に費やす時間を Lune はゼロにします。**正準形はひとつ**で、`lune fmt` がそこへ揃えます。

散らかったファイル `messy.lune`:

```lune
module messy



let   nums = [ 1,2 ,3 ]

# 合計を出す
def total( xs : List[Int] ) : Int =
      fold( xs, 0, fn a x -> a+x )

let answer=total(nums)
```

```console
$ lune fmt messy.lune
module messy

let nums = [1, 2, 3]

# 合計を出す
def total(xs: List[Int]): Int =
    fold(xs, 0, fn a x -> a + x)

let answer = total(nums)
```

余分な空行が1つに、括弧まわりの空白が整い、インデントは4つ、`#` コメントは位置ごと保たれました。

この整形には、2つの保証があります。

**冪等**（idempotent）— 一度整形した結果をもう一度整形しても、何も変わりません。「整形するたびに揺れる」ことがないので、CI に置いても安全です。

**意味を変えない** — `fmt` は AST（構文木）を整形して印字し、**自分の出力を読み直して構文木が一致するか確かめてから**結果を返します。もし一致しなければ、整形を諦めてエラーを出します（第2章の脚注で触れた入れ子 `let-in` のバグがまさにこれで捕まりました）。整形が黙ってプログラムを壊すことはありません。

使い方は3つのモードです。

```console
$ lune fmt FILE            # 整形結果を標準出力へ（元ファイルは変えない）
$ lune fmt --write FILE    # ファイルを整形して書き換える
$ lune fmt --check FILE    # 整形が必要なら失敗する（CI 用）
```

`--check` は差分があるとファイル名を挙げて終了コード 1 を返します。

```console
$ lune fmt --check messy.lune
would reformat messy.lune
```

制限が一つ。`###` で囲むブロックコメントを含むファイルは、まだ整形できません。

```console
$ lune fmt bc.lune
error: bc.lune: lune fmt does not support `###` block comments yet
```

整形されない（＝壊されない）だけなので安全側の挙動ですが、`fmt` を CI に置くなら `###` は避けて `#` を並べるのが今の作法です。

## 12.4 CLI の検査系フラグ

`lune` コマンドの主なフラグを、使う順に並べます。

| コマンド | 何をするか |
| --- | --- |
| `lune --repl` | REPL を起動 |
| `lune --check FILE` | 型検査だけして終わる（評価しない） |
| `lune --eval NAME FILE` | 束縛 NAME を評価して表示 |
| `lune --eval NAME --trace FILE` | 上に加えて force のトレースを stderr へ（第4章） |
| `lune --module-path DIR` | モジュール探索ルートを追加（第10章、繰り返し可） |
| `lune --tokens FILE` | 字句解析の結果（トークン列）を表示 |
| `lune explain CODE` | 診断コードの解説（第11章。`--index` で全部） |
| `lune fmt` / `lune fix` | 整形 / 自動修正（12.3節、第11章） |
| `--lang en\|ja` | 診断の言語（本書は `ja`）。既定は環境変数 `LUNE_LANG`、フラグが優先 |

`--tokens` は普段使う道具ではありませんが、レイアウト（インデント）の扱いを覗くのに便利です。第2章で「インデントは構文の一部」と言ったことの実物が見られます。

```console
$ lune --tokens geometry.lune
1:1	MODULE	'module'	None
1:8	IDENT	'geometry'	'geometry'
1:16	NEWLINE	''	None
3:1	DEF	'def'	None
3:5	IDENT	'circleArea'	'circleArea'
...
```

`--check` と `--eval` の関係も押さえておきましょう。**`--eval` は型検査を通しません** — 第4章で `RUN0005`（再帰サンク）を出せたのはこのためです。実行する前に検査したければ、`--check` を先に走らせるのが確実です。

存在しない束縛を `--eval` すると実行時エラーになります。

```console
$ lune --eval nosuch geometry.lune
error[RUN0006]: 未定義の変数: nosuch
```

## 12.5 小さな CI レシピ

道具を並べると、そのままプロジェクトの検査になります。終了コードは「問題があれば非0」で揃っているので、シェルの `&&` で繋げば1本のパイプラインです。

```bash
lune fmt --check src/*.lune && lune --check src/main.lune && lune fix --check src/*.lune
```

3つの意味はこうです。

1. `fmt --check` — 全ファイルが正準形か（整形漏れがないか）
2. `--check` — 型検査が通るか
3. `fix --check` — 機械が直せる問題（タイポなど）が残っていないか

終了コードの規則を整理しておきます。

| 状況 | 終了コード |
| --- | --- |
| 検査が通る | 0 |
| **警告だけ**（`TYP0009` など） | **0** |
| エラーがある | 1 |
| `fmt --check` で差分あり | 1 |
| `fix --check` で直せる問題あり | 1 |

注意すべきは2行目です。第5章で見たとおり、警告だけなら検査は成功します。警告も見逃したくなければ、出力に `warning` が現れたら落とす一手間が必要です。

```bash
lune --check src/main.lune 2>&1 | tee /tmp/out; ! grep -q warning /tmp/out
```

> **壊してみよう** — `messy.lune` を `fmt --write` で整形してから、もう一度 `fmt --check` を走らせてください。今度は何も言われないはずです（冪等の確認）。ついでに `fmt` した結果を自分の目で読み、自分の書き癖と正準形の差を数えてみるのも良い練習です。

## まとめ

| 道具 | 一言で |
| --- | --- |
| `:help` | REPL コマンドの一覧。迷ったらここ |
| `:type` / `:env` | 型に聞く / 見えている名前を全部並べる |
| `lune fmt` | 正準形へ整形。**冪等**で**意味を変えない**（再パースで自己検査） |
| `fmt` の3モード | 標準出力 / `--write` / `--check`（CI） |
| `fmt` の制限 | `###` ブロックコメントは未対応（安全に諦める） |
| `--check` vs `--eval` | `--eval` は型検査を通さない。検査したいなら `--check` を先に |
| `--tokens` | 字句とレイアウトの覗き窓 |
| CI レシピ | `fmt --check && --check && fix --check`。警告だけなら終了コードは 0 |

## 演習問題

**演習 12-1**（★） `messy.lune` を `fmt` にかけた結果を予想してから確かめてください。予想と違った箇所はどこですか。

<details><summary>解答</summary>

本文 12.3 節のとおりです。よく外れるのは「連続した空行が1つに詰められる」「`def total( xs : List[Int] ) : Int =` の括弧とコロンまわりの空白」「`a+x` に空白が入る」あたり。`#` コメントが消えずに残ることも確認してください。

</details>

**演習 12-2**（★） `:env` を使って、プレリュードに `zipWith` があることと、その型を確かめてください。第8章で使ったときの記憶と合っていますか。

<details><summary>解答</summary>

`zipWith : [T, U, V] List[T] -> List[U] -> (T -> U -> V) -> List[V]`。「2本のリストと、2引数の関数を受け取り、1本のリストを返す」— 第8章の移動平均（演習 8-3）でやったことが、型に書いてあります。`:type zipWith` でも同じ答えが得られます。

</details>

**演習 12-3**（★★） `:type` で確かめながら、`scale(factor, n)` から「3倍にする関数」を部分適用で作り、リストに `map` してください。途中で `:type scale(3)` のように部分適用の型も確かめること。

<details><summary>解答</summary>

```lune
module answers

# 演習 12-3: :type で確かめながら組み立てた、部分適用で作る道具。
def scale(factor: Int, n: Int): Int =
    factor * n

let double = scale(2)

let tripled = map([1, 2, 3], scale(3))

let doubled = map([1, 2, 3], double)
```

```console
$ lune --eval tripled ex12-3.lune
(3 6 9)
$ lune --eval doubled ex12-3.lune
(2 4 6)
```

REPL では `:type scale` が `Int -> Int -> Int`、`let triple = scale(3)` としてから `:type triple` が `Int -> Int`。第3章で読んだ「`->` は右結合」がそのまま観察できます。

</details>

**演習 12-4**（★★） 自分のプロジェクト（この本の演習ファイルでも構いません）に対して、12.5節の CI レシピを走らせてください。1つでも失敗するファイルを見つけたら、何が原因かを診断から説明してください。

<details><summary>解答</summary>

本書の `books/examples/` で試すなら、意図的に壊してあるファイル（`ch02/annot.lune` や `ch11/typos.lune` など）が引っかかります。`typos.lune` は `--check` でも `fix --check` でも落ちますが、意味が違います — 前者は「型検査が通らない」、後者は「機械が直せる問題が残っている」。同じファイルに対して**別の理由で**落ちていることを読み取れれば正解です。

</details>

**演習 12-5**（★・逆転問題） `lune fmt` が「整形を諦める」場面を作ってください。

<details><summary>解答</summary>

`###` で囲んだブロックコメントを含むファイルを `fmt` にかければ、`lune fmt does not support ### block comments yet` で諦めます（12.3節）。もう一つの諦め方は、フォーマッタ自身のバグで意味保存の自己検査に失敗する場合です（`formatter changed the program's meaning (internal bug)`）。後者を狙って出すのは難しいですが、見つけたらそれは報告すべきバグです — 実際、本書の執筆中に1件見つかりました。

</details>

---

**より正確には** — REPL の仕様は `documents/REPL_SPEC.md`（`:thunks` / `:trace` の表示形式を含む）、フォーマッタの保証と制限は `documents/FORMATTER_SPEC.md`、CLI の全フラグは付録D。この章のコード例は `books/examples/ch12/` にあり、すべて実際の CLI で検証されています。
