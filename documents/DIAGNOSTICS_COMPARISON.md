# 診断比較ケーススタディ — Lune vs GHC / Elm / Rust

初心者がつまずく典型 5 場面について、各処理系が「何を・どこまで」伝えるかを
実際の出力で比較する。プログラミング・シンポジウム発表(第68回)と原稿の根拠資料。

## 採取方法

| 処理系 | バージョン | 採取方法 | 採取日 |
|---|---|---|---|
| Lune | main (f3b2ef7) | ローカルで `./bin/lune` を実行(実測) | 2026-07-24 |
| GHC | 9.10.3 | play.haskell.org で実行(実測) | 2026-07-24 |
| Elm | 0.19.1 | editor.elm-lang.org/api/compile に直接 POST(実測)。構造化エラー JSON を端末表示相当に復元 | 2026-07-24 |
| Rust | rustc 1.86.0 | ローカルで `rustc --edition 2021` を実行(実測) | 2026-07-24 |

出力はすべて逐語。唯一の例外はケース5の GHCi `:sprint` で、
これは実測ではなく GHC User's Guide 記載の挙動(本文中に明記)。
Lune の出力は `--lang ja` でも採取済み(§各ケース末尾)。

---

## ケース1: 未定義名(タイポ) — `lenght` と書いてしまう

### GHC

```haskell
main :: IO ()
main = print (lenght [1, 2, 3])
```

```
Main.hs:2:15: error: [GHC-88464]
    Variable not in scope: lenght :: [a0] -> a1
    Suggested fix: Perhaps use ‘length’ (imported from Prelude)
  |
2 | main = print (lenght [1, 2, 3])
  |               ^^^^^^
```

### Elm

```elm
main =
    text (String.fromInt (List.lenght [ 1, 2, 3 ]))
```

```
-- NAMING ERROR ----
I cannot find a `List.lenght` variable:

6|     text (String.fromInt (List.lenght [ 1, 2, 3 ]))
                             ^^^^^^^^^^^
The `List` module does not expose a `lenght` variable. These names seem close
though:

    List.length
    List.concat
    ...

Hint: Read <https://elm-lang.org/0.19.1/imports> to see how `import`
declarations work in Elm.
```

(補足: 非修飾の `lenght` で試すと、Elm では `length` が既定スコープに
ないため候補が `negate` `not` `text` と的外れになる。修飾名の場合のみ上記の
質の高い提案が出る。)

### Rust

```rust
let numbers = vec![1, 2, 3];
let total = numbrs.len();
```

```
error[E0425]: cannot find value `numbrs` in this scope
 --> typo.rs:3:17
  |
3 |     let total = numbrs.len();
  |                 ^^^^^^ help: a local variable with a similar name exists: `numbers`

For more information about this error, try `rustc --explain E0425`.
```

### Lune

```
let numbers = [1, 2, 3]
let total = lenght(numbers)
```

```
error[TYP0001]: undefined name: lenght
  --> typo.lune:9:13
  |
9 | let total = lenght(numbers)
  |             ^^^^^^ name is not defined
   = hint: did you mean `length`?
   = help: run `lune explain TYP0001` for a detailed explanation
```

さらに Lune では提案が**機械適用可能**:

```
$ lune fix --write typo.lune
fixed 1 issue(s) in typo.lune
$ lune --check typo.lune
type check OK
```

### 比較

4 言語とも位置情報と did-you-mean 提案を持つ(この分野の到達点は高い)。
差が出るのはその先:
- **自動修正**: Lune のみ(`lune fix`)。Rust は `cargo fix` があるが E0425 の名前修正は対象外。
- **長文解説への導線**: Rust(`--explain`)と Lune(`explain`)。GHC 9.10 はエラーコード
  `[GHC-88464]` を持ち errors.haskell.org で照会可能。Elm はコードを持たず Web ドキュメントへのリンク。
- **日本語**: Lune のみ(`もしかして `length` ですか?`)。

---

## ケース2: 型注釈と値の不一致 — `Int` に文字列を入れる

### GHC

