# Lune リストリテラル仕様

Version: 0.1 draft  
Related: `LANGUAGE_SPEC.md`, `STANDARD_LIBRARY_SPEC.md`, `LAZY_EVALUATION_SPEC.md`

この文書は Lune v0.1 のリストリテラル仕様を定義する。

## 1. 目的

リストリテラルは、`Cons` / `Nil` を直接書かずに有限リストを作るための構文である。

```lune
let numbers = [1, 2, 3]
```

これは意味的には次と同等である。

```lune
let numbers = Cons(1, Cons(2, Cons(3, Nil)))
```

## 2. 構文

```lune
[]
[expr]
[expr, expr]
[expr, expr,]
```

末尾カンマを許可する。

## 3. AST

追加 AST:

```text
ListExpr(items, span)
```

`items` はリテラル内の式を左から右の順に保持する。

## 4. 型チェック

空リスト `[]` の型は `List[Any]` とする。型注釈がある場合は、その型に代入可能である。

```lune
let empty: List[Int] = []
```

非空リスト `[a, b, c]` の型は、各要素型の共通型 `T` を使って `List[T]` とする。

```lune
let numbers = [1, 2, 3]       # List[Int]
let words = ["a", "b"]        # List[String]
```

要素型が一致しない場合は型エラーである。

```lune
let bad = [1, true]
```

## 5. 評価

リストリテラルは `Cons` / `Nil` の有限リストを生成する。

```lune
[1, 2, 3]
```

評価結果:

```text
Cons(1, Cons(2, Cons(3, Nil)))
```

REPL / `show` / `repr` では Lisp 風に表示する。

```text
lune> [1, 2, 3]
(1 2 3) : List[Int]
```

## 6. 遅延評価との関係

リストリテラルの要素は遅延される。リストの spine は有限構造として作られるが、各要素式は必要になるまで評価されない。

```lune
let items = [1, crash()]
let answer = head(items)
```

この例では `answer` は `Some(1)` になり、2 番目の要素 `crash()` は評価されない。

表示、`length`、`fold`、`for` など、要素や spine を必要とする操作では必要な分だけ評価される。

## 7. 制限

- v0.1 では finite list literal のみを扱う。
- list pattern `[x, y]` は未対応。
- list comprehension は未対応。
- infix cons `::` は未対応。
