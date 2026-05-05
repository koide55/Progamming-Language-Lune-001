# Lune while 仕様

Version: 0.1 draft  
Related: `LANGUAGE_SPEC.md`, `TYPE_CHECKER_SPEC.md`, `LAZY_EVALUATION_SPEC.md`

この文書は Lune v0.1 の `while` ループ仕様を定義する。

## 1. 目的

`while` は、`var` と代入を使った最小の命令的反復構文である。

目標:

- 初心者にも分かりやすいループを書ける。
- 既存の `var` / assignment と組み合わせられる。
- 遅延評価の中で、条件評価と body 実行の正格境界を明確にする。

非目標:

- `break` / `continue`。
- 値を返す loop expression。
- `while else`。
- top-level statement としての `while`。

## 2. 構文

`while` は expression として parser に追加される。

```lune
while condition:
    body
```

ただし v0.1 の top-level は宣言のみなので、実用上は `def` や `let` の block 内で使う。

```lune
let answer =
    var i = 0
    var total = 0
    while i < 5:
        total = total + i
        i = i + 1
    total
```

## 3. AST

追加 AST:

```text
WhileExpr(condition, body, span)
```

`body` は `BlockExpr` である。

## 4. 型チェック

`while` の条件式は `Bool` でなければならない。

```lune
while i < 10:
    i = i + 1
```

body は型チェックされるが、body の結果型は捨てられる。

`while` 式全体の型は常に `Unit` である。

```lune
let loop =
    var i = 0
    while i < 3:
        i = i + 1
```

この例で `loop` の型は `Unit` である。

## 5. 評価

評価手順:

1. 条件式を評価し、弱頭正規形まで force する。
2. truthy なら body を実行する。
3. body 実行後、再び条件式を評価する。
4. 条件が false になったら `Unit` を返す。

条件式は各 iteration で再評価される。

```lune
let answer =
    var i = 0
    while i < 3:
        i = i + 1
    i
```

`answer` は `3` になる。

body は loop の外側 environment を親に持つ child environment で評価する。これにより、body 内の `let` は iteration 内に閉じ、外側の `var` への代入は反映される。

## 6. 遅延評価との関係

`while` の条件は正格境界である。条件式は毎回 force される。

body は実行される iteration でのみ評価される。条件が最初から false の場合、body は評価されない。

```lune
let answer =
    var i = 0
    while false:
        crash()
    42
```

この例では `crash()` は評価されない。

## 7. 制限

- `break` / `continue` は未対応。
- `while` の戻り値は常に `Unit`。
- top-level に直接 `while` は書けない。`let` / `def` の block 内で使う。
- 無限ループ検出は行わない。
