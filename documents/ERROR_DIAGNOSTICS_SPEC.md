# Lune エラー診断仕様

Version: 0.1 draft  
Related: `LANGUAGE_SPEC.md`, `LEXER_PARSER_SPEC.md`, `TYPE_CHECKER_SPEC.md`, `LAZY_EVALUATION_SPEC.md`, `REPL_SPEC.md`

この文書は Lune v0.1 のエラー表示を実用に近づけるための診断仕様である。対象は lexer、layout processor、parser、typechecker、evaluator、REPL で発生するエラーである。

## 1. 目的

エラー表示は、利用者が次の行動をすぐ決められる形にする。

必須要件:

- エラー種別が分かる。
- ファイル名、行、列が分かる。
- 可能なら該当範囲が分かる。
- 該当行のソース断片が表示される。
- 原因を短く説明する。
- 修正ヒントを出せる場合は出す。
- REPL でも同じ形式で表示する。

## 2. 診断モデル

すべてのコンパイル時エラーと実行時エラーは、内部的に `Diagnostic` として表現する。

```text
Diagnostic:
  code: DiagnosticCode
  severity: Severity
  message: String
  primary: Label
  notes: List[String]
  hints: List[String]
  fixes: List[Fix]
```

```text
Label:
  span: SourceSpan
  message: String?
```

```text
Fix:
  span: SourceSpan     # the range to replace
  replacement: String  # the text to put there
  description: String
```

`fixes` は機械的に適用可能な修正候補である。`lune fix` がこれを収集して適用する（§9.5）。span は置換対象を正確に覆う必要がある。

```text
SourceSpan:
  filename: String
  startLine: Int
  startColumn: Int
  endLine: Int
  endColumn: Int
```

`endColumn` は半開区間の終端とする。つまり 1 文字分の範囲は `startColumn = 5, endColumn = 6`。

## 3. Severity

```text
error
warning
note
```

非網羅 match は `TYP0007` の error、到達不能 match ケースは `TYP0009` の `warning` として検査する (`MATCH_EXHAUSTIVENESS_SPEC.md`)。warning は型チェックを中断せず、型チェッカが収集して CLI (`--check`) と REPL が stderr に表示する。将来、未使用変数などにも `warning` を拡張する。

## 4. DiagnosticCode

診断コードはカテゴリ接頭辞と 4 桁番号で表す。

```text
LXL0001  lexer
LAY0001  layout processor
PRS0001  parser
MOD0001  module loader
TYP0001  typechecker
REC0001  record
RUN0001  runtime/evaluator
```

v0.1 で実際に発行されるコード（正は `lune/explanations.py` のカタログ）:

| Code | Category | Meaning |
| --- | --- | --- |
| `LAY0001` | layout | inconsistent indentation |
| `LAY0002` | layout | unmatched closing delimiter |
| `LXL0001` | lexer | unexpected character |
| `LXL0002` | lexer | unterminated string or character literal |
| `LXL0003` | lexer | unterminated block comment |
| `LXL0004` | lexer | tabs are not allowed in indentation |
| `PRS0001` | parser | unexpected token |
| `PRS0002` | parser | expected a specific token |
| `MOD0001` | module | module not found or unreadable |
| `MOD0002` | module | cyclic module import |
| `MOD0003` | module | module declaration mismatch |
| `TYP0001` | typechecker | undefined name |
| `TYP0003` | typechecker | type mismatch |
| `TYP0004` | typechecker | value is not callable |
| `TYP0005` | typechecker | wrong number of arguments |
| `TYP0006` | typechecker | for-loop iterable must be a List |
| `TYP0007` | typechecker | non-exhaustive match |
| `TYP0008` | typechecker | refutable pattern in let/for binding |
| `TYP0009` | typechecker | unreachable match case (warning) |
| `TYP0010` | typechecker | cannot infer parameter type (warning) |
| `TYP0011` | typechecker | recursive function requires return type |
| `REC0001` | record | duplicate record field |
| `REC0002` | record | unknown record field |
| `REC0003` | record | missing record field |
| `REC0004` | record | duplicate initializer field |
| `REC0005` | record | unexpected record field |
| `REC0006` | record | record fields must be named |
| `RUN0005` | runtime | recursive thunk evaluation |
| `RUN0006` | runtime | runtime error (generic) |

runtime エラーは、再帰サンクの force（専用コード `RUN0005`、hint 付き）を除き、現状ほぼすべて汎用の `RUN0006` に集約される（未定義変数、失敗サンクの force、標準ライブラリの型不一致、実行時の非網羅 match など）。`TYP0002` は欠番。REPL コマンドのエラーは診断コードではなくプレーンな文字列で返す。各コードの詳解は `lune explain <CODE>` で読め、テスト `tests/test_explanations.py` が「発行されうる全コードに詳解が存在すること」を保証する。

