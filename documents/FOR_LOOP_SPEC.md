# Lune for 仕様

Version: 0.1 draft  
Related: `LANGUAGE_SPEC.md`, `WHILE_LOOP_SPEC.md`, `TYPE_CHECKER_SPEC.md`, `LAZY_EVALUATION_SPEC.md`

この文書は Lune v0.1 の `for` 式仕様を定義する。

## 1. 目的

`for` は `List[T]` を読みやすく走査するための最小の反復構文である。

目標:

- `range` や `Cons` / `Nil` で作ったリストを自然に走査できる。
- `var` / assignment と組み合わせて小さな集計を書ける。
- パターン束縛を使い、タプルや ADT の要素を分解しながら処理できる。
- 遅延リストの spine を必要な分だけ force する。

非目標:

- `break` / `continue`。
- 値を返す loop expression。
- Java `Iterable` や任意コレクションの走査。
- top-level statement としての `for`。

## 2. 構文

`for` は expression として parser に追加される。

```lune
for pattern in iterable:
    body
```

ただし v0.1 の top-level は宣言のみなので、実用上は `def` や `let` の block 内で使う。

```lune
let answer =
    var total = 0
    for x in [1, 2, 3, 4]:
        total = total + x
    total
```

この例で `answer` は `10` になる。

パターンも利用できる。

```lune
let pairs = [(1, 10), (2, 20)]

let answer =
    var total = 0
    for (left, right) in pairs:
        total = total + left + right
    total
```

## 3. AST

追加 AST:

```text
ForExpr(pattern, iterable, body, span)
```

- `pattern`: 各要素に対して照合される pattern。
- `iterable`: `List[T]` を返す式。
- `body`: `BlockExpr`。

## 4. 型チェック

`iterable` の型は `List[T]` でなければならない。

```lune
for x in range(1, 4):
    println(x)
```

このとき `x` の型は `Int` である。

`pattern` は要素型 `T` に対して型チェックされる。

```lune
for (left, right) in pairs:
    left + right
```

`pairs` が `List[Tuple[Int, Int]]` なら、`left` と `right` は `Int` として束縛される。

body は型チェックされるが、body の結果型は捨てられる。`for` 式全体の型は常に `Unit` である。

## 5. 評価

評価手順:

1. `iterable` を評価し、リストの spine を弱頭正規形まで force する。
2. `Nil` なら `Unit` を返す。
3. `Cons(head, tail)` なら `head` に対して `pattern` を照合する。
4. 照合に成功した束縛を body 用 environment に定義し、body を実行する。
5. `tail` を weak-head force して次の iteration に進む。

body の結果値は捨てられる。

## 6. 遅延評価との関係

`for` はリストの spine を iteration ごとに force する。要素自体は、パターン照合や body で必要になった時点で force される。

空リストでは body は評価されない。

```lune
let answer =
    for _ in Nil:
        crash()
    42
```

この例で `answer` は `42` になる。

## 7. 制限

- v0.1 では `for` の対象は `List[T]` のみ。
- `break` / `continue` は未対応。
- `for` の戻り値は常に `Unit`。
- top-level に直接 `for` は書けない。`let` / `def` の block 内で使う。
- 無限リストの走査は、body 側で停止手段がない限り終了しない。
