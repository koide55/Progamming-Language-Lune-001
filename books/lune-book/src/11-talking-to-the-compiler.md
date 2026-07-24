# 第11章 エラーと対話する

ここまでの章で、あなたは30個近い診断に出会ってきました。タイポを名指しされ、足りない match のケースを反例つきで教わり、null の考慮漏れをコンパイル時に止められた。この章では、その体験を**体系**にします。

Lune にとって診断は「失敗の通知」ではなく、言語のユーザーインターフェースの半分です。すべての診断コードに教材としての解説が付いていること、それがテストで保証されていること — この設計に乗って、コンパイラを「うるさい門番」から「隣に座る家庭教師」に変えるのがこの章の目標です。

## 11.1 診断の解剖学 — 部品は6つ

第1章で軽く触れた診断の構造を、今度は完全に分解します。標本には、部品が全部そろっている `TYP0008`（第5章）を使いましょう。

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

| 部品 | この例では | 役割 |
| --- | --- | --- |
| 重大度 | `error` | `error`（検査が失敗する）か `warning`（通るが要注意） |
| コード | `TYP0008` | 診断の背番号。調べるための鍵（11.3節） |
| 要約 | `let の束縛に…` | 一行で「何がだめか」 |
| 場所とソース断片 | `--> refutable.lune:3:5` と `^^^^` | どこの、どの部分か |
| ラベル | `このパターンはマッチに失敗し得る` | `^^^^` が指す箇所の説明 |
| hint / help | `= hint: ...` ×2 | 直し方の提案と、詳しく学ぶ道 |

読み順のコツは「**要約 → ラベル → hint**」です。要約で何の話か掴み、ラベルでどこの話か特定し、hint で次の一手を得る。hint が複数あるときは、**原因 → 対処**の順に並んでいます（この例なら「None をカバーしていない」が原因、「match を使え」が対処）。

`warning` は検査を止めません。第5章の `TYP0009` で見たとおり、警告だけなら最後に `type check OK` が出て、検査は成功扱いです。ただし警告は「動くけれど、たぶん意図と違う」の印 — 放置しない習慣をつけましょう。

## 11.2 コード体系 — 7つの族と検査の段階

コードの頭3文字は**族**を表し、族はそのままコンパイラの**検査段階**に対応しています。ソースコードは上から順に、レイアウト → 字句 → 構文 → モジュール → 型の検問を通り、全部を通過したものだけが実行されます。

| 族 | 段階 | 例 | 主に出会う章 |
| --- | --- | --- | --- |
| `LAY` | レイアウト（インデント） | 不整合なインデント | 第2章 |
| `LXL` | 字句 | 知らない文字、閉じていない文字列 | 第2章 |
| `PRS` | 構文解析 | 予期しないトークン | 第2・6章 |
| `MOD` | モジュール解決 | 見つからない import、循環 | 第10章 |
| `TYP` | 型検査 | 未定義名、型不一致、網羅性 | 全域 |
| `REC` | レコード検査 | フィールドの過不足・重複 | 第6章 |
| `RUN` | **実行時** | 0除算、再帰サンク | 第4章 |

この表から2つのことが読み取れます。第一に、**手前の族ほど早く捕まる** — `LXL` のエラーが出ている間は、型の話はまだ始まってもいません。第二に、`RUN` だけが実行時です。`--check` が通っても `RUN` は出うる（第4章の `crash()` や 0 除算）— 型検査は多くを守りますが、すべてではありません。

コードは現在全部で 29 個。一覧は付録Cに、全コードの解説カタログは `documents/ERROR_INDEX_JA.md`（英語版は `ERROR_INDEX.md`）にあります。

## 11.3 explain — エラー番号は調べるためにある

診断コードの解説には、3つの入り口があります。

```console
$ lune explain TYP0007        # シェルから（本書の規約では --lang ja 込み）
```

```text
lune> :explain TYP0007        # REPL の中から
```

そして全部まとめて読みたければ `lune explain --index` — これが先ほどの `ERROR_INDEX_JA.md` の正体です（このファイルは索引コマンドの出力をそのまま保存したもので、古くなるとテストが落ちる仕組みになっています）。

各解説は「何が起きたか / 再現する最小の例 / 直し方」の3部構成で、第1章の `TYP0001` や第4章の `RUN0005` で読んだとおりです。存在しないコードを聞くと、聞けるコードの一覧が返ってきます。

```text
$ lune explain ZZZ9999
error: no explanation for diagnostic code 'ZZZ9999'
available codes: LAY0001, LAY0002, LXL0001, LXL0002, LXL0003, LXL0004, MOD0001, MOD0002, MOD0003, PRS0001, PRS0002, REC0001, REC0002, REC0003, REC0004, REC0005, REC0006, RUN0005, RUN0006, TYP0001, TYP0003, TYP0004, TYP0005, TYP0006, TYP0007, TYP0008, TYP0009, TYP0010, TYP0011
```