### 4.1 コード詳解（`lune explain`）

各診断コードには長文の詳解（意味・発生する最小例・修正方法）を用意する。詳解は**英語と日本語の 2 言語**で提供する（英語: `lune/explanations.py`、日本語: `lune/explanations_ja.py`。両カタログのコード集合が一致することはテストで強制する）。

- CLI: `lune explain <CODE> [--lang en|ja]`（大文字小文字は無視。未知コードは利用可能コード一覧を表示して終了コード 1、引数欠如・未対応言語は 2。既定は英語）。
- CLI: `lune explain --index [--lang en|ja]` — 全コードの詳解を 1 つの Markdown として出力する。生成結果は `documents/ERROR_INDEX.md`（英語）/ `documents/ERROR_INDEX_JA.md`（日本語）としてコミットし、テストで同期を強制する。
- REPL: `:explain CODE [en|ja]`。
- 導線: 診断表示（CLI/REPL）は、詳解のあるコードに対し末尾へ `= help: run \`lune explain <CODE>\` for a detailed explanation` を付す。この導線は `format_diagnostic(..., explain_hint=True)` のオプトインで、コアの整形出力自体は変更しない。

### 4.2 診断メッセージの多言語化

診断のメッセージ・caret 注（label）・hint は、すべてメッセージカタログ `lune/messages.py` の `t(key, **params)` を通して生成される（英語・日本語の対訳）。言語はプロセス全体の状態で、入口で一度だけ選ぶ:

- CLI: グローバル `--lang en|ja`（どのサブコマンドでも可。例: `lune --check --lang ja file.lune`）
- REPL: `:lang en|ja`（`:explain` の既定言語もこれに追従する）
- Playground: 「言語」セレクタ

テスト `tests/test_messages.py` が「ソース中で使われる全キーがカタログに存在し、未使用キーがなく、全キーに日本語訳があり、英日のプレースホルダが一致すること」を強制する。`= help:` フッタも言語化される（日本語では `--lang ja` 付きの再実行を案内する）。

## 5. 表示形式

標準表示:

```text
error[TYP0003]: return type of bad: expected Bool, got Int
  --> examples/bad.lune:2:5
   |
 2 |     x + 1
   |     ^^^^^ this expression has type Int
   |
   = hint: change the return type to Int, or return a Bool
```

規則:

- 1 行目は `severity[code]: message`。
- 2 行目は `--> filename:line:column`。
- 該当行を `line | source` 形式で表示する。
- `^` を使って primary span を示す。
- label message がある場合、caret の右に表示する。
- hint は `= hint:` で表示する。
- note は `= note:` で表示する。

複数行 span の v0.1 表示は、最初の行のみを primary として表示してよい。将来、複数行 caret を実装する。

## 6. ソース断片

診断を整形する側は、filename からソース本文を取得する。

取得方法:

- ファイル実行時: ファイル内容を `SourceMap` に登録する。
- REPL 実行時: 入力断片を仮想ファイル名 `<repl:N>` で登録する。
- ソースが取得できない場合: `--> filename:line:column` だけ表示し、断片表示を省略する。

## 7. Lexer / Layout エラー

lexer/layout は発生位置を正確に持てるため、必ず `SourceSpan` を付ける。

例:

```text
error[LXL0001]: unexpected character '$'
  --> sample.lune:1:9
   |
 1 | let x = $1
   |         ^ unexpected character
```

タブによるインデント:

```text
error[LXL0004]: tabs are not allowed in indentation
  --> sample.lune:2:1
   |
 2 | \tvalue
   | ^ use spaces for indentation
   |
   = hint: replace tabs with spaces
```

## 8. Parser エラー

parser は「期待したもの」と「実際のトークン」を表示する。

例:

```text
error[PRS0002]: expected RPAREN, got COLON
  --> sample.lune:1:12
   |
 1 | def f(x: Int: Int =
   |            ^ expected ')'
```

parser の `expected` エラーでは、hint を出せる場合だけ出す。

例:

```text
= hint: did you forget ')' before ':'?
```

## 9. Typechecker エラー

typechecker は可能な限り、問題の式または宣言の span を primary とする。

### 9.1 Undefined name

```text
error[TYP0001]: undefined name: totl
  --> sample.lune:3:9
   |
 3 | let x = totl + 1
   |         ^^^^ name is not defined
   = hint: did you mean `total`?
```

