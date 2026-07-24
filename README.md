# Lune — the Lazy and Native programming language

コンパイラが教えてくれる、遅延評価の関数型入門言語。
エラーも、その解説も、母語で読めます。

> Lune is a teaching-first functional language: lazy by default, with diagnostics that speak your native language. If you prefer English, start with [documents/TUTORIAL_EN.md](documents/TUTORIAL_EN.md) — every diagnostic and explanation defaults to English.

**[▶ Playground(インストール不要)](https://koide55.github.io/lune-lang/playground/)** · [診断カタログ](https://koide55.github.io/lune-lang/playground/errors.html) · [チュートリアル](documents/TUTORIAL.md)

---

## プロローグ — 全員、部活に入ること

転校初日に知らされた校則がこれだった。**「全生徒、いずれかの部に所属すること」**。

運動部は続く気がしない。文化系の一覧を眺めていたら「プログラミング部」とある。パソコンで何か打っていれば終わる、いちばん楽そうなやつだ。僕は入部届を出した。

部室のドアには、こう書かれていた。

> **部訓: 必要になるまで、やらない。一度やったことは、忘れない。**

……楽そうな部、で合ってるよな?

## 入部初日 — さっそく間違える

プログラミング部にはいってみたら、部員は先輩3人だけ、男子は自分だけだった。はたしてやっていけるのかな？

「じゃあ転校生くん、まず書いてみて」と真知（まち）部長。見よう見まねで打ったら、初日からエラーを出した。

```lune
let count = 10
let total = cont + 5
```

```text
$ ./bin/lune --check --lang ja guide.lune
error[TYP0001]: 未定義の名前: cont
  --> guide.lune:2:13
  |
2 | let total = cont + 5
  |             ^^^^ この名前は定義されていない
   = hint: もしかして `count` ですか?
   = help: 詳しくは `lune explain TYP0001 --lang ja` を実行してください
```

身構えた僕に、部長は画面を指しながら言った。「読み方を教える。上から順に」

- `TYP0001` — エラーの出席番号(診断コード)。あとで調べるときの索引になる
- `^^^^` — 問題の場所そのもの。まずここを見る
- `= hint:` — 次の一手。**正解の候補まで書いてある**
- `= help:` — もっと深く知りたいときの案内

「**うちの部では、エラーは赤点じゃなくて教材**。読めるようになったら、もう半分書けるのと同じ」

思っていたのと違う。この部、楽じゃない。でも、理不尽でもなかった。

## 部員紹介 — 教えてくれる先輩たち

- **真知(まち)部長** — `match` の抜けを絶対に見逃さない。「`Blue` のケースがありません」と**反例つき**で指摘してくる(TYP0007)。書きすぎれば「そのケースには到達しません」(TYP0009)。null も `T?` の型として扱わせ、`?.` / `??` / フロー narrowing まで仕込んでくる。厳しいが、指摘には全部理由がある。
- **英美(えいみ)先輩** — 解説担当。全29の診断コードに「意味・発生する最小例・直し方」の詳解を用意している(`lune explain CODE`、REPL では `:explain`)。日本語でも英語でも説明できる(`--lang ja`)。全文は[診断カタログ](https://koide55.github.io/lune-lang/playground/errors.html)に貼り出されている。
- **直美(なおみ)先輩** — 赤ペンと清書の担当。typo は did-you-mean の候補で機械的に直してくれるし(`lune fix`)、提出前には正準スタイルに整えてくれる(`lune fmt`)。整形で意味が変わっていないことを再パースで検証してから返す、と聞いてこの部の本気度を理解した。

教わる流れは決まっている: **間違える → 読む → `explain` → `fix` → 確認**。チュートリアル第17章には「指定した診断をわざと出せたら正解」という逆転演習まであって、僕は初日にエラーの出し方から教わった。

## 部訓の意味 — 「必要になるまで、やらない」(遅延評価)

Lune の値は、必要になるまで計算されない。

```lune
let danger = crash()
let answer = 42
```

`answer` を評価しても `danger` は使われないから、`crash()` は実行されない。「サボりじゃないの。**必要なものを、必要なときに、一度だけ**。そして一度やったことは忘れない(メモ化)」と部長は言う。

信じられないなら目で見ればいい、と教わったのが REPL の `:trace` だ。

```text
lune> :trace on
trace on
lune> let y = x + 1
ok                       # 宣言では何も評価されない
lune> y * 10
force y * 10
  force x + 1            # y が必要になって初めて評価される
    memo 1 + 1 => 2      # x はメモ化済み。再計算されない
  => 3
=> 30
30 : Int
```

この校風なら、無限リストとも普通に付き合える。どこまで計算が進んだかは `:thunks` が見せてくれる。

```text
lune> let nat = naturalsFrom(1)
ok
lune> head(nat)
Some(1) : Option[Int]
lune> :thunks nat
nat : evaluated = Cons(1, <thunk>)   # 先頭だけ計算済み。続きは手つかず
```

## 放課後 — 部室はブラウザの中にもある

**<https://koide55.github.io/lune-lang/playground/>**

家に帰ってからも練習できるように、部室はブラウザの中にもある。処理系(Pure Python)が Pyodide 上でそのまま動くので、インストールは不要。実行・型チェック・整形・自動修正・explain・遅延評価のトレース・日本語/英語の切り替え、全部できる。

## 資料棚 — ドキュメント

- [チュートリアル(日本語)](documents/TUTORIAL.md) / [Tutorial (English)](documents/TUTORIAL_EN.md) — 全20章。遅延評価は第2〜6章でじっくり、エラー駆動学習は第17章
- [診断コード索引(日本語)](documents/ERROR_INDEX_JA.md) / [Error Index (English)](documents/ERROR_INDEX.md) — 自動生成、テストで同期を強制
- [言語仕様](documents/LANGUAGE_SPEC.md)ほか、[documents/](documents/README.md) に仕様書一式
- [普及戦略](documents/STRATEGY.md) — この部がどこへ向かうか

## 入部届 — はじめかた

必要なのは Python 3.12+ だけ。依存パッケージはありません。

```sh
git clone https://github.com/koide55/lune-lang.git
cd lune-lang

./bin/lune                                 # REPL(:help でコマンド一覧)
./bin/lune --check --lang ja file.lune     # 型チェック(日本語診断)
./bin/lune --eval answer file.lune         # ファイルの束縛を評価
./bin/lune --eval answer --trace file.lune # 遅延評価をトレース
./bin/lune explain TYP0007 --lang ja       # 診断コードの詳解
./bin/lune fmt --write file.lune           # 整形
./bin/lune fix --write file.lune           # typo の自動修正
```

書き味の見本は [samples/](samples/) にあります(ADT・match・レコード・パイプライン `|>`・nullable・無限ストリームなど)。

## 顧問の先生より — 開発者向け

処理系は `lune/` 以下の Pure Python(外部依存なし)。lexer → layout → parser → typechecker → evaluator の各層と、diagnostics / explanations / messages(英日メッセージカタログ)/ formatter / fixer / REPL で構成されています。

```sh
PYTHONPATH=. python3 -m unittest discover -s tests
```

テストは「発行されうる全診断コードに詳解があること」「詳解とメッセージに日本語訳があること」「生成物(診断カタログ)が陳腐化していないこと」まで強制します。間違いを教材にする部なので、自分自身にもそこそこ厳しめです。

---

気づけば、放課後の部室にいちばん長く残っているのは僕になっていた。

*Lazy* は評価戦略のこと。*Native* はネイティブコードのこと……ではなく **native language(母語)** のことだと、英美先輩は最初に教えてくれた。それでは、よい部活動を。
