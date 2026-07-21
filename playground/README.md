# Lune Playground — 技術検証 PoC

Pyodide (ブラウザ内 CPython) 上で Lune 処理系を**無改造で**動かす検証。
`documents/STRATEGY.md` の施策 A (ブラウザ Playground) の実現可能性を確認した。

## 動かし方

リポジトリのルートで HTTP サーバーを立て、`/playground/` を開く。

```sh
python3 -m http.server 8642
# → http://localhost:8642/playground/
```

ビルド不要。`index.html` が Pyodide を CDN から読み込み、`/lune/*.py` を
fetch して Pyodide のファイルシステムに書き込み、`check_file` / `eval_file` /
`format_source` / `apply_fixes` / `render_explanation` を直接呼ぶ。

## 検証結果 (2026-07-20)

環境: Pyodide v0.26.4 (Python 3.12.1)、ローカル配信、macOS 上のブラウザ。

| 項目 | 結果 |
| --- | --- |
| 処理系の互換性 | **無改造で動作**。全 246 テストが Python 3.12/3.13 でもパス (外部依存は標準ライブラリのみ) |
| 起動時間 | Pyodide 本体 約 4.0 秒 + Lune ソース読み込み 約 0.6 秒 (初回。2回目以降はブラウザキャッシュで短縮) |
| 実行 (`--eval` 相当) | 6 ms — 体感ゼロ |
| 型チェック / 診断表示 | TYP0007 (witness・caret・hint 込み) が CLI と同一の出力 |
| did-you-mean → `fix` | TYP0001 の提案 → 自動修正がエディタに反映 (1 ms) |
| `fmt` | 6 ms で整形 |
| `explain` | 教材解説の全文表示 (1 ms) |

## 分かったこと・注意点

- **実装が Pure Python であることがそのまま武器になる**。WASM 化・移植は不要。
- 診断は ANSI カラーを使わないプレーンテキストなので、行頭パターン
  (`error[` / `warning[` / `= hint:` / `= help:`) の色付けだけで CLI 同等の見た目になる。
- Pyodide 本体のダウンロードは初回 約 10 MB。CDN 依存を避けるなら
  self-host も可能 (静的ファイルのみ)。
- モジュール import (`import` 文を含むプログラム) は未検証。複数ファイルを
  Pyodide FS に書けば `--module-path` 相当も動くはずだが、本格版で要確認。
- REPL・thunk 可視化は未実装 (PoC の範囲外)。

## 診断カタログページ

`errors.html` は `documents/ERROR_INDEX_JA.md` / `ERROR_INDEX.md` をその場で
レンダリングする静的ページ(日英切り替え付き)。Rust の error index に相当する。

## GitHub Pages

`.github/workflows/pages.yml` が main への push でリポジトリ全体を GitHub Pages
にデプロイする。ランディングページ(リポジトリルートの `index.html`)、
Playground、診断カタログが公開される。ページ内の fetch はすべて相対パスなので、
プロジェクトページのサブパス配信 (`/<repo>/...`) でもローカル配信でも動く。

## explain の言語切り替え

explain ボタンの隣のセレクタで、診断詳解を**日本語/英語**で切り替えられる
(`lune explain <CODE> --lang ja` と同じ内容。カタログは `lune/explanations_ja.py`)。

## トレース(遅延評価の観察)

「トレース」チェックボックスを有効にして実行すると、評価器の trace hook
(`set_trace_hook`)経由で **いつ・どの thunk が force されたか** が入れ子の
深さ付きで表示される(`REPL_SPEC.md` §5.2 と同じイベント)。プリセット
「無限ストリーム(トレースで観察)」が需要駆動の評価を見るデモになっている。

## 本格版への課題

1. エディタの強化 (CodeMirror 等、構文ハイライト・診断の行内表示)
2. 診断カタログ (`explain` 全コード) の常設ページ化
3. チュートリアルとの連動 (「このコードを Playground で開く」リンク)
4. GitHub Pages 等での静的ホスティング (サーバー不要で公開できる)
