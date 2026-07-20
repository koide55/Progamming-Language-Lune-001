# Lune 遅延評価仕様

Version: 0.1 draft  
Related: `LANGUAGE_SPEC.md`, `SYNTAX_SPEC.md`, `LEXER_PARSER_SPEC.md`, `STANDARD_LIBRARY_SPEC.md`, `RECORD_FIELD_SPEC.md`, `WHILE_LOOP_SPEC.md`

この文書は Lune v0.1 の遅延評価ランタイム仕様を定義する。

## 1. 基本モデル

Lune はデフォルト非正格評価を採用する。式は値が必要になるまで評価されず、遅延式はランタイム上でサンクとして保持される。

サンクは式と環境を閉じ込める。

```text
Thunk:
  expr
  env
  state
  value?
  error?
```

サンクの評価はメモ化される。評価に成功したサンクは、以後同じ値を返す。

## 2. サンク状態

サンクは次の状態を持つ。

```text
Unevaluated
Evaluating
Evaluated(value)
Failed(error)
```

状態遷移:

```text
Unevaluated -> Evaluating -> Evaluated(value)
Unevaluated -> Evaluating -> Failed(error)
Evaluated(value) -> Evaluated(value)
Failed(error) -> Failed(error)
Evaluating -> runtime error
```

`Evaluating` のサンクを再度 force した場合、再入評価エラーにする。

`Failed(error)` のサンクを再度 force した場合、同じ失敗を再送出する。失敗した式を再実行してはならない。

## 3. Force 境界

以下の文脈では弱頭正規形まで force する。

- 変数参照。
- `force expr`。
- `seq a b` の第 1 引数。
- `if` / `elif` の条件。
- `while` の条件。
- `for` の iterable spine。
- 二項演算、比較演算、単項演算の必要な引数。
- 関数呼び出しの callee。
- builtin 関数の正格引数。
- `match` の scrutinee の外側コンストラクタ。
- リテラルパターンとの比較。
- リストリテラルの表示や走査で必要になった要素。
- 正格引数 `!x`。
- `strict let`。
- 正格データフィールド `!field: Type`。

弱頭正規形では、データ値の外側コンストラクタだけが分かればよい。データフィールドは必要になるまで force しない。

## 4. let

通常の `let` は遅延束縛である。

```lune
let x = expensive()
```

`x` は参照されるまで評価されない。

`strict let` は束縛時に評価される。

```lune
strict let x = expensive()
```

パターン束縛は外側のパターン照合に必要な分だけ評価する。

```lune
type Wrap[T] =
    | Wrap(value: T)

let Wrap(x) = Wrap(expensive())
```

この例では外側の `Wrap` は確認するが、`x` の中身は参照されるまで評価しない。なお `let` のパターンは反駁不能でなければならない (`MATCH_EXHAUSTIVENESS_SPEC.md` §7、`TYP0008`)。

## 5. 関数呼び出し

関数引数はデフォルトでサンクとして渡される。

```lune
def first(a: Int, b: Int): Int =
    a

first(1, crash())
```

この例では `b` は評価されない。

正格引数は呼び出し時に評価される。

```lune
def strictFirst(!a: Int, !b: Int): Int =
    a
```

この例では `b` が関数本体で使われなくても評価される。

## 6. データコンストラクタ

データコンストラクタのフィールドはデフォルトで遅延される。

```lune
type Box =
    | Box(value: Int)
```

`Box(crash())` を作っても、`value` を使うまでは `crash()` は評価されない。

正格フィールドは生成時に評価される。

```lune
type Point =
    | Point(!x: Int, !y: Int)
```

`Point(crash(), 0)` は生成時に失敗する。

## 7. 部分適用

ユーザー定義関数、ラムダ、データコンストラクタは部分適用できる。

```lune
let add = fn x y -> x + y
let inc = add(1)
let answer = inc(41)
```

`add(1)` は `x` を捕捉し、残りの `y` を受け取る関数値を返す。捕捉された非正格引数は通常の関数呼び出しと同じくサンクとして保存される。

```lune
type Pair =
    | Pair(left: Int, right: Int)

let withOne = Pair(1)
let pair = withOne(41)
```

コンストラクタの部分適用も、渡されたフィールドを捕捉し、残りのフィールドを受け取るコンストラクタ関数値を返す。

正格引数または正格フィールドは、部分適用で渡された時点で評価される。

## 8. match

`match` は scrutinee を弱頭正規形まで評価する。

```lune
match value:
    | Some(x) -> x
    | None -> 0
```

コンストラクタの種類を判定するため、外側の値は評価される。コンストラクタフィールドは、対応するサブパターンが必要とする分だけ評価される。

```lune
match Box(crash()):
    | Box(_) -> 1
```

この例では `crash()` は評価されない。

```lune
match Box(crash()):
    | Box(0) -> 1
    | Box(_) -> 2
```

この例ではリテラルパターン `0` と比較するため `crash()` が評価される。

## 9. seq

`seq a b` は `a` を弱頭正規形まで評価し、その後 `b` を返す。

```lune
seq x y
```

`y` 自体は、外側の文脈が必要としない限り deep force されない。

## 10. deepForce

`deepForce value` は値全体を可能な限り評価する。

対象:

- サンク。
- タプル要素。
- データコンストラクタの全フィールド。

関数値、builtin 関数、コンストラクタ関数はそれ以上評価しない。

## 11. v0.1 実装範囲

v0.1 evaluator は以下を実装する。

- サンクの成功メモ化。
- サンクの失敗メモ化。
- 再入評価検出。
- 通常 `let` の遅延束縛。
- `strict let`。
- 通常関数引数の遅延渡し。
- 正格引数 `!x`。
- データコンストラクタフィールドの遅延。
- 正格コンストラクタフィールド `!field`。
- リストリテラル要素の遅延。
- ユーザー定義関数、ラムダ、データコンストラクタの部分適用。
- `match` の外側コンストラクタ評価。
- `seq`。
- `deepForce`。
- `while` 条件の毎回 force。
- `for` iterable spine の iteration ごとの force。
- `take(list, 0)` が list を force しないこと。
- `take` の返す tail の遅延。

保留:

- 並行環境でのサンク評価ロック。
- 例外型の静的検査。
- strictness analysis による最適化。

## 12. 評価の観察

遅延評価の挙動は次の道具で観察できる（詳細は `REPL_SPEC.md` §5.1–5.2）。

- REPL `:thunks [NAME]`: thunk の状態（unevaluated / evaluated / failed）を評価を起こさずに表示する。
- REPL `:trace on|off`: force・メモ化ヒットを入れ子の深さ付きでトレースする。
- CLI `lune --eval NAME --trace FILE`: 同じトレースを stderr に出力する。
- Playground の「トレース」チェックボックス: ブラウザ上で同じトレースを表示する。

いずれも評価器の trace hook（`lune.evaluator.set_trace_hook`）と非強制プレビュー（`preview_value`、未評価部分を `<thunk>` と表示）の上に実装されている。
