#!/bin/bash
# 第68回プロシン デモのリハーサル検証。
# 全デモステップを実際に実行し、期待するキー出力が得られるか確認する。
# 使い方: リポジトリのルートで ./demo/prosym68/rehearse.sh
set -u
cd "$(dirname "$0")/../.." || exit 1

pass=0
fail=0

check() {
    local name="$1" expected="$2" actual="$3"
    if printf '%s' "$actual" | grep -qF "$expected"; then
        echo "ok   $name"
        pass=$((pass + 1))
    else
        echo "FAIL $name — expected to contain: $expected"
        printf '%s\n' "$actual" | head -10 | sed 's/^/     | /'
        fail=$((fail + 1))
    fi
}

# デモ1: 無限リストと :thunks
out=$(printf 'let nats = naturalsFrom(1)\n:thunks nats\ntake(nats, 5)\n:thunks nats\n' | ./bin/lune --repl 2>&1)
check "demo1: 定義直後は未評価"            "nats : unevaluated" "$out"
check "demo1: take で先頭だけ評価される"   "nats : evaluated = Cons(1, Cons(2, Cons(3, Cons(" "$out"
check "demo1: 無限リストから5要素"          "(1 2 3 4 5) : List[Int]" "$out"

# デモ2: :trace と メモ化
out=$(printf ':trace on\ntake(map(naturalsFrom(1), fn x: Int -> x * x), 3)\nlet y = 1 + 1\ny\ny\n' | ./bin/lune --repl 2>&1)
check "demo2: force が入れ子で見える"      "force naturalsFrom(1)" "$out"
check "demo2: 結果 (1 4 9)"                "(1 4 9) : List[Int]" "$out"
check "demo2: 2回目はメモ化される"          "memo 1 + 1 => 2" "$out"

# デモ3: 再帰サンク RUN0005 (GHC <<loop>> との対比)
out=$(./bin/lune --eval a --lang ja demo/prosym68/loop.lune 2>&1)
check "demo3: RUN0005 が日本語で出る"      "error[RUN0005]: 再帰的なサンク評価" "$out"
check "demo3: 直し方のヒントつき"           "再帰関数 (\`def\`) として書くか" "$out"

# デモ4a: did-you-mean → lune fix (typo.lune は書き換わるので /tmp で実行)
tmpfile=$(mktemp /tmp/prosym-typo-XXXXXX.lune)
cp demo/prosym68/typo.lune "$tmpfile"
out=$(./bin/lune --check --lang ja "$tmpfile" 2>&1)
check "demo4a: did-you-mean が出る"        "もしかして \`length\` ですか?" "$out"
out=$(./bin/lune fix --write "$tmpfile" 2>&1; ./bin/lune --check "$tmpfile" 2>&1)
check "demo4a: fix 後に型検査が通る"        "type check OK" "$out"
rm -f "$tmpfile"

# デモ4b: 網羅性の反例 TYP0007
out=$(./bin/lune --check --lang ja demo/prosym68/traffic.lune 2>&1)
check "demo4b: 反例 Yellow が出る"          "Yellow のケースがありません" "$out"

# クロージング: 説明の完全性はテストが強制している
out=$(PYTHONPATH=. python3 -m unittest tests.test_explanations 2>&1)
check "closing: 説明完全性テストが green"   "OK" "$out"

echo
echo "passed: $pass  failed: $fail"
[ "$fail" -eq 0 ] || exit 1
