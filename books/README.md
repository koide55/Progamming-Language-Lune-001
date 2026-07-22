# books/ — Lune の教科書プロジェクト

このディレクトリは、Lune の「マニュアル本」スタイルの教科書
（イメージ: K&R『プログラミング言語C』、『はじめてのC』）を執筆するための場所です。

## 現在の状態

**構成確定・執筆準備の段階**。本文はまだありません。

- [OUTLINE.md](OUTLINE.md) — 本書の構成案（書名・対象読者・設計方針・全章の内容・付録・執筆計画）
- 決定済み（2026-07-21）: 書名『プログラミング言語 Lune』、組版は **mdBook/HTML**、
  診断表示は当面英語出力（`feature/ja-diagnostics` の main マージ後に日本語へ一括差し替え）、
  演習解答は各問題直下の折りたたみ（`<details>`）

## 既存ドキュメントとの関係

`documents/` には既にチュートリアルと仕様書が揃っています。本書はそれらと役割を分けます。

| 文書 | 役割 | 想定読了時間 |
| --- | --- | --- |
| `documents/TUTORIAL.md` | 手を動かして1周する入門（現状20章） | 1〜2時間 |
| `documents/*_SPEC.md` | 実装者向けの規範仕様 | 参照用 |
| `documents/ERROR_INDEX.md` | 全29診断コードの解説（`lune explain --index` で生成） | 参照用 |
| **books/（本書）** | **体系的に学ぶ教科書 + リファレンスマニュアル付録** | 数日〜数週間 |

本書は仕様書を「正」とし、各章の末尾で対応する仕様書を参照します。
チュートリアルの内容は取り込みつつ、K&R 流に「体系性・演習・リファレンス」を加えます。

## 執筆時の品質規約（案）

リポジトリの文化（「全診断コードに解説があることをテストで強制」「チュートリアルの出力は実 CLI で検証」）に合わせ、本書も **載せるものはすべて実際に動かして検証する** ことを規約とします。

1. 本文中のコード例は `books/examples/chNN/` に実行可能な `.lune` ファイルとして置く。
2. 型が付く例は `./bin/lune --check`、値を示す例は `./bin/lune --eval`、
   エラー例は実際の診断出力との一致で検証する（検証スクリプトを `books/tools/` に用意予定）。
3. REPL トランスクリプトは実際の REPL 出力を貼る。
4. 用語は `documents/TUTORIAL.md` の訳語（サンク、正格、網羅性など）に合わせる。

## ディレクトリ構成（mdBook）

```
books/
  README.md              # このファイル
  OUTLINE.md             # 構成案
  lune-book/             # mdBook プロジェクト
    book.toml            # mdBook 設定
    src/
      SUMMARY.md         # 目次（章構成の正はここ）
      00-preface.md      # 序章
      01-tour.md         # 第1章
      ...
      appendix-a-reference.md
  examples/              # 検証可能なコード例（章ごと）
    ch01/
    ...
  tools/
    check_examples.sh    # 例の一括検証（--check / --eval / 診断出力照合）
```

ビルド:

```sh
cd books/lune-book
mdbook build    # book/ に HTML を生成（book/ はコミットしない）
mdbook serve    # ローカルプレビュー
```

執筆規約の補足:

- 診断出力を載せるコードブロックは ` ```text,diagnostic` の目印付きで書く。
  `feature/ja-diagnostics` マージ後の日本語出力への一括差し替えを機械的に行うため。
- 診断の `-->` 行のパスは、紙面では作業ディレクトリを省略して `ファイル名:行:桁` で載せる
  （検証スクリプトも同じ正規化で厳密比較する）。
- 演習の解答は各問題の直下に `<details><summary>解答</summary>…</details>` で置く。
  解答のコード例も `books/examples/` の検証対象。
