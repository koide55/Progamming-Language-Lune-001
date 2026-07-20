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
:thunks [NAME]
:trace [on|off]
:explain CODE [en|ja]
```

- `:help`: コマンド一覧を表示する。
- `:quit` / `:q`: REPL を終了する。
- `:env`: 現在のトップレベル名と型を表示する。
- `:type NAME`: 指定名の型を表示する。
- `:thunks [NAME]`: 遅延束縛（thunk）の評価状態を、**評価を一切起こさずに**表示する。NAME を省略すると全 thunk を定義順に一覧する。
- `:trace [on|off]`: 遅延評価トレースの有効/無効を切り替える（引数なしで現在の状態を表示）。有効な間、式の評価で**いつ・どの thunk が force されたか**を入れ子の深さ付きで表示する（§5.2）。
- `:explain CODE [en|ja]`: 診断コードの詳解を表示する（`lune explain CODE` と同じ内容、`ERROR_DIAGNOSTICS_SPEC.md` §4.1）。言語を省略すると英語。`ja` で日本語の詳解を表示する。

### 5.1 `:thunks` の表示

各束縛は次のいずれかの状態で表示される（`LAZY_EVALUATION_SPEC.md` の thunk 状態に対応）。

```text
x   : unevaluated                    # まだ一度も force されていない
x   : evaluated = 2                  # メモ化済み（値を表示）
x   : failed = division by zero      # 失敗もメモ化される
v   : value = 7                      # thunk ではない（:thunks NAME 指定時のみ）
```

値の表示は専用の非強制プレビューを使う。値の中の未評価部分は `<thunk>` と表示されるため、無限ストリームでも安全で、**どこまで評価が進んだか**がそのまま見える。

```text
lune> let nat = naturalsFrom(1)
ok
lune> head(nat)
Some(1) : Option[Int]
lune> :thunks nat
nat : evaluated = Cons(1, <thunk>)
```

### 5.2 `:trace` の表示

トレースが有効な間、式の評価は次のイベントを入れ子の深さ付きで表示する。

```text
force <式>       # thunk の評価に入った
=> <値>          # その評価が完了した（対応する force と同じ深さ）
memo <式> => <値> # force がメモ化済みの結果に当たった（再評価なし）
```

式は正準フォーマッタで一行に整形し、値は §5.1 と同じ非強制プレビューで表示する。宣言（`let` など）は遅延されるため、トレースには何も現れない — それ自体が遅延評価の教材になる。

```text
lune> :trace on
trace on
lune> let x = 1 + 1
ok                       # 宣言では何も評価されない
lune> x + 1
force x + 1
  force 1 + 1
  => 2
=> 3
3 : Int
lune> x
force x
  memo 1 + 1 => 2        # 2 回目はメモ化された値を再利用
=> 2
2 : Int
```

CLI では `lune --eval NAME --trace FILE` で同じトレースを stderr に出力する。

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
