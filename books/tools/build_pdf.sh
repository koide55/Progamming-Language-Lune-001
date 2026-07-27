#!/usr/bin/env bash
# 教科書を1冊の PDF に組む。
#
#   books/tools/build_pdf.sh [出力先.pdf]
#
# mdBook が生成する print.html（全ページを1枚に連結したもの）を、ヘッドレスの
# Chrome で印刷する。OUTLINE の「PDF が必要になったら print.html を第一候補と
# する」という方針そのままの実装。
#
# 目次と索引にページ番号を入れるため 2 パスで組む。mdBook にページの概念はなく、
# ページ番号は組み上がった PDF から実測するしかない。
#
#   1 パス目: ページ番号なしの目次で組み、各章の開始ページを測る
#   2 パス目: 測った番号を入れた目次と索引で組み直す
#   検算:     2 パス目で章の開始ページが動いていないことを確かめる
#             （動いていたら目次の行数が変わったということで、番号が嘘になる）
#
# 紙面の調整は books/lune-book/theme/pdf.css（表紙・A4・コード折り返し）と
# theme/head.hbs（print.html では演習の解答を開く）にある。

set -euo pipefail

BOOKS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BOOK_DIR="$BOOKS_DIR/lune-book"
SRC_DIR="$BOOK_DIR/src"
OUT="${1:-$BOOK_DIR/lune-book.pdf}"
PAGES_TOOL="$BOOKS_DIR/tools/book_pages.py"

command -v mdbook > /dev/null || { echo "error: mdbook が必要です (brew install mdbook)" >&2; exit 1; }
command -v pdftotext > /dev/null || { echo "error: pdftotext が必要です (brew install poppler)" >&2; exit 1; }

# しおりの注入だけ pikepdf が要る。無ければその工程を飛ばす（PDF 自体はできる）。
# システムの python は PEP 668 で保護されていて pip が使えないことがあるので、
# venv を指す PYTHON を渡せるようにしてある。
#   python3 -m venv .venv && .venv/bin/pip install pikepdf
#   PYTHON=.venv/bin/python books/tools/build_pdf.sh
PYTHON="${PYTHON:-python3}"

CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
if [ ! -x "$CHROME" ]; then
    for c in chromium "Google Chrome for Testing"; do
        p=$(command -v "$c" || true)
        [ -n "$p" ] && { CHROME="$p"; break; }
    done
fi
[ -x "$CHROME" ] || { echo "error: Chrome が見つかりません。CHROME=... で指定してください" >&2; exit 1; }

# 目次と索引は生成物だが、HTML 版のためにページ番号なしの版をコミットしてある。
# ビルド中はページ番号入りに差し替えるので、終了時に必ず戻す。
TMP=$(mktemp -d)
cp "$SRC_DIR/00-toc.md" "$TMP/toc.md"
cp "$SRC_DIR/zz-index.md" "$TMP/index.md"
restore() {
    cp "$TMP/toc.md" "$SRC_DIR/00-toc.md"
    cp "$TMP/index.md" "$SRC_DIR/zz-index.md"
    rm -rf "$TMP"
}
trap restore EXIT

render() { # 出力先
    ( cd "$BOOK_DIR" && mdbook build > /dev/null )
    # print.html は CSS/フォントを相対パスで読むので file:// でも解決できる
    "$CHROME" --headless --disable-gpu --no-pdf-header-footer \
        --virtual-time-budget=20000 \
        --print-to-pdf="$1" "file://$BOOK_DIR/book/print.html" \
        2> >(grep -v -E "ERROR:|allocator|bytes written" >&2 || true)
    [ -s "$1" ] || { echo "error: PDF が生成されませんでした" >&2; exit 1; }
}

echo "==> 1 パス目 (ページ番号を測る)"
render "$TMP/pass1.pdf"
before=$("$PYTHON" "$PAGES_TOOL" starts --pdf "$TMP/pass1.pdf")

echo "==> 目次と索引を生成"
"$PYTHON" "$PAGES_TOOL" toc   --pdf "$TMP/pass1.pdf"
"$PYTHON" "$PAGES_TOOL" index --pdf "$TMP/pass1.pdf"

echo "==> 2 パス目"
render "$OUT"

after=$("$PYTHON" "$PAGES_TOOL" starts --pdf "$OUT")
if [ "$before" != "$after" ]; then
    echo "warning: 2 パスの間で章の開始ページが動きました。目次のページ番号がずれています。" >&2
    echo "         目次の行数が変わったのが原因です。" >&2
else
    echo "==> 検算: 章の開始ページは 2 パスで一致 (目次のページ番号は正しい)"
fi

echo "==> しおりを付ける"
"$PYTHON" "$PAGES_TOOL" bookmarks --pdf "$OUT"

if command -v pdfinfo > /dev/null; then
    pages=$(pdfinfo "$OUT" | awk '/^Pages:/ {print $2}')
    size=$(pdfinfo "$OUT" | awk -F'  +' '/^Page size:/ {print $2}')
    echo "==> $OUT ($pages ページ / $size)"
else
    echo "==> $OUT ($(wc -c < "$OUT" | tr -d ' ') bytes)"
fi