```
Main.hs:2:5: error: [GHC-83865]
    • Couldn't match type ‘[Char]’ with ‘Int’
      Expected: Int
        Actual: String
    • In the expression: "hello"
      In an equation for ‘x’: x = "hello"
  |
2 | x = "hello"
  |     ^^^^^^^
```

### Elm

```
-- TYPE MISMATCH ----
Something is off with the body of the `x` definition:

6| x = "hello"
       ^^^^^^^
The body is a string of type:

    String

But the type annotation on `x` says it should be:

    Int

Hint: Want to convert a String into an Int? Use the String.toInt function!
```

### Rust

```
error[E0308]: mismatched types
 --> mismatch.rs:2:18
  |
2 |     let x: i32 = "hello";
  |            ---   ^^^^^^^ expected `i32`, found `&str`
  |            |
  |            expected due to this

For more information about this error, try `rustc --explain E0308`.
```

### Lune

```
error[TYP0003]: let annotation: expected Int, got String
  --> mismatch.lune:3:14
  |
3 | let x: Int = "hello"
  |              ^^^^^^^ this expression has type String
   = help: run `lune explain TYP0003` for a detailed explanation
```

### 比較

- Elm の説明文の丁寧さ(会話調 + `String.toInt` という具体的な直し方)は依然この分野の最高水準。
- Rust の「expected due to this」(注釈側にもラベル)は原因箇所の特定として優秀。
- GHC は `[Char]`/`String` の二重表記が初心者には混乱要因。
- Lune は簡潔だが、Elm のような「どう変換するか」の提案はまだない。**この場面での Lune の
  優位は explain への導線と日本語のみ**(正直に認める)。

---

## ケース3: 非網羅 match — `Yellow` のケースを書き忘れる

3 言語(Elm/Rust/Lune)はコンパイルエラー、GHC だけ既定では**無警告で通る**。

### GHC(要 `-Wincomplete-patterns`。既定では検出されない)

```
Main.hs:5:1: warning: [GHC-62161] [-Wincomplete-patterns]
    Pattern match(es) are non-exhaustive
    In an equation for ‘action’:
        Patterns of type ‘Signal’ not matched: Yellow
```

フラグなしで実行した場合は**実行時に**クラッシュする:

```
Main: Main.hs:(5,1)-(6,14): Non-exhaustive patterns in function action
```

### Elm

```
-- MISSING PATTERNS ----
This `case` does not have branches for all possibilities:

 9|>    case s of
10|>        Green -> 1
11|>        Red -> 0

Missing possibilities include:

    Yellow

I would have to crash if I saw one of those. Add branches for them!

Hint: If you want to write the code for each branch later, use `Debug.todo` as a
placeholder. Read <https://elm-lang.org/0.19.1/missing-patterns> for more
guidance on this workflow.
```

### Rust

```
error[E0004]: non-exhaustive patterns: `Signal::Yellow` not covered
 --> nonexhaustive.rs:4:11
  |
4 |     match s {
  |           ^ pattern `Signal::Yellow` not covered
  |
note: `Signal` defined here
 --> nonexhaustive.rs:1:6
  |
1 | enum Signal { Green, Yellow, Red }
  |      ^^^^^^          ------ not covered
  = note: the matched value is of type `Signal`
help: ensure that all possible cases are being handled by adding a match arm
with a wildcard pattern or an explicit pattern as shown
  |
6 ~         Signal::Red => 0,
7 ~         Signal::Yellow => todo!(),
  |
```

### Lune

```
error[TYP0007]: non-exhaustive match: missing case Yellow
  --> traffic.lune:12:5
   |
12 |     match s:
   |     ^^^^^ pattern Yellow is not covered
   = hint: add a case for Yellow, or a wildcard case `| _ -> ...`
   = help: run `lune explain TYP0007` for a detailed explanation
```

### 比較

- **Rust が最強**: 型定義側の該当コンストラクタまでラベルし、追加すべき arm を
  差分形式(`Signal::Yellow => todo!()`)で提示する。
- Elm は Debug.todo ワークフローの提案 + 解説 URL。
- Lune は反例(witness)+ 追加すべきケースのヒント。Rust の差分提示には及ばないが、
  遅延評価の言語で**既定で有効なエラー**である点が GHC(既定オフの警告)との対比。
