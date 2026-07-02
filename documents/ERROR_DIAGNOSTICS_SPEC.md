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
```

```text
Label:
  span: SourceSpan
  message: String?
```

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

v0.1 では基本的に `error` のみを実装する。非網羅 match は `TYP0007` の error として検査する (`MATCH_EXHAUSTIVENESS_SPEC.md`)。将来、未使用変数や到達不能 match ケースなどを `warning` として扱う。

## 4. DiagnosticCode

診断コードはカテゴリ接頭辞と 4 桁番号で表す。

```text
LXL0001  lexer
LAY0001  layout processor
PRS0001  parser
TYP0001  typechecker
RUN0001  runtime/evaluator
RPL0001  REPL
```

v0.1 の標準コード:

| Code | Category | Meaning |
| --- | --- | --- |
| `LXL0001` | lexer | unexpected character |
| `LXL0002` | lexer | unterminated string literal |
| `LXL0003` | lexer | unterminated block comment |
| `LXL0004` | lexer | invalid indentation character |
| `LAY0001` | layout | indentation does not match an outer level |
| `LAY0002` | layout | unmatched closing delimiter |
| `PRS0001` | parser | unexpected token |
| `PRS0002` | parser | expected token |
| `PRS0003` | parser | invalid declaration |
| `TYP0001` | typechecker | undefined name |
| `TYP0002` | typechecker | undefined constructor |
| `TYP0003` | typechecker | type mismatch |
| `TYP0004` | typechecker | value is not callable |
| `TYP0005` | typechecker | wrong number of arguments |
| `TYP0006` | typechecker | unsupported syntax in v0.1 |
| `TYP0007` | typechecker | non-exhaustive match |
| `TYP0008` | typechecker | refutable pattern in let/for binding |
| `TYP0009` | typechecker | unreachable match case (warning、予約、未実装) |
| `RUN0001` | runtime | undefined variable |
| `RUN0002` | runtime | value is not callable |
| `RUN0003` | runtime | wrong number of arguments |
| `RUN0004` | runtime | non-exhaustive match |
| `RUN0005` | runtime | recursive thunk evaluation |
| `RUN0006` | runtime | user-raised runtime error |
| `RPL0001` | REPL | unknown command |
| `RPL0002` | REPL | invalid command usage |

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
error[TYP0001]: undefined name: total
  --> sample.lune:3:9
   |
 3 | let x = total + 1
   |         ^^^^^ name is not defined
```

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
