# 第68回プログラミング・シンポジウム ライブデモ台本

発表テーマ: **「デフォルト遅延評価は初心者に教えられるか? — 遅延を隠さず観察可能にする言語 Lune」**

想定: 発表 25 分(質疑込み)のうち、ライブデモ約 10 分。
この台本の期待出力はすべて実機で採取済み(2026-07-24, main = f3b2ef7)。
`./demo/prosym68/rehearse.sh` を実行すると全ステップを自動検証できる。

---

## 事前チェックリスト(会場入り前日まで)

- [ ] `git pull` して main を最新化、全テスト green を確認
      (`PYTHONPATH=. python3 -m unittest discover -s tests`)
- [ ] `./demo/prosym68/rehearse.sh` が `failed: 0` で通る
- [ ] ターミナル: フォントを拡大(24pt 以上)、背景と診断色のコントラスト確認
- [ ] REPL 貼り付け用に `repl-session.txt` を隣のエディタで開いておく
- [ ] **ネットワークは不要**(すべてローカル実行)。バックアップ 2 段構え:
  - 期待出力はこの台本に全文貼付 → 最悪スライドに貼って見せる
  - [Playground](https://koide55.github.io/lune-lang/playground/)(要ネット)を第 2 フォールバックに

---

## デモ0: 起動(30 秒)

```
./bin/lune --repl
:lang ja
```

セリフ: 「実装は Python 標準ライブラリのみ、約 6,000 行です。今日お見せするものはすべてこの場で動かします」

---

## デモ1: 無限リストと `:thunks` — 遅延を"覗く"(3 分)

狙い: **無限リストが特別な Stream 型ではなく普通の `List`** であること、
そして **評価せずに評価状態を観察できる** ことを見せる。

```
lune> let nats = naturalsFrom(1)
lune> :thunks nats
nats : unevaluated
```

セリフ: 「`nats` は 1 から始まる無限リストです。いま中身はどうなっているか?
GHC では確かめようとした瞬間に評価が走ってしまう。ハイゼンベルク的です。
Lune の `:thunks` は**評価せずに**状態を覗けます — まだ未評価(unevaluated)です」

```
lune> take(nats, 5)
(1 2 3 4 5) : List[Int]
lune> :thunks nats
nats : evaluated = Cons(1, Cons(2, Cons(3, Cons(…))))
```

セリフ: 「5 要素取り出すと、**必要になった先頭部分だけ**が評価されました。
`Cons(…)` の `…` の先は依然サンクのまま。無限リストと安全に共存できます」

---

## デモ2: `:trace` — 強制の瞬間を実況する(2 分)

狙い: 「いつ・何が・どの深さで」force されるかがソースレベルで見えること。

```
lune> :trace on
lune> take(map(naturalsFrom(1), fn x: Int -> x * x), 3)
force take(map(naturalsFrom(1), fn x: Int -> x * x), 3)
  force 3
  => 3
  force map(naturalsFrom(1), fn x: Int -> x * x)
    force naturalsFrom(1)
    => Cons(1, <thunk>)
    ...
(1 4 9) : List[Int]
```

セリフ: 「map が先に全要素を計算するのではなく、take に**引っ張られて**
1 要素ずつ生成される様子が、入れ子の深さつきで見えます。
教科書で図に描いて説明していたものが、処理系の一次情報として出てきます」

メモ化も見せる:

```
lune> let y = 1 + 1
lune> y
force y
  force 1 + 1
  => 2
=> 2
2 : Int
lune> y
force y
  memo 1 + 1 => 2
=> 2
2 : Int
```

セリフ: 「2 回目は `memo` — 計算ではなくメモ化された値が返ったことまで区別して見えます」

---

## デモ3: 循環定義 — GHC の `<<loop>>` との対比(2 分)

スライドに先に GHC の挙動を出しておく:

> GHC: `Exception: <<loop>>`(どこが・なぜかは教えてくれない)

Lune では(REPL を抜けてシェルから):

```
./bin/lune --eval a --lang ja demo/prosym68/loop.lune
```

```
error[RUN0005]: 再帰的なサンク評価: この値の定義が自分自身の結果に依存しています
   = hint: 再帰的な値は計算できません。再帰関数 (`def`) として書くか、参照の循環を断ち切ってください
   = help: 詳しくは `lune explain RUN0005 --lang ja` を実行してください
```

セリフ: 「同じ現象を、Lune は**診断コードつきで説明**します。
遅延評価の言語で初心者が最初に踏む地雷を、教材に変えるという設計です」

---

## デモ4: コンパイラが教える(3 分)

### 4a. 書き間違い → did-you-mean → 自動修正

**注意: fix はファイルを書き換えるので、必ず /tmp にコピーしてから実演する。**

```
cp demo/prosym68/typo.lune /tmp/typo.lune
./bin/lune --check --lang ja /tmp/typo.lune
```

```
error[TYP0001]: 未定義の名前: lenght
  --> /private/tmp/typo.lune:9:13
  |
9 | let total = lenght(numbers)
  |             ^^^^^^ この名前は定義されていない
   = hint: もしかして `length` ですか?
   = help: 詳しくは `lune explain TYP0001 --lang ja` を実行してください
```

```
./bin/lune fix --write /tmp/typo.lune
./bin/lune --check /tmp/typo.lune   # → type check OK
```

### 4b. 網羅性検査が「足りないケース」を反例で示す

```
./bin/lune --check --lang ja demo/prosym68/traffic.lune
```

```
error[TYP0007]: 網羅的でない match: Yellow のケースがありません
  --> demo/prosym68/traffic.lune:12:5
   |
12 |     match s:
   |     ^^^^^ パターン Yellow がカバーされていない
   = hint: Yellow のケースを追加するか、ワイルドカードケース `| _ -> ...` を追加してください
   = help: 詳しくは `lune explain TYP0007 --lang ja` を実行してください
```

セリフ: 「エラーは失敗の通知ではなく**仕様の穴を見つける道具**、という位置づけです」

### 4c. クロージング: 説明の完全性は"テストが強制"している

```
./bin/lune explain TYP0007 --lang ja
```

セリフ: 「全 29 の診断コードに、意味・発生する最小例・直し方の解説があります。
そして**説明のない診断コードはテストが落ちるので、この言語には存在できません**
(`tests/test_explanations.py`)。親切さを気合いではなく機構で保証するのが Lune の主張です」

---

## 進行が崩れたとき

| 事態 | 対処 |
|---|---|
| REPL が固まった/落ちた | Ctrl-C → 再起動。`repl-session.txt` から貼り直し |
| 出力が期待とズレる | 深追いしない。台本の採取済み出力(スライド控え)に切替 |
| 手元機が使えない | [Playground](https://koide55.github.io/lune-lang/playground/) + [診断カタログ](https://koide55.github.io/lune-lang/playground/errors.html) |
| 時間超過 | デモ2(trace)とデモ4a(fix)を落とす。デモ1と3は削らない — コア主張そのものなので |

## 想定質問(戦略メモより)

- 「既存技術の寄せ集めでは?」→ 個々の系譜は認める。説明完全性の*テストによる強制*は既存言語になく、「デフォルト遅延 × 初心者教育」の緊張を観察可能性で解くのが統合としての新規性。
- 「教育効果の根拠は?」→ 未測定と正直に認め、評価計画(playground 到達、explain 参照頻度、講義での理解度)を示して「どう測るべきか」を会場に問う。
- 「なぜ Python 実装? 遅くない?」→ 教育と Pyodide ゼロインストールを最優先した意図的選択。性能は非目標。