- GHC のこの既定は「遅延言語では部分関数が慣習的に許容されてきた」歴史の反映であり、
  教育の場では落とし穴になる。

---

## ケース4: 循環定義 — `a = b; b = a`(遅延の罠の核心)

このケースは 3 言語の**設計思想の違い**が最も鮮明に出る。

### GHC — 受理してコンパイル成功、実行時に不透明なエラー

```haskell
a, b :: Int
a = b
b = a
main = print a
```

```
Main: <<loop>>
```

以上。位置情報も、原因の説明も、直し方も出ない。
(遅延評価では値の相互参照が合法(例: `ones = 1 : ones`)なため静的排除はできず、
RTS のブラックホール検出が実行時に報告する。)

### Elm — コンパイル時に拒否(ただし言語から遅延を排除した上で)

```
-- CYCLIC DEFINITION ----
The `a` definition is causing a very tricky infinite loop.

5| a = b
   ^
The `a` value depends on itself through the following chain of definitions:

    ┌─────┐
    │    a
    │     ↓
    │    b
    └─────┘

Hint: The root problem is often a typo in some variable name, but I recommend
reading <https://elm-lang.org/0.19.1/bad-recursion> for more detailed advice,
especially if you actually do want mutually recursive values.
```

説明は見事だが、Elm は正格言語であり**値の再帰そのものを禁止**している。
つまり無限リストや遅延ストリームも書けない。

### Rust — 構文的に成立しない(宣言前の使用)

```
error[E0425]: cannot find value `b` in this scope
 --> cyclic.rs:2:13
  |
2 |     let a = b;
  |             ^ not found in this scope
```

正格 + 宣言順スコープなので、この形の罠は言語構造上存在しない(そのかわり遅延もない)。

### Lune — 遅延を保ったまま、強制時に説明つきで報告

```
error[RUN0005]: recursive thunk evaluation: this value's definition depends on its own result
   = hint: recursive values cannot be computed; use a recursive function (`def`) instead, or break the reference cycle
   = help: run `lune explain RUN0005` for a detailed explanation
```

日本語では:

```
error[RUN0005]: 再帰的なサンク評価: この値の定義が自分自身の結果に依存しています
   = hint: 再帰的な値は計算できません。再帰関数 (`def`) として書くか、参照の循環を断ち切ってください
   = help: 詳しくは `lune explain RUN0005 --lang ja` を実行してください
```

### 比較 — 発表のコア主張がここにある

| | 遅延評価 | 循環定義の扱い | 説明の質 |
|---|---|---|---|
| GHC | ○ 既定 | 実行時 `<<loop>>` | **なし**(位置も原因も出ない) |
| Elm | ✕ 正格(値再帰も禁止) | コンパイル時に拒否 | 依存の輪まで図示 |
| Rust | ✕ 正格 | 構文的に不成立 | (該当場面なし) |
| Lune | **○ 既定** | 強制時に RUN0005 | コード + ヒント + explain 導線 |

Elm は遅延を捨てることで罠を静的に排除した。GHC は遅延を取り、報告の不透明さを
受け入れた。**Lune は遅延を保ったまま、失敗を説明可能な診断に変える**という中間点を主張する。

---

## ケース5: 遅延評価の観察可能性(エラーではなく機能の比較)

対象は遅延を持つ GHC と Lune のみ(Elm/Rust は正格なので該当なし)。

### GHCi(参考: GHC User's Guide 記載の挙動。本ケースのみ実測ではない)

- `:sprint x` — サンクを評価せずに表示(未評価部分は `_`)。例: `xs = _`
- `:print x` — 同上 + 未評価部分に名前を束縛
- 強制の**トレース**(いつ・何が・どこで force されたか)を見る組み込み手段はない
  (`Debug.Trace` を手で仕込む、あるいはプロファイラを使う)。
- メモ化(2 回目のアクセスが計算でなくキャッシュであること)を直接観察する手段はない。

### Lune(実測)

```
lune> let nats = naturalsFrom(1)
lune> :thunks nats
nats : unevaluated
lune> take(nats, 5)
(1 2 3 4 5) : List[Int]
lune> :thunks nats
nats : evaluated = Cons(1, Cons(2, Cons(3, Cons(…))))
```