「エラー番号は覚えるものではなく、**調べるための鍵**」— これがコード体系の使い方です。

## 11.4 機械が直せるエラー — did-you-mean と lune fix

診断の中には、直し方が一意に決まるものがあります。その代表がタイポです。わざと2つ仕込んだ `typos.lune`:

```lune
module stats

let values = [3, 1, 4, 1, 5]

let total = fold(valeus, 0, fn a x -> a + x)

let count = lenght(values)
```

```console
$ lune --check typos.lune
```

```text,diagnostic
error[TYP0001]: 未定義の名前: valeus
  --> typos.lune:5:18
  |
5 | let total = fold(valeus, 0, fn a x -> a + x)
  |                  ^^^^^^ この名前は定義されていない
   = hint: もしかして `values` ですか?
   = help: 詳しくは `lune explain TYP0001 --lang ja` を実行してください
```

`--check` が報告するのは最初の1つだけですが、`lune fix` は hint を**機械的に適用し、直った結果をまた検査して**、直せるものがなくなるまで繰り返します。

```console
$ lune fix typos.lune
module stats

let values = [3, 1, 4, 1, 5]

let total = fold(values, 0, fn a x -> a + x)

let count = length(values)
```

`valeus` も `lenght` も、一度に両方直りました。`--write` を付ければファイルを直接書き換え、`--check` を付ければ「直せるものが残っていれば失敗する」CI 向けの検査になります。

```console
$ lune fix --check typos.lune
typos.lune: 2 auto-fixable issue(s)
```

一方、`fix` は**直せないものには手を出しません**。第2章の `annot.lune`（`let n: Int = "hello"`）に `fix` をかけても、ソースはそのまま出力されます。`Int` に直すべきか `"hello"` を変えるべきか、それは設計判断であって、機械には決められないからです。この線引きを覚えてください — **hint が一意なら機械の仕事、判断が要るなら人間の仕事**。

## 11.5 エラー駆動開発 — witness に導かれて書く

仕上げに、この本がずっと予告してきた開発スタイルを1本通しでやります。**先に骨組みを書いて、何が足りないかはコンパイラに聞く**のです。

お題はじゃんけん。「`a` は `b` に勝つか」を判定します。まず型と、確実に分かっている1ケースだけ書きます。

```text,diagnostic
lune> type Hand =
...     | Rock
...     | Paper
...     | Scissors
...
ok
lune> def beats(a: Hand, b: Hand): Bool =
...     match (a, b):
...         | (Rock, Scissors) -> true
...
error[TYP0007]: 網羅的でない match: (Paper, Rock) のケースがありません
  --> <repl:2>:2:5
  |
2 |     match (a, b):
  |     ^^^^^ パターン (Paper, Rock) がカバーされていない
   = hint: (Paper, Rock) のケースを追加するか、ワイルドカードケース `| _ -> ...` を追加してください
   = help: 詳しくは `lune explain TYP0007 --lang ja` を実行してください
```

コンパイラが**次に書くべき勝ち筋**を挙げてきました。`(Paper, Rock)` — 紙は石に勝つ。言われたとおり、勝ち筋を全部書きます。

```text,diagnostic
lune> def beats(a: Hand, b: Hand): Bool =
...     match (a, b):
...         | (Rock, Scissors) -> true
...         | (Paper, Rock) -> true
...         | (Scissors, Paper) -> true
...
error[TYP0007]: 網羅的でない match: (Rock, Rock) のケースがありません
  --> <repl:3>:2:5
  |
2 |     match (a, b):
  |     ^^^^^ パターン (Rock, Rock) がカバーされていない
   = hint: (Rock, Rock) のケースを追加するか、ワイルドカードケース `| _ -> ...` を追加してください
   = help: 詳しくは `lune explain TYP0007 --lang ja` を実行してください
```

今度は `(Rock, Rock)` — **あいこの存在**を指摘されました。勝ち筋以外はすべて「勝ちではない」ので、ワイルドカードで受けます。

```text
lune> def beats(a: Hand, b: Hand): Bool =
...     match (a, b):
...         | (Rock, Scissors) -> true
...         | (Paper, Rock) -> true
...         | (Scissors, Paper) -> true
...         | _ -> false
...
ok
lune> beats(Rock(), Scissors())
true : Bool
lune> beats(Scissors(), Rock())
false : Bool
```

振り返ってください。私たちは仕様の抜け（紙の勝ち筋、あいこ）を**一つも自力で思い出していません**。全部コンパイラが、具体的な反例の形で持ってきました。診断は読むものではなく、**TODO リストとして消化するもの** — これがエラー駆動開発です。

