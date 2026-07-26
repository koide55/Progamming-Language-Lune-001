#!/usr/bin/env bash
# 教科書を1冊の PDF に組む。
#
#   books/tools/build_pdf.sh [出力先.pdf]
#
# mdBook が生成する print.html（全ページを1枚に連結したもの）を、ヘッドレスの
# Chrome で印刷する。OUTLINE の「PDF が必要になったら print.html を第一候補と
# する」という方針そのままの実装。
#
# 紙面の調整は books/lune-book/theme/pdf.css（A4・章の改ページ・コード折り返し）
# と theme/head.hbs（print.html では演習の解答を開く）にある。

set -euo pipefail

BOOKS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BOOK_DIR="$BOOKS_DIR/lune-book"
OUT="${1:-$BOOK_DIR/lune-book.pdf}"

command -v mdbook > /dev/null || { echo "error: mdbook が必要です (brew install mdbook)" >&2; exit 1; }

CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
if [ ! -x "$CHROME" ]; then
    for c in chromium "Google Chrome for Testing"; do
        p=$(command -v "$c" || true)
        [ -n "$p" ] && { CHROME="$p"; break; }
    done
fi
[ -x "$CHROME" ] || { echo "error: Chrome が見つかりません。CHROME=... で指定してください" >&2; exit 1; }

echo "==> mdbook build"
( cd "$BOOK_DIR" && mdbook build )

# print.html は同ディレクトリの CSS/フォントを相対パスで読むので、file:// でも
# 解決できる。HTTP サーバーを立てる必要はない。
SRC="file://$BOOK_DIR/book/print.html"

echo "==> print.html -> PDF"
"$CHROME" --headless --disable-gpu --no-pdf-header-footer \
    --virtual-time-budget=20000 \
    --print-to-pdf="$OUT" "$SRC" 2> >(grep -v -E "ERROR:|allocator" >&2 || true)

[ -s "$OUT" ] || { echo "error: PDF が生成されませんでした" >&2; exit 1; }

if command -v pdfinfo > /dev/null; then
    pages=$(pdfinfo "$OUT" | awk '/^Pages:/ {print $2}')
    size=$(pdfinfo "$OUT" | awk -F'  +' '/^Page size:/ {print $2}')
    echo "==> $OUT ($pages ページ / $size)"
else
    echo "==> $OUT ($(wc -c < "$OUT" | tr -d ' ') bytes)"
fi
