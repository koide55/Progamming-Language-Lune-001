# Lune Documents

このフォルダは Lune v0.1 に関連する仕様書をまとめる。

## 現状仕様

- `LANGUAGE_SPEC.md`: 現在の実装で利用できる Lune v0.1 の言語仕様。
- `LANGUAGE_FUTURE_SPEC.md`: JVM/Java/OO 連携まで含む将来目標仕様。
- `TUTORIAL.md`: Lune v0.1 を楽しく学ぶためのチュートリアル。
- `TUTORIAL_EN.md`: チュートリアルの英語版。

## 詳細仕様

- `SYNTAX_SPEC.md`: Python + ML 風の表面構文。
- `LEXER_PARSER_SPEC.md`: lexer/layout/parser/AST 実装のための詳細仕様。
- `LAZY_EVALUATION_SPEC.md`: 遅延評価、サンク、strict、部分適用の仕様。
- `TYPE_CHECKER_SPEC.md`: v0.1 typechecker の仕様。
- `LOCAL_TYPE_INFERENCE_SPEC.md`: 期待型伝播によるローカル型推論の仕様。
- `MATCH_EXHAUSTIVENESS_SPEC.md`: `match` 網羅性・到達不能・反駁可能パターン検査の仕様。
- `FUNCTION_TYPE_SPEC.md`: 関数型注釈とカリー化表記の仕様。
- `REPL_SPEC.md`: 対話 REPL の仕様。
- `ERROR_DIAGNOSTICS_SPEC.md`: エラー診断表示・`lune explain`・`lune fix` の仕様。
- `ERROR_INDEX.md`: 全診断コードの詳解カタログ（`lune explain --index` で自動生成）。
- `FORMATTER_SPEC.md`: 正準フォーマッタ `lune fmt` の仕様。
- `VALUE_DISPLAY_SPEC.md`: REPL / show / print の値表示仕様。
- `STANDARD_LIBRARY_SPEC.md`: prelude 標準ライブラリ最小セットの仕様。
- `LIST_LITERAL_SPEC.md`: リストリテラルの仕様。
- `MODULE_LOADING_SPEC.md`: ファイルモジュール読み込みの仕様。
- `RECORD_FIELD_SPEC.md`: レコードとフィールドアクセスの追加仕様。
- `WHILE_LOOP_SPEC.md`: `while` ループの仕様。
- `FOR_LOOP_SPEC.md`: `for` 式の仕様。
