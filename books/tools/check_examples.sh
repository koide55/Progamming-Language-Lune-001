#!/usr/bin/env bash
# books/ に載せるコード例を実 CLI で検証する。
#
#   books/tools/check_examples.sh
#
# 検証の種類:
#   check_ok   FILE                 --check が通ること
#   fmt_ok     FILE...              lune fmt --check が通ること（正準形であること）
#   eval_is    FILE BINDING EXPECT  --eval BINDING の出力が期待ファイルと一致すること
#   diag_is    FILE EXPECT          --check が失敗し、診断出力が期待ファイルと一致すること
#   fix_is     FILE EXPECT          lune fix の出力が期待ファイルと一致すること
#
# 診断出力中の絶対パスは、その例のディレクトリからの相対パスに正規化して比較する
# （紙面の表記規約と同じ）。

set -u
BOOKS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(cd "$BOOKS_DIR/.." && pwd)"
LUNE="$REPO_ROOT/bin/lune"

pass=0
fail=0

ok() { pass=$((pass + 1)); }
ng() {
    echo "FAIL: $1"
    fail=$((fail + 1))
}

check_ok() {
    local out
    if out=$("$LUNE" --check "$1" 2>&1); then ok; else ng "--check $1: $out"; fi
}

fmt_ok() {
    local out
    if out=$("$LUNE" fmt --check "$@" 2>&1); then ok; else ng "fmt --check $*: $out"; fi
}

eval_is() {
    local out
    out=$("$LUNE" --eval "$2" "$1" 2>&1)
    if printf '%s\n' "$out" | diff -u "$3" - > /dev/null; then
        ok
    else
        ng "--eval $2 $1: differs from $3"
        printf '%s\n' "$out" | diff -u "$3" - | head -20
    fi
}

diag_is() {
    local out
    if out=$("$LUNE" --check "$1" 2>&1); then
        ng "--check $1: unexpectedly passed"
        return
    fi
    out=$(printf '%s\n' "$out" | sed "s|$PWD/||g")
    if printf '%s\n' "$out" | diff -u "$2" - > /dev/null; then
        ok
    else
        ng "--check $1: diagnostic differs from $2"
        printf '%s\n' "$out" | diff -u "$2" - | head -20
    fi
}

fix_is() {
    local out
    out=$("$LUNE" fix "$1" 2>&1)
    if printf '%s\n' "$out" | diff -u "$2" - > /dev/null; then
        ok
    else
        ng "fix $1: differs from $2"
        printf '%s\n' "$out" | diff -u "$2" - | head -20
    fi
}

# --eval が失敗し、診断出力が期待ファイルと一致すること
eval_diag_is() { # file binding expect
    local out
    if out=$("$LUNE" --eval "$2" "$1" 2>&1); then
        ng "--eval $2 $1: unexpectedly succeeded"
        return
    fi
    out=$(printf '%s\n' "$out" | sed "s|$PWD/||g")
    if printf '%s\n' "$out" | diff -u "$3" - > /dev/null; then
        ok
    else
        ng "--eval $2 $1: diagnostic differs from $3"
        printf '%s\n' "$out" | diff -u "$3" - | head -20
    fi
}

# --eval --trace の stderr トレースが期待ファイルと一致すること
trace_is() { # file binding expect
    local out
    out=$("$LUNE" --eval "$2" --trace "$1" 2>&1 > /dev/null)
    if printf '%s\n' "$out" | diff -u "$3" - > /dev/null; then
        ok
    else
        ng "--eval $2 --trace $1: trace differs from $3"
        printf '%s\n' "$out" | diff -u "$3" - | head -20
    fi
}

# ----- 第1章 -----
cd "$BOOKS_DIR/examples/ch01"

check_ok hello.lune
eval_is hello.lune main expected/hello.main.txt

check_ok temperature.lune
eval_is temperature.lune table expected/temperature.table.txt

diag_is typo.lune expected/typo.check.txt
fix_is typo.lune expected/typo.fix.txt

diag_is arity.lune expected/arity.check.txt

check_ok answers/ex1-2.lune
eval_is answers/ex1-2.lune table expected/ex1-2.table.txt

check_ok answers/ex1-3.lune
eval_is answers/ex1-3.lune total expected/ex1-3.total.txt
eval_is answers/ex1-3.lune average expected/ex1-3.average.txt

check_ok answers/ex1-4.lune
eval_is answers/ex1-4.lune freezing expected/ex1-4.freezing.txt

fmt_ok hello.lune temperature.lune answers/ex1-2.lune answers/ex1-3.lune answers/ex1-4.lune

# ----- 第4章 -----
cd "$BOOKS_DIR/examples/ch04"

check_ok myif.lune
eval_is myif.lune taken expected/myif.taken.txt
eval_is myif.lune skipped expected/myif.skipped.txt

check_ok trace_demo.lune
eval_is trace_demo.lune answer expected/trace_demo.answer.txt
trace_is trace_demo.lune answer expected/trace_demo.trace.txt

check_ok box.lune
eval_is box.lune ok expected/box.ok.txt

check_ok point.lune
eval_diag_is point.lune p expected/point.p.txt

diag_is recursive.lune expected/recursive.check.txt
eval_diag_is recursive.lune x expected/recursive.x.txt

check_ok answers/ex4-2.lune
eval_is answers/ex4-2.lune shortCircuited expected/ex4-2.shortCircuited.txt

fmt_ok myif.lune trace_demo.lune box.lune point.lune recursive.lune answers/ex4-2.lune

# ----- 結果 -----
echo "passed: $pass, failed: $fail"
[ "$fail" -eq 0 ]
