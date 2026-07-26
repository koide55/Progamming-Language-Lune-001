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
#   fmt_is     FILE EXPECT          lune fmt の整形結果が期待ファイルと一致すること
#
# 診断出力中の絶対パスは、その例のディレクトリからの相対パスに正規化して比較する
# （紙面の表記規約と同じ）。

set -u
BOOKS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(cd "$BOOKS_DIR/.." && pwd)"
LUNE="$REPO_ROOT/bin/lune"

# 本書の表記規約（第1章「表記について」）どおり、診断は LUNE_LANG=ja の
# 日本語出力で検証する。全章（第1〜8章）が日本語表示に移行済み。
export LUNE_LANG=ja

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
    out=$(printf '%s\n' "$out" | sed "s|$PWD/||g; s|$PWD|.|g")
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

# lune fmt の出力が期待ファイルと一致すること（整形結果そのものを紙面に載せる場合）
fmt_is() { # file expect
    local out
    out=$("$LUNE" fmt "$1" 2>&1)
    if printf '%s\n' "$out" | diff -u "$2" - > /dev/null; then
        ok
    else
        ng "fmt $1: differs from $2"
        printf '%s\n' "$out" | diff -u "$2" - | head -20
    fi
}

# --check が警告付きで成功し、出力が期待ファイルと一致すること
check_warn_is() { # file expect
    local out
    if ! out=$("$LUNE" --check "$1" 2>&1); then
        ng "--check $1: unexpectedly failed"
        return
    fi
    out=$(printf '%s\n' "$out" | sed "s|$PWD/||g; s|$PWD|.|g")
    if printf '%s\n' "$out" | diff -u "$2" - > /dev/null; then
        ok
    else
        ng "--check $1: warning output differs from $2"
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
    out=$(printf '%s\n' "$out" | sed "s|$PWD/||g; s|$PWD|.|g")
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

# ----- 第2章 -----
cd "$BOOKS_DIR/examples/ch02"

check_ok grade.lune
eval_is grade.lune result expected/grade.result.txt

diag_is annot.lune expected/annot.check.txt
diag_is lex.lune expected/lex.check.txt
diag_is indent.lune expected/indent.check.txt

check_ok answers/ex2-3.lune
eval_is answers/ex2-3.lune bmi expected/ex2-3.bmi.txt

check_ok answers/ex2-4.lune
eval_is answers/ex2-4.lune swapped expected/ex2-4.swapped.txt

fmt_ok grade.lune answers/ex2-3.lune answers/ex2-4.lune

# ----- 第3章 -----
cd "$BOOKS_DIR/examples/ch03"

check_ok pipeline.lune
eval_is pipeline.lune result expected/pipeline.result.txt
eval_is pipeline.lune eleven expected/pipeline.eleven.txt

check_ok hof.lune
eval_is hof.lune fortyTwo expected/hof.fortyTwo.txt
eval_is hof.lune seven expected/hof.seven.txt

diag_is norettype.lune expected/norettype.check.txt

check_ok answers/ex3-2.lune
eval_is answers/ex3-2.lune answer expected/ex3-2.answer.txt

check_ok answers/ex3-3.lune
eval_is answers/ex3-3.lune answer expected/ex3-3.answer.txt

check_ok answers/ex3-4.lune
eval_is answers/ex3-4.lune answer expected/ex3-4.answer.txt

fmt_ok pipeline.lune hof.lune norettype.lune answers/ex3-2.lune answers/ex3-3.lune answers/ex3-4.lune

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

# ----- 第5章 -----
cd "$BOOKS_DIR/examples/ch05"

check_ok shape.lune
eval_is shape.lune circleArea expected/shape.circleArea.txt
eval_is shape.lune rectArea expected/shape.rectArea.txt
eval_is shape.lune squareness expected/shape.squareness.txt

diag_is missing.lune expected/missing.check.txt
diag_is refutable.lune expected/refutable.check.txt
check_warn_is unreachable.lune expected/unreachable.check.txt

check_ok maybediv.lune
eval_is maybediv.lune half expected/maybediv.half.txt
eval_is maybediv.lune broke expected/maybediv.broke.txt
eval_is maybediv.lune nothing expected/maybediv.nothing.txt
eval_is maybediv.lune ratio expected/maybediv.ratio.txt
eval_is maybediv.lune viaNull expected/maybediv.viaNull.txt

check_ok answers/ex5-2.lune
eval_is answers/ex5-2.lune afterRed expected/ex5-2.afterRed.txt
eval_is answers/ex5-2.lune afterTwo expected/ex5-2.afterTwo.txt

check_ok answers/ex5-3.lune
eval_is answers/ex5-3.lune good expected/ex5-3.good.txt
eval_is answers/ex5-3.lune bad expected/ex5-3.bad.txt

check_ok answers/ex5-4.lune
eval_is answers/ex5-4.lune some expected/ex5-4.some.txt
eval_is answers/ex5-4.lune none expected/ex5-4.none.txt

fmt_ok shape.lune missing.lune refutable.lune unreachable.lune maybediv.lune answers/ex5-2.lune answers/ex5-3.lune answers/ex5-4.lune

# ----- 第6章 -----
cd "$BOOKS_DIR/examples/ch06"

check_ok user.lune
eval_is user.lune hello expected/user.hello.txt
eval_is user.lune ada expected/user.ada.txt

check_ok items.lune
eval_is items.lune total expected/items.total.txt

diag_is typofield.lune expected/typofield.check.txt

check_ok answers/ex6-2.lune
eval_is answers/ex6-2.lune pricey expected/ex6-2.pricey.txt

check_ok answers/ex6-3.lune
eval_is answers/ex6-3.lune swapped expected/ex6-3.swapped.txt

fmt_ok user.lune items.lune typofield.lune answers/ex6-2.lune answers/ex6-3.lune

# ----- 第7章 -----
cd "$BOOKS_DIR/examples/ch07"

check_ok orzero.lune
eval_is orzero.lune unwrapped expected/orzero.unwrapped.txt
eval_is orzero.lune defaulted expected/orzero.defaulted.txt

check_ok nameof.lune
eval_is nameof.lune someName expected/nameof.someName.txt
eval_is nameof.lune noName expected/nameof.noName.txt
eval_is nameof.lune fallback expected/nameof.fallback.txt

check_ok maybediv.lune
eval_is maybediv.lune some expected/maybediv.some.txt
eval_is maybediv.lune none expected/maybediv.none.txt
eval_is maybediv.lune fallback expected/maybediv.fallback.txt

check_ok maybedivlet.lune
eval_is maybedivlet.lune viaLet expected/maybedivlet.viaLet.txt

diag_is missingnull.lune expected/missingnull.check.txt
diag_is misuse.lune expected/misuse.check.txt

check_ok answers/ex7-4.lune
eval_is answers/ex7-4.lune some expected/ex7-4.some.txt
eval_is answers/ex7-4.lune none expected/ex7-4.none.txt
eval_is answers/ex7-4.lune safe expected/ex7-4.safe.txt

fmt_ok orzero.lune nameof.lune maybediv.lune maybedivlet.lune missingnull.lune misuse.lune answers/ex7-4.lune

# ----- 第8章 -----
cd "$BOOKS_DIR/examples/ch08"

check_ok infinite.lune
eval_is infinite.lune firstFive expected/infinite.firstFive.txt
eval_is infinite.lune powersOfTwo expected/infinite.powersOfTwo.txt
eval_is infinite.lune threeSevens expected/infinite.threeSevens.txt
eval_is infinite.lune pattern expected/infinite.pattern.txt

check_ok fib.lune
eval_is fib.lune first10 expected/fib.first10.txt

check_ok primes.lune
eval_is primes.lune first10 expected/primes.first10.txt

check_ok answers/ex8-2.lune
eval_is answers/ex8-2.lune evenSquares expected/ex8-2.evenSquares.txt

check_ok answers/ex8-3.lune
eval_is answers/ex8-3.lune smoothed expected/ex8-3.smoothed.txt

check_ok answers/ex8-4.lune
eval_is answers/ex8-4.lune first10 expected/ex8-4.first10.txt

fmt_ok infinite.lune fib.lune primes.lune answers/ex8-2.lune answers/ex8-3.lune answers/ex8-4.lune

# ----- 第9章 -----
cd "$BOOKS_DIR/examples/ch09"

check_ok counter.lune
eval_is counter.lune answer expected/counter.answer.txt

check_ok fortotal.lune
eval_is fortotal.lune total expected/fortotal.total.txt

check_ok io.lune
eval_is io.lune run expected/io.run.txt

diag_is badfor.lune expected/badfor.check.txt

check_ok answers/ex9-1.lune
eval_is answers/ex9-1.lune product expected/ex9-1.product.txt

check_ok answers/ex9-2.lune
eval_is answers/ex9-2.lune run expected/ex9-2.run.txt

fmt_ok counter.lune fortotal.lune io.lune badfor.lune answers/ex9-1.lune answers/ex9-2.lune

# ----- 第10章 -----
cd "$BOOKS_DIR/examples/ch10"

check_ok main.lune
eval_is main.lune area expected/main.area.txt
eval_is main.lune banner expected/main.banner.txt

diag_is cycle_a.lune expected/cycle_a.check.txt
diag_is badname.lune expected/badname.check.txt
diag_is missing.lune expected/missing.check.txt

# --module-path 付きの解決（付けないと MOD0001 になることも確認する）
if "$LUNE" --check usesshared.lune > /dev/null 2>&1; then
    ng "--check usesshared.lune: unexpectedly passed without --module-path"
else
    ok
fi
check_ok_args() { # args... file
    local out
    if out=$("$LUNE" "$@" 2>&1); then ok; else ng "$*: $out"; fi
}
check_ok_args --module-path lib --check usesshared.lune
eval_is_args() { # expect -- args...
    local expect="$1"
    shift 2
    local out
    out=$("$LUNE" "$@" 2>&1)
    if printf '%s\n' "$out" | diff -u "$expect" - > /dev/null; then
        ok
    else
        ng "$*: differs from $expect"
        printf '%s\n' "$out" | diff -u "$expect" - | head -20
    fi
}
eval_is_args expected/usesshared.answer.txt -- --module-path lib --eval answer usesshared.lune

check_ok answers/shop_main.lune
eval_is answers/shop_main.lune sum expected/shop_main.sum.txt

fmt_ok main.lune geometry.lune util/text.lune cycle_a.lune cycle_b.lune badname.lune mismatch.lune missing.lune usesshared.lune lib/shared.lune answers/shop/items.lune answers/shop_main.lune

# ----- 第11章 -----
cd "$BOOKS_DIR/examples/ch11"

diag_is typos.lune expected/typos.check.txt
fix_is typos.lune expected/typos.fix.txt

check_ok rps.lune
eval_is rps.lune win expected/rps.win.txt
eval_is rps.lune lose expected/rps.lose.txt
eval_is rps.lune draw expected/rps.draw.txt

diag_is rps_missing.lune expected/rps_missing.check.txt

check_ok answers/ex11-3.lune
eval_is answers/ex11-3.lune won expected/ex11-3.won.txt
eval_is answers/ex11-3.lune lost expected/ex11-3.lost.txt
eval_is answers/ex11-3.lune tied expected/ex11-3.tied.txt

fmt_ok typos.lune rps.lune rps_missing.lune answers/ex11-3.lune

# ----- 第12章 -----
cd "$BOOKS_DIR/examples/ch12"

check_ok tidy.lune
eval_is tidy.lune answer expected/tidy.answer.txt
fmt_is messy.lune expected/messy.fmt.txt

check_ok answers/ex12-3.lune
eval_is answers/ex12-3.lune tripled expected/ex12-3.tripled.txt
eval_is answers/ex12-3.lune doubled expected/ex12-3.doubled.txt

fmt_ok tidy.lune answers/ex12-3.lune

# ----- 第13章 -----
cd "$BOOKS_DIR/examples/ch13"

check_ok stats.lune
eval_is stats.lune summary expected/stats.summary.txt
eval_is stats.lune average expected/stats.average.txt
eval_is stats.lune emptyAverage expected/stats.emptyAverage.txt

check_ok ledger_main.lune
eval_is ledger_main.lune balance expected/ledger.balance.txt
eval_is ledger_main.lune expenses expected/ledger.expenses.txt
eval_is ledger_main.lune rejected expected/ledger.rejected.txt
eval_is ledger_main.lune accepted expected/ledger.accepted.txt

check_ok collatz.lune
eval_is collatz.lune fromSix expected/collatz.fromSix.txt
eval_is collatz.lune fromSeven expected/collatz.fromSeven.txt

check_ok counted.lune
eval_is counted.lune firstTwo expected/counted.firstTwo.txt
eval_is counted.lune cost expected/counted.cost.txt

check_ok answers/ex13-1.lune
eval_is answers/ex13-1.lune summary expected/ex13-1.summary.txt
eval_is answers/ex13-1.lune emptySummary expected/ex13-1.emptySummary.txt

fmt_ok stats.lune ledger/entry.lune ledger_main.lune collatz.lune counted.lune answers/ex13-1.lune

# ----- 結果 -----
echo "passed: $pass, failed: $fail"
[ "$fail" -eq 0 ]