スコープ内（prelude を含む）に綴りの近い名前があれば、`= hint: did you mean \`x\`?` を付す。近さは編集距離ベース（`difflib.get_close_matches`, cutoff 0.6）で、候補が無ければヒントは付かない。レコードフィールドの未知アクセス (`REC0002`) や構築時の未宣言フィールド (`REC0005`) でも、同様に近いフィールド名を提案する。

### 9.2 Type mismatch

```text
error[TYP0003]: let annotation: expected Int, got Bool
  --> sample.lune:1:19
   |
 1 | let answer: Int = true
   |                   ^^^^ this expression has type Bool
```

### 9.3 Call arity

```text
error[TYP0005]: add expects 2 arguments, got 1
  --> sample.lune:4:14
   |
 4 | let answer = add(1)
   |              ^^^^^^ wrong number of arguments
```

### 9.4 Match branch mismatch

```text
error[TYP0003]: branch type mismatch: Int vs Bool
  --> sample.lune:5:19
   |
 5 |         | None -> false
   |                   ^^^^^ this branch has type Bool
```

### 9.5 自動修正 (`lune fix`)

診断が `fixes`（§2 の `Fix`）を持つ場合、`lune fix` がそれを適用する。実装は `lune/fixer.py`。

- 現状の対象は未定義名の typo (`TYP0001`)。`did you mean` の候補（§9.1）を置換 `Fix` として持たせ、名前の span を置き換える。
- 反復適用: 型チェッカは最初のエラーで停止するため、1 件適用しては再チェックし、ファイル内の複数 typo を 1 回の実行で直す（無進捗・上限 200 回で停止）。
- `import` を含むファイルは、輸入名を解決できず誤修正しうるため現状スキップする。
- CLI: `lune fix <file>`（stdout）/ `--write`（その場書き換え）/ `--check`（修正候補があれば終了コード 1）。

レコードフィールド (`REC0002`/`REC0005`) は、現状 span がフィールド名を正確に覆わないため `Fix` を付けていない（ヒントのみ）。span 改善後に対応予定。

## 10. Runtime エラー

runtime エラーは、v0.1 では評価中 AST の span がない場合がある。その場合でもエラー種別とメッセージは統一する。

span が取れる場合:

```text
error[RUN0004]: non-exhaustive match for value: None
  --> sample.lune:7:5
   |
 7 |     match option:
   |     ^^^^^^^^^^^^^ no pattern matched this value
```

span が取れない場合:

```text
error[RUN0005]: recursive thunk evaluation
```

将来、AST 全ノードに span を保持して runtime エラーにも位置を付ける。

## 11. REPL 表示

REPL 入力は `<repl:N>` という仮想ファイル名を使う。

```text
lune> let answer: Int = true
error[TYP0003]: let annotation: expected Int, got Bool
  --> <repl:3>:1:19
   |
 1 | let answer: Int = true
   |                   ^^^^ this expression has type Bool
```

REPL はエラー後も継続する。

## 12. API 方針

v0.1 実装では以下を追加する。

```text
DiagnosticError(Exception):
  diagnostic: Diagnostic
```

既存のエラー型は段階的に `DiagnosticError` を継承または内包する。

```text
LuneSyntaxError(DiagnosticError)
LuneTypeError(DiagnosticError)
LuneRuntimeError(DiagnosticError)
```

ただし移行期間中は、旧形式の `Exception` も診断整形器に渡せるようにする。

## 13. SourceMap

`SourceMap` は filename からソース行を取得する責務を持つ。

```text
SourceMap:
  add(filename, source)
  getLine(filename, line) -> String?
```

CLI はファイルを読むときに `SourceMap` へ登録する。

REPL は入力ごとに `<repl:N>` として登録する。

## 14. 実装順序

推奨順:

1. `SourceSpan` を end position 付きに拡張する。
2. `Diagnostic` / `Label` / `SourceMap` / formatter を追加する。
3. `LuneSyntaxError` を `DiagnosticError` に移行する。
4. CLI と REPL で診断 formatter を使う。
5. parser の expected token エラーを診断コード付きにする。
6. typechecker の主要エラーを span 付き診断にする。
7. AST ノードへ span を持たせ、runtime エラー位置を改善する。

## 15. v0.1 での制限

- AST ノードに span がないため、typechecker/runtime の位置は初期実装では限定的になる。
- 複数箇所ラベルは将来対応とする。
- カラー出力は任意。環境変数や TTY 判定で制御する。
- 日本語メッセージと英語メッセージの切り替えは将来対応とする。