型を先に書くほど、コンパイラは良い質問をくれます。ADT で形を列挙し、match で骨組みを作り、`--check` を回す。埋め終わったら `fix` と `fmt` で仕上げる。この繰り返しが、Lune の開発の基本サイクルです。

> **壊してみよう** — `rps.lune` の `| _ -> false` を消して `--check` し、witness を確認したら、ワイルドカードではなく**あいこ3つと負け筋3つを列挙**して網羅してみてください。どちらの書き方にも利点があります: ワイルドカードは短く、列挙は `Hand` に手を足したとき（演習 5-1 の教訓）に守られます。

## まとめ

| 概念 | 一言で |
| --- | --- |
| 診断の部品 | 重大度 / コード / 要約 / 場所+ラベル / hint / help。要約→ラベル→hint の順に読む |
| hint の並び | 原因 → 対処 |
| 7つの族 | LAY・LXL・PRS・MOD・TYP・REC は実行前、RUN だけ実行時 |
| `lune explain` / `:explain` / `--index` | 全29コードに解説。番号は調べるための鍵 |
| `lune fix` | hint が一意なら機械が直す（反復適用）。`--write` / `--check` |
| fix の線引き | 機械が決められない修正には手を出さない |
| エラー駆動開発 | 骨組み → `--check` → witness を TODO として消化 |

## 演習問題

**演習 11-1**（★） 11.1節の標本（`TYP0008`）について: この診断の「原因を述べる hint」と「対処を述べる hint」はそれぞれどれですか。また、なぜ `--check` の結果は失敗（exit 非0）になるのですか。

<details><summary>解答</summary>

原因は1つ目（「このパターンは None をカバーしていません」）、対処は2つ目（「`match` を使って…場合分けしてください」）。失敗になるのは重大度が `error` だからです。`warning`（TYP0009 など）だけなら検査は成功し、`type check OK` が出ます。

</details>

**演習 11-2**（★★） `typos.lune` と `annot.lune`（第2章）のそれぞれに `lune fix` をかけると何が起きるか、予想してから確かめてください。

<details><summary>解答</summary>

`typos.lune` は2つのタイポが両方直った完全なソースが出力されます。`annot.lune` は**そのまま**出力されます — `TYP0003` には機械的に適用できる一意の hint がないからです。`fix --check` を使うと、前者は「2 auto-fixable issue(s)」で失敗（exit 非0）、後者は「直せるものがない」ので成功します。

</details>

**演習 11-3**（★★） `beats` を部品にして、`"win"` / `"lose"` / `"draw"` の3値を返す `judge(a, b)` を書いてください。

<details><summary>解答</summary>

```lune
def judge(a: Hand, b: Hand): String =
    if beats(a, b):
        "win"
    elif beats(b, a):
        "lose"
    else:
        "draw"
```

```console
$ lune --eval tied ex11-3.lune
"draw"
```

勝敗の**規則**は `beats` に1箇所だけ書き、`judge` はそれを2回聞くだけ — 規則を2箇所に書かないのが要点です。

</details>

**演習 11-4**（★★★・逆転総合） `LXL`・`PRS`・`TYP`・`REC`・`RUN` の5つの族から1つずつ、診断を出す最小のコードを書いてください（この本でまだ見せていないコードが出せたらボーナス点）。

<details><summary>解答</summary>

例: `let x = $1`（LXL0001）、`let a = (1`（PRS 系 — 閉じていない括弧）、`1 + true`（TYP0003）、`User(name = "X", name = "Y", age = 1)`（REC0004、第6章）、`--eval` で `1 / 0` を含む束縛を評価（RUN0006）。ボーナス例: `###` を閉じずにファイルを終えると `LXL0003`（閉じていないブロックコメント）が出ます。全29コードの索引（付録C / `ERROR_INDEX_JA.md`）と照合してみてください。

</details>

**演習 11-5**（★） `lune explain --index` の出力を眺めて、まだ本書に登場していない診断コードを1つ見つけ、その解説を読んでください。

<details><summary>解答</summary>

例えば `MOD0002`（循環 import）はまだ登場していません — 第10章のお楽しみです。`LAY0002`（対応しない閉じ括弧）や `REC0001`（レコード宣言のフィールド重複）も、狙って出すにはひと工夫要ります。

</details>

---

**より正確には** — 診断モデルと表示形式の規範は `documents/ERROR_DIAGNOSTICS_SPEC.md`、全コードのカタログは `documents/ERROR_INDEX_JA.md`（`lune explain --index --lang ja` で再生成）、fix の適用規則は `documents/ERROR_DIAGNOSTICS_SPEC.md` §9.5。この章のコード例は `books/examples/ch11/` にあり、すべて実際の CLI で検証されています。
