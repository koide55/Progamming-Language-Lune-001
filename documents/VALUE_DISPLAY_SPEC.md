# Lune 値表示仕様

Version: 0.1 draft  
Related: `REPL_SPEC.md`, `STANDARD_LIBRARY_SPEC.md`, `LIST_LITERAL_SPEC.md`, `RECORD_FIELD_SPEC.md`

この文書は Lune v0.1 の REPL、CLI `--eval`、`show`、`print`、`println` で使う値表示ルールを定義する。

## 1. 目的

値表示は、内部実装ではなく Lune の表面構文に近い形を優先する。

目標:

- 文字列を Lune の文字列リテラルに近い `"text"` で表示する。
- 有限リストを Lisp 風の `(1 2 3)` で表示する。
- レコードをフィールド中心の `{ name = value }` で表示する。
- `show`、REPL、CLI の表示を統一する。

## 2. 基本値

```text
Int       42
Bool      true / false
String    "Ada"
Unit      ()
Null      null
```

文字列はダブルクォートで囲み、改行や `"` は escape する。

## 3. 複合値

リスト:

```text
[]              ()
[1, 2, 3]       (1 2 3)
(1 2 3)         (1 2 3)
["a", "b"]      ("a" "b")
```

`(1 2 3)` は表示互換の入力構文としても認める。`()` は `Unit` の表示なので、空リスト入力には `[]` を使う。

タプル:

```text
("Ada", true)
```

ADT:

```text
Some("ok")
Ok(42)
None
```

レコード:

```text
{ name = "Ada", age = 36 }
```

レコード表示では record type name は省略し、フィールド名と値を優先する。

## 4. 関数値

関数値の表示では、内部実装（パラメータ list、本体 AST、クロージャ環境）を出力しない。名前だけを `<fn 名前>` の形で示す。

```text
def greet(...) の greet          <fn greet>
部分適用された greet             <fn greet>
ラムダ fn x -> x                <fn>
ビルトイン println               <fn println>
コンストラクタ Some              <fn Some>
部分適用コンストラクタ Cons(1)    <fn Cons>
レコードコンストラクタ Person     <fn Person>
```

ルール:

- 名前を持つ関数値（`def` 定義、ビルトイン、コンストラクタ、レコードコンストラクタ）は `<fn 名前>`。
- 無名のラムダは `<fn>`。
- 部分適用は元の関数、コンストラクタの名前を引き継ぐ。
- `< >` 囲みは再入力可能な構文ではないことを示す（`:thunks` の `<thunk>` と同じ規約）。

この表記は `show`、`print`、`println`、REPL の値表示、CLI `--eval`、`:thunks` や `:trace` のプレビュー表示で共通とする。

## 5. 遅延評価との関係

表示は値を観測する操作なので、表示に必要な部分を force する。

- 文字列、数値、真偽値はそのまま表示する。
- リスト表示は finite list の spine と各要素を表示に必要な分だけ force する。
- レコード表示は表示対象の全フィールドを force する。
- ADT 表示は表示対象のフィールドを force する。
- 関数値の表示は名前のみを使うので、本体やクロージャ環境を force しない。

表示したくない遅延計算がある場合は、値全体ではなく必要なフィールドや要素だけを取り出して表示する。