```
lune> :trace on
lune> take(map(naturalsFrom(1), fn x: Int -> x * x), 3)
force take(map(naturalsFrom(1), fn x: Int -> x * x), 3)
  force map(naturalsFrom(1), fn x: Int -> x * x)
    force naturalsFrom(1)
    => Cons(1, <thunk>)
    ...
(1 4 9) : List[Int]
lune> let y = 1 + 1
lune> y
force y
  force 1 + 1
  => 2
=> 2
lune> y
force y
  memo 1 + 1 => 2    ← 2回目はメモ化された値が返ったことまで区別して表示
=> 2
```

### 比較

- 「評価せずに覗く」は GHCi `:sprint` が先行(Lune `:thunks` は同系の機能)。
- **強制のトレース**(順序・入れ子・ソース式)と**メモ化の可視化**(`memo` 表示)を
  組み込みで持つのは Lune のみ。遅延評価を「教える」ための一次情報として設計されている。

---

## 総合マトリクス

| 能力 | GHC 9.10 | Elm 0.19 | Rust 1.86 | Lune |
|---|---|---|---|---|
| 位置情報 + ソーススニペット | ○ | ○ | ○ | ○ |
| did-you-mean 提案 | ○ | ○ | ○ | ○ |
| 修正の機械適用(auto-fix) | ✕ | ✕ | △ (`cargo fix`、対象限定) | **○ `lune fix`** |
| エラーコード | ○ (9.x〜) | ✕ | ○ | ○ |
| 長文解説への導線 | △ (errors.haskell.org) | △ (Web リンク) | ○ (`--explain`) | **○ (`explain`、REPL/playground 統合)** |
| 解説の網羅性の保証 | ✕ | ✕ | ✕(慣習) | **○(テストで機構的に強制)** |
| 非網羅 match の既定検出 | ✕(警告・既定オフ) | ○(エラー) | ○(エラー) | ○(エラー + 反例) |
| 循環定義の説明 | ✕ (`<<loop>>`) | ○(静的・ただし遅延なし) | (該当なし) | **○(遅延を保ったまま診断)** |
| 遅延の観察(非強制の状態表示) | △ (GHCi `:sprint`) | — | — | ○ (`:thunks`) |
| 強制トレース・メモ化の可視化 | ✕ | — | — | **○ (`:trace`)** |
| 診断の多言語対応(日本語) | ✕ | ✕ | ✕ | **○ (`--lang ja`)** |

## 正直な考察(発表・原稿でもこのトーンで)

**Lune が勝っていない点:**
- 個別メッセージの文章力・具体的な修正提案では Rust(差分つき arm 提案、
  「expected due to this」)と Elm(会話調 + `String.toInt` の提案)が上回る場面がある。
- 「評価せずに覗く」機能自体は GHCi `:sprint` が先行。
- 型不一致(ケース2)では Lune の優位は explain 導線と日本語のみ。

**Lune の差別化(データが支持する主張):**
1. **説明可能性の機構的保証** — 全診断コードに解説があることをテストが強制。
   他 3 言語はどれも「良いメッセージを書く文化」であって「保証する機構」ではない。
2. **遅延と説明可能性の両立**(ケース4) — Elm は遅延を捨て、GHC は不透明さを
   受け入れた。その中間点は空いている。
3. **遅延の教材化**(ケース5) — 強制トレースとメモ化の可視化は、遅延評価を
   授業で「見せる」ための一次情報として他にない。
4. **母語診断** — 主要 4 言語で日本語診断を持つものはない。

## 再現方法

Lune 側の出力は次で再現できる(デモ素材と共通):

```
./demo/prosym68/rehearse.sh          # デモ全ステップの自動検証
./bin/lune --check --lang ja demo/prosym68/traffic.lune
./bin/lune --eval a --lang ja demo/prosym68/loop.lune
```

GHC / Elm / Rust の入力ソースは本文中に全文掲載(GHC は play.haskell.org、
Elm は editor.elm-lang.org/api/compile への POST、Rust はローカル rustc で再現可)。
