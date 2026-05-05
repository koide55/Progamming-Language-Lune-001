# Lune REPL 仕様

Version: 0.1 draft  
Related: `LANGUAGE_SPEC.md`, `TYPE_CHECKER_SPEC.md`, `LAZY_EVALUATION_SPEC.md`, `ERROR_DIAGNOSTICS_SPEC.md`

## 1. 目的

Lune v0.1 REPL は、lexer/parser/typechecker/evaluator を対話的に試すための開発用 REPL である。

目標:

- 入力ごとに型チェックしてから評価する。
- `let`、`def`、`type` 宣言をセッション内に保持する。
- 式を入力した場合は値と型を表示する。
- 遅延評価の挙動を観察できる。

## 2. セッション状態

REPL セッションは 2 つの環境を保持する。

```text
typeEnv
evalEnv
```

各入力は同じ環境に追加される。たとえば:

```lune
let x = 40
x + 2
```

2 行目は 1 行目の `x` を参照できる。

## 3. 入力の分類

REPL は入力を次の順で解釈する。

1. 宣言またはモジュール断片としてパースする。
2. 失敗した場合、式として扱い `let __repl_value = expr` に包んでパースする。

式入力は内部的にトップレベル `let` として評価されるが、表示上は式の値として扱う。

## 4. 表示

宣言入力:

```text
ok
```

式入力:

```text
value : Type
```

値の表示形式は `VALUE_DISPLAY_SPEC.md` に従う。代表例:

```text
lune> "Ada"
"Ada" : String
lune> [1, 2, 3]
(1 2 3) : List[Int]
```

例:

```text
lune> 1 + 2
3 : Int
```

## 5. コマンド

v0.1 でサポートするコマンド:

```text
:help
:quit
:q
:env
:type NAME
```

- `:help`: コマンド一覧を表示する。
- `:quit` / `:q`: REPL を終了する。
- `:env`: 現在のトップレベル名と型を表示する。
- `:type NAME`: 指定名の型を表示する。

## 6. 複数行入力

v0.1 の対話 REPL は簡易的な複数行入力をサポートする。

- 入力行が `:`、`=`、`->` で終わる場合、継続プロンプトへ移る。
- 継続中は空行で入力を確定する。

例:

```text
lune> def add(x: Int, y: Int): Int =
...     x + y
...
ok
```

## 7. 行編集と履歴

端末上で `--repl` を起動した場合、REPL は readline 互換の行編集を有効にする。

想定する操作:

- 左右矢印によるカーソル移動。
- 上下矢印による履歴移動。
- Backspace / Delete。
- `Ctrl-A` / `Ctrl-E` など readline の基本操作。

履歴は可能なら `~/.lune_history` に保存する。

標準入力が pipe やテスト用 stream の場合、行編集は有効化せず、従来どおり 1 行ずつ読み込む。

## 8. エラー

型エラー、構文エラー、実行時エラーは REPL を終了させない。エラーメッセージを表示し、次の入力へ進む。

エラー表示形式は `ERROR_DIAGNOSTICS_SPEC.md` に従う。REPL 入力は `<repl:N>` という仮想ファイル名で表示する。

v0.1 ではエラー時の環境ロールバックを完全保証する。入力を型チェックしてから評価するため、型チェック失敗時は評価環境を変更しない。評価失敗時は、その入力による部分的な変更が残る場合がある。将来、評価環境のトランザクション化を検討する。

## 9. 制限

- ファイル読み込みコマンドは未実装。
- 行編集と履歴保存は Python の readline 環境に依存する。
- 補完は未実装。
- 複数行入力の完了判定は簡易的である。
