# Lune v0.1 チュートリアル

小さな遅延評価言語で遊んでみよう。

Lune はまだ初期バージョンの実験的な言語です。それでも、すでにいくつかの楽しい特徴があります。

- Python 風のインデント構文。
- ML 風の `fn`、`type`、`match`。
- デフォルト遅延評価。
- 部分適用で自然にクロージャを作れる。
- `Option` / `Result` / `List` が最初から使える。
- 軽量な `record` とフィールドアクセス。
- `while` で小さな命令的ループも書ける。
- `for` でリストを自然に走査できる。
- 小さな型チェッカつき。
- `T?`（nullable）で「無いかもしれない値」を安全に扱える。
- `|>` で処理を左から右へつなげる。
- 教えてくれるツール: `lune explain` / `lune fmt` / `lune fix`。

このチュートリアルでは、Lune の「書いていて楽しいところ」を、実際に動くコードで順番に見ていきます。

## 1. はじめの一歩

作業ディレクトリ:

```sh
cd lune_v0_1
```

式や宣言を試すなら REPL が便利です。

```sh
./bin/lune
```

引数なしの `./bin/lune` は REPL を起動します。ファイルを指定したいときは、同じスクリプトへ CLI 引数を渡します。

端末で起動した REPL は、Bash のコマンドラインのように行編集できます。

- 左右キーでカーソル移動。
- 上下キーで履歴をたどる。
- Backspace / Delete で編集。
- `Ctrl-A` で行頭、`Ctrl-E` で行末へ移動。

履歴は可能なら `~/.lune_history` に保存されます。少し前に試した式を上キーで呼び戻せるので、試行錯誤がぐっと楽になります。

ファイルを評価する場合:

```sh
./bin/lune --eval answer samples/records.lune
```

型チェックだけしたい場合:

```sh
./bin/lune --check samples/records.lune
```

## 2. `let` は遅延される

Lune の `let` は、値をすぐには計算しません。必要になるまで待ちます。

```lune
let x = 1 + 2
let answer = x * 10
```

これは普通に見えます。でも、遅延評価が効いていることは、失敗する式を置くとよく分かります。

```lune
let danger = crash()
let answer = 42
```

`answer` を評価しても `danger` は使われないので、`crash()` は評価されません。

```sh
./bin/lune --eval answer your_file.lune
```

結果:

```text
42
```

遅延評価の感覚は、「値を置いておく」のではなく「必要になったら計算する約束を置いておく」に近いです。

## 3. 関数引数も遅延される

関数の引数も、デフォルトでは遅延されます。

```lune
def first(a: Int, b: Int): Int =
    a

let answer = first(10, crash())
```

`first` は `b` を使わないので、`crash()` は評価されません。

```text
answer == 10
```

これは、条件付きの計算や無限データ構造を扱うときに強力です。使わないものを作らなくていい、という気楽さがあります。

## 4. strict で「今すぐ評価」を選ぶ

遅延がうれしい場面もあれば、すぐ評価したい場面もあります。その時は `strict` や `!` を使います。

```lune
def ignore(a: Int, !b: Int): Int =
    a

let answer = ignore(10, crash())
```

この場合、`b` は正格引数なので、関数呼び出し時に `crash()` が評価されます。

束縛にも使えます。

```lune
strict let x = 1 + 2
```

Lune では「基本は遅延、必要なところだけ正格」という使い分けをします。

## 5. `lazy` と `force`

明示的に遅延値を作りたいときは `lazy` を使います。

```lune
let delayed = lazy (1 + 2)
let answer = force delayed
```

`delayed` の型は `Lazy[Int]`、`answer` は `Int` です。

複数行にもできます。

```lune
let delayed = lazy:
    let x = 40
    x + 2

let answer = force delayed
```

`lazy` は「あとで開ける箱」のようなものです。`force` すると中身が計算されます。

## 6. メモ化されるサンク

遅延値は、一度評価されると結果を覚えます。

この章では観察用に `tick()` と `tickCount()` を使います。

- `tick()` は呼ばれるたびに内部カウンタを 1 増やし、その値を返します。
- `tickCount()` は現在のカウンタ値を返します。

どちらも遅延評価の動きを見るための補助関数です。普通のアプリケーションロジックで積極的に使うものではありません。

```lune
let x = tick()
let answer = x + x
let count = tickCount()
```

`x` は 2 回使われていますが、`tick()` は 1 回だけ実行されます。

```text
answer == 2
count == 1
```

もし `tick()` が 2 回実行されていたら、`answer` は `1 + 2` で `3` になり、`count` も `2` になっていたはずです。実際には `x` のサンクが最初に必要になった時点で `tick()` が 1 回だけ実行され、その結果 `1` が保存されます。2 回目の `x` は保存済みの `1` を読むだけです。

REPL でも試せます。

```text
lune> let x = tick()
ok
lune> x + x
2 : Int
lune> tickCount()
1 : Int
```

`tickCount()` 自体はカウンタを増やしません。いま何回 `tick()` が本当に実行されたかを見る窓です。

この「必要になるまで待つ」と「一度計算したら覚える」の組み合わせが、Lune の遅延評価の核です。

### 評価を目で見る — `:thunks` と `:trace`

ここまでの章の内容は、REPL の 2 つのコマンドで**直接観察**できます。

`:thunks` は、遅延束縛がいまどの状態かを表示します。表示のために評価が走ることはありません。

```text
lune> let x = 1 + 1
ok
lune> :thunks
x : unevaluated          # まだ計算されていない
lune> x
2 : Int
lune> :thunks
x : evaluated = 2        # 一度使ったので、結果が保存された
```

`:trace on` を有効にすると、式の評価で「いつ・何が force されたか」が入れ子で表示されます。

```text
lune> :trace on
trace on
lune> let y = x + 1
ok                       # 宣言では何も評価されない
lune> y * 10
force y * 10
  force x + 1            # y が必要になって初めて評価される
    memo 1 + 1 => 2      # x はメモ化済み。再計算されない
  => 3
=> 30
30 : Int
```

無限リスト（第 12 章）と組み合わせると、「必要な分だけ計算される」ことが構造で見えます。未評価の部分は `<thunk>` と表示されます。

```text
lune> let nat = naturalsFrom(1)
ok
lune> head(nat)
Some(1) : Option[Int]
lune> :thunks nat
nat : evaluated = Cons(1, <thunk>)   # 先頭だけ計算済み。続きはまだ計算されていない
```

ファイルに対しては `./bin/lune --eval NAME --trace file.lune` で同じトレースを表示できます。ブラウザ Playground（`playground/`）にも「トレース」チェックボックスがあり、同じ観察をインストールなしで試せます。

## 7. `fn` と部分適用

ラムダは `fn` で書きます。

```lune
let add = fn x y -> x + y
let answer = add(20, 22)
```

部分適用もできます。

```lune
let add = fn x y -> x + y
let inc = add(1)
let answer = inc(41)
```

`add` は本来 2 つ引数を受け取る関数ですが、1 つだけ引数を渡す `add(1)` は、「あと 1 つ引数を受け取ったら足し算する関数」を返します。

つまり、こういう小さな道具を簡単に作れます。

```lune
let double = fn x -> x * 2
let add10 = fn x -> x + 10

let answer = add10(double(16))
```

こうした小さな関数は `|>`（パイプライン）でつなげます。`x |> f` は `f(x)` と同じで、処理を左から右へ読めます。

```lune
def inc(n: Int): Int =
    n + 1

def double(n: Int): Int =
    n * 2

let result = 5 |> inc |> double
```

`5 |> inc |> double` は `double(inc(5))` と同じで、結果は `12` です。多引数の関数に部分適用としてつなぐこともできます（`5 |> add` は `add(5)`）。

## 8. 代数的データ型で「形」を作る

Lune は代数的データ型を持っています。英語では Algebraic Data Type と呼ばれ、略して ADT と書かれることもあります。

名前は少し大げさですが、最初は「値が取りうる形を、型として並べる仕組み」だと思えば十分です。

```lune
type Option[T] =
    | Some(value: T)
    | None
```

この `Option[T]` は、値の形が 2 種類ある型です。

- `Some(value)` は「値がある」形。
- `None` は「値がない」形。

値があるかもしれない、ないかもしれない、という状態を `null` ではなく型で表せます。

```lune
let good = Some(42)
let empty = None
```

取り出すときは `match` を使います。

```lune
def getOrElse[T](option: Option[T], defaultValue: T): T =
    match option:
        | Some(value) -> value
        | None -> defaultValue

let answer = getOrElse(Some(42), 0)
```

`match` は「値の形に応じて分岐する」ための構文です。

## 9. パターンマッチは読みやすい

もう少し例を見ましょう。

```lune
type Shape =
    | Circle(radius: Int)
    | Rect(width: Int, height: Int)

def area(shape: Shape): Int =
    match shape:
        | Circle(radius) -> radius * radius * 3
        | Rect(width, height) -> width * height

let answer = area(Rect(6, 7))
```

`if` で種類を調べるのではなく、「この形ならこう」と直接書けます。

代数的データ型と `match` は、Lune の関数型らしさがよく出る部分です。

`match` は網羅性もチェックします。ある形を書き忘れると、型チェッカが「どの形が漏れているか」を例つきで教えてくれます。

```lune
def area(shape: Shape): Int =
    match shape:
        | Circle(radius) -> radius * radius * 3
```

これは `Rect` が漏れているので `TYP0007` エラーになります。すべての形を書くか、`| _ -> ...` のワイルドカードを足すと通ります。逆に、前のケースに完全に覆われて絶対に届かないケースは警告（`TYP0009`）になります。

## 10. レコードで名前付きデータを作る

複数の値をまとめたいだけなら、`record` が便利です。

```lune
record User:
    name: String
    age: Int

let ada = User(name = "Ada", age = 36)
let answer = ada.age + 6
```

フィールドには `.` でアクセスします。

```lune
let name = ada.name
let age = ada.age
```

generic record も使えます。

```lune
record Box[T]:
    value: T

let boxed = Box(value = 42)
let answer = boxed.value
```

REPL でレコード値を見ると、フィールド中心の形で表示されます。

```text
lune> ada
{ name = "Ada", age = 36 } : User
```

レコードの通常フィールドも遅延されます。使わないフィールドは評価されません。

```lune
record User:
    name: String
    age: Int

let ada = User(name = crash(), age = 36)
let answer = ada.age
```

この場合、`name` は参照されないので `crash()` は評価されません。

## 11. null と安全に付き合う

「値が無いかもしれない」ことは、`T?`（nullable 型）で表します。

```lune
let name: String? = "Ada"
let missing: String? = null
```

非 null の値も `null` も `T?` に入れられます。でも `null` を非 null の型（`String` など）へ入れることはできません。ここが Lune の安全なところで、うっかり null を混ぜても型チェッカが止めてくれます。

`T?` の中身を使うには、まず「null かどうか」を確かめてアンラップします。方法はいくつかあります。

### `match` で分解する

`match` は `null` と中身の両方を扱えます。`null` を先に処理すると、続く名前は非 null に絞り込まれます（narrowing）。

```lune
def orZero(value: Int?): Int =
    match value:
        | null -> 0
        | v -> v
```

`v` の枝では `value` が非 null と分かっているので、`v` は `Int` として使えます。`null` の枝を書き忘れると、網羅していないので型エラーになります。

### `??` でデフォルトを与える

`a ?? b` は、`a` が `null` のとき `b` を返します（`a` が非 null なら `b` は評価しません）。

```lune
let shown = missing ?? "anon"
```

### `if` で絞り込む

`if x != null then ...` の then 側では、`x` は非 null に絞り込まれます。

```lune
def orOne(x: Int?): Int =
    if x != null then x else 1
```

### `?.` で安全にたどる

レコードのフィールドは `?.` でたどれます。receiver が `null` なら、たどらずに `null` に短絡します。

```lune
record User:
    name: String
    age: Int

def nameOf(user: User?): String? =
    user?.name
```

`user?.name` の型は `String?` です。`nameOf(null)` は `null`、値があれば名前を返します。

### null かどうか比べる

`x == null` / `x != null` で確かめられます。

ここまでの機能は、サンプル `samples/nullable.lune` にまとまっています。

## 12. 標準ライブラリの小さな道具

Lune v0.1 では、いくつかの便利な型と関数が最初から使えます。

```lune
let xs = (1 2 3 4)
let doubled = map(xs, fn x -> x * 2)
let total = fold(doubled, 0, fn acc x -> acc + x)
let answer = total
```

`(1 2 3 4)` は Lisp 風のリストリテラルです。表示と同じ形で入力できます。`[1, 2, 3, 4]` も同じ意味です。

どちらも `Cons(1, Cons(2, Cons(3, Cons(4, Nil))))` と書く代わりに、短く自然に有限リストを作れます。

空リストは `[]` です。`()` は `Unit` なので、ここは分けて考えます。

`range(1, 5)` でも同じく `1, 2, 3, 4` のリストを作れます。

REPL ではリストは Lisp 風に表示されます。

```text
lune> [1, 2, 3, 4]
(1 2 3 4) : List[Int]
lune> (1 2 3 4)
(1 2 3 4) : List[Int]
lune> "Ada"
"Ada" : String
```

文字列はダブルクォートつきで表示されるので、リストやレコードの中に入っても読みやすくなります。

リストリテラルの要素も遅延されます。

```lune
let items = [1, crash()]
let answer = head(items)
```

`answer` は `Some(1)` です。2 番目の要素は、必要になるまで眠ったままです。

### リスト操作の基本セット

Lune のリスト処理は、まずこの 7 つを覚えるとかなり書けます。

```lune
map(list, fn x -> ...)
filter(list, fn x -> ...)
fold(list, initial, fn acc x -> ...)
take(list, count)
drop(list, count)
head(list)
tail(list)
```

`map` は、各要素を変換します。

```lune
let numbers = [1, 2, 3, 4]
let doubled = map(numbers, fn x -> x * 2)
```

REPL:

```text
lune> doubled
(2 4 6 8) : List[Int]
```

`filter` は、条件に合う要素だけを残します。

```lune
let numbers = [1, 2, 3, 4, 5, 6]
let evens = filter(numbers, fn x -> x % 2 == 0)
```

```text
lune> evens
(2 4 6) : List[Int]
```

`fold` は、リストを 1 つの値に畳み込みます。合計、最大値、文字列化などに使います。

```lune
let numbers = [1, 2, 3, 4]
let total = fold(numbers, 0, fn acc x -> acc + x)
```

`acc` は「ここまでの結果」です。最初は `0`、次に `1`、次に `3`、次に `6`、最後に `10` になります。

`take` と `drop` は、リストを前から切り出す道具です。

```lune
let numbers = [1, 2, 3, 4, 5, 6]
let firstThree = take(numbers, 3)
let afterThree = drop(numbers, 3)
```

```text
lune> firstThree
(1 2 3) : List[Int]
lune> afterThree
(4 5 6) : List[Int]
```

ページングのような処理も書けます。

```lune
let numbers = [1, 2, 3, 4, 5, 6]
let page1 = take(numbers, 2)
let page2 = take(drop(numbers, 2), 2)
let page3 = take(drop(numbers, 4), 2)
```

`head` と `tail` は、リストの先頭と残りを安全に取り出します。空リストがあるので、戻り値は `Option` です。

```lune
let numbers = [1, 2, 3]
let first = head(numbers)
let rest = tail(numbers)
let missing = head([])
```

```text
lune> first
Some(1) : Option[Int]
lune> rest
Some((2 3)) : Option[List[Int]]
lune> missing
None : Option[Any]
```

値として使いたいときは `getOrElse` が便利です。

```lune
let firstNumber = getOrElse(head([10, 20]), 0)
let emptyNumber = getOrElse(head([]), 0)
```

`firstNumber` は `10`、`emptyNumber` は `0` です。

### 組み合わせる

リスト関数は、単体より組み合わせたときに気持ちよくなります。

```lune
let numbers = [1, 2, 3, 4, 5, 6]
let answer =
    fold(
        map(
            filter(numbers, fn x -> x % 2 == 0),
            fn x -> x * 10
        ),
        0,
        fn acc x -> acc + x
    )
```

これは「偶数だけ残す」「10 倍する」「合計する」という流れです。`answer` は `120` です。

`record` と組み合わせると、もう少し実用的なコードになります。

```lune
record User:
    name: String
    age: Int

let users = [
    User(name = "Ada", age = 36),
    User(name = "Grace", age = 85),
    User(name = "Linus", age = 55),
]

let names = map(users, fn user: User -> user.name)
let elders = filter(users, fn user: User -> user.age >= 60)
let elderNames = map(elders, fn user: User -> user.name)
let totalAge = fold(users, 0, fn acc: Int user: User -> acc + user.age)
```

```text
lune> names
("Ada" "Grace" "Linus") : List[String]
lune> elderNames
("Grace") : List[String]
lune> totalAge
176 : Int
```

### 遅延評価とリスト関数

`take` は、必要な分だけ取り出すための道具です。`take(list, 0)` は list 自体を評価しません。

```lune
let safe = take(crash(), 0)
```

これは `()`、つまり空リストとして扱えます。

さらに、`take` が返したリストの tail も遅延されます。

```lune
let one = take([1, crash()], 1)
```

```text
lune> one
(1) : List[Int]
```

2 番目の要素は、結果に含まれないので評価されません。遅延評価はここでかなり実感しやすいです。

### サンプルファイル

この章のまとまった例は `samples/list_tools.lune` にあります。

```sh
./bin/lune --check samples/list_tools.lune
./bin/lune --eval doubled samples/list_tools.lune
./bin/lune --eval adultNames samples/list_tools.lune
```

`Option` も組み込み済みです。

```lune
let value = Some(42)
let answer = getOrElse(value, 0)
```

標準ライブラリはまだ小さいですが、「毎回自分で `Option` や `List` を定義しなくてよい」だけでも、試し書きがずいぶん楽になります。

## 13. `while` で小さなループを書く

Lune は関数型の機能を大事にしていますが、ちょっとした反復処理には `while` も使えます。

```lune
let answer =
    var i = 0
    var total = 0
    while i < 5:
        total = total + i
        i = i + 1
    total
```

`answer` は `0 + 1 + 2 + 3 + 4` なので `10` になります。

`while` の条件は毎回評価されます。条件が `false` になったらループを抜け、`while` 自体は `Unit` を返します。

```lune
let answer =
    var i = 0
    while i < 3:
        i = i + 1
    i
```

この例では `answer` は `3` です。

遅延評価との関係も大事です。条件が最初から `false` なら、body は実行されません。

```lune
let answer =
    while false:
        crash()
    42
```

この場合、`crash()` は評価されません。

`while` は便利ですが、Lune らしいデータ変換では `map`、`filter`、`fold` の方が読みやすい場面もあります。小さな手続きには `while`、データの流れには関数、という使い分けが気持ちよいです。

同じ処理は再帰でも書けます。

```lune
def sumUntil(i: Int, end: Int, total: Int): Int =
    if i >= end then total else sumUntil(i + 1, end, total + i)

let answer = sumUntil(0, 5, 0)
```

この `answer` も `10` です。

`while` 版は、変数を更新しながら手順を追うので、初めて読む人に分かりやすいことがあります。再帰版は、状態を引数として渡していくので、関数型らしく、テストしやすい小さな部品になります。

Lune ではどちらも選べます。ちょっとした手続きは `while`、値の変換や再利用したい計算は再帰や `fold`、という感覚で使い分けるとよいでしょう。

## 14. `for` でリストを歩く

`while` は条件が続く限り繰り返す構文でした。リストを順番に処理したいだけなら、`for` の方がすっきり書けます。

```lune
let answer =
    var total = 0
    for x in [1, 2, 3, 4]:
        total = total + x
    total
```

`[1, 2, 3, 4]` は `(1 2 3 4)` なので、`answer` は `10` です。

`for` は `List[T]` 専用の小さな構文です。`for x in items:` と書くと、リストの各要素が `x` に束縛され、body が実行されます。`for` 自体は `Unit` を返すので、上の例では `total` を最後に置いて答えにしています。

パターンも使えます。

```lune
let pairs = [(1, 10), (2, 20)]

let answer =
    var total = 0
    for (left, right) in pairs:
        total = total + left + right
    total
```

タプルの各要素が `left` と `right` に分かれて入ります。この例の `answer` は `33` です。

遅延評価との関係も見ておきましょう。

```lune
let answer =
    for _ in Nil:
        crash()
    42
```

空リストでは body が実行されないので、`crash()` は評価されません。`for` はリストの外側、つまり `Cons` か `Nil` かを一歩ずつ確かめながら進みます。要素の中身は、パターンや body で必要になったときに評価されます。

`for` は読みやすい集計や副作用的な処理に向いています。一方で、リストから別のリストを作るなら `map`、条件で絞るなら `filter`、値に畳み込むなら `fold` もよい選択です。

## 15. モジュールに分ける

少し大きくなったら、ファイルを分けられます。

`math.lune`:

```lune
module math

def add(x: Int, y: Int): Int =
    x + y
```

`main.lune`:

```lune
module main
import math

let answer = add(20, 22)
```

実行:

```sh
./bin/lune --eval answer main.lune
```

v0.1 では import したモジュールのトップレベル名が同じ環境に入ります。そのため `math.add` ではなく `add` と書きます。

## 16. 型チェックとツール

Lune には小さな型チェッカがあります。

```lune
let answer: Int = true
```

これは型エラーです。

```sh
./bin/lune --check bad.lune
```

エラーはコード位置つきで表示され、コード（`TYP0003` など）と修正ヒントが付きます。型チェッカはまだ完全ではありませんが、基本的なミスをかなり見つけてくれます。

Lune には、エラーを「見つける」だけでなく「教えて・直して・整える」ための小さなツールがそろっています。

### エラーを詳しく知る: `lune explain`

診断コードの意味・発生する最小例・直し方を読めます。

```sh
./bin/lune explain TYP0007
```

REPL では `:explain CODE` でも読めます。

### タイポを直す: did you mean と `lune fix`

未定義の名前が、近い名前に似ていると「did you mean」で候補を出します。

```text
error[TYP0001]: undefined name: totl
   = hint: did you mean `total`?
```

`lune fix` はこの候補を自動で当てます。

```sh
./bin/lune fix --write myfile.lune   # その場で修正
./bin/lune fix --check myfile.lune   # 修正候補があれば終了コード 1（CI 向け）
```

### 整形する: `lune fmt`

正準スタイルに整形します。整形しても意味は変わりません（再パースして確認します）。

```sh
./bin/lune fmt myfile.lune           # 整形結果を表示
./bin/lune fmt --write myfile.lune   # その場で整形
./bin/lune fmt --check myfile.lune   # 未整形なら終了コード 1（CI 向け）
```

## 17. エラーを読む、エラーから学ぶ

Lune では、エラーは「怒られ」ではなく教材です。この章では**わざとエラーを起こして**、診断を読み、`explain` で理解し、`fix` で直す、という一周を体験します。この流れが身につくと、初めて見るエラーも怖くなくなります。

### 診断の解剖学

まず、1 つの診断を部品に分解して読めるようになりましょう。次のファイルを `guide.lune` として保存して、`--check` してみます。

```lune
let count = 10
let total = cont + 5
```

```text
error[TYP0001]: undefined name: cont
  --> guide.lune:2:13
  |
2 | let total = cont + 5
  |             ^^^^ name is not defined
   = hint: did you mean `count`?
   = help: run `lune explain TYP0001` for a detailed explanation
```

上から順に:

- `error[TYP0001]` — 重大度（error / warning）と**診断コード**。コードはこの後の `explain` の索引になります。
- `--> guide.lune:2:13` — ファイル・行・列。
- 引用行と `^^^^` — 問題の場所そのもの。まずここを見ます。
- `= hint:` — 具体的な次の一手。ここでは正しい候補まで教えてくれています。
- `= help:` — もっと詳しく知りたいときの入口。

### 一周目: typo → 診断 → explain → fix

hint の意味をもっと知りたければ、コードを `explain` に渡します。

```sh
./bin/lune explain TYP0001
```

意味・発生する最小例・直し方、の 3 点セットが表示されます。`--lang ja` を付けると**日本語で**読めます（REPL では `:explain TYP0001 ja`）。さらに `./bin/lune --check --lang ja file.lune` のように付ければ、**診断メッセージそのもの**（メッセージ・caret の注・hint）も日本語になります（REPL では `:lang ja`）。全コードの詳解を一覧したいときは `documents/ERROR_INDEX_JA.md`（英語版は `ERROR_INDEX.md`）を開いてください。

このエラーは機械的に直せる種類なので、`fix` に任せられます。

```sh
./bin/lune fix --write guide.lune
./bin/lune --check guide.lune
```

```text
type check OK
```

これが基本の一周です: **起こす → 読む → explain → fix → 確認**。

### 二周目: 網羅性 — コンパイラが反例をくれる

次は typo より深い、設計に関わるエラーです。

```lune
type Color =
    | Red
    | Green
    | Blue

def name(c: Color): String =
    match c:
        | Red -> "red"
        | Green -> "green"
```

```text
error[TYP0007]: non-exhaustive match: missing case Blue
  --> guide.lune:7:5
  |
7 |     match c:
  |     ^^^^^ pattern Blue is not covered
   = hint: add a case for Blue, or a wildcard case `| _ -> ...`
   = help: run `lune explain TYP0007` for a detailed explanation
```

注目してほしいのは、「網羅的でない」と言うだけでなく、**どの値が漏れているか（`Blue`）を反例として教えてくれる**ことです。hint の通り `| Blue -> "blue"` を足せば直ります。

ここでワイルドカード `| _ -> ...` を選ぶこともできますが、安易に使うと「後で `Color` にコンストラクタを足したときに、コンパイラが漏れを教えてくれなくなる」という代償があります。実際、全ケースを書いた上に `_` を足すと、今度は警告が出ます。

```text
warning[TYP0009]: unreachable match case: _
   = hint: remove this case, or move it before the cases that cover it
```

エラー（TYP0007）と警告（TYP0009)は対になっていて、「漏れなく、無駄なく」に向かって両側から挟んでくれます。

### 三周目: 実行時エラーも教材

型チェックを通っても、実行時に失敗することはあります。

```lune
let x = 1 / 0
```

`--check` は通りますが、`--eval x` すると:

```text
error[RUN0006]: division by zero
   = hint: the right operand of `/` evaluated to 0
   = help: run `lune explain RUN0006` for a detailed explanation
```

実行時エラーも同じ文法（コード・hint・explain）で報告されます。REPL なら `:thunks x` で「失敗もメモ化される」ことまで観察できます（第 6 章）。

### 演習: エラーを出してみよう

普通の演習は「動くものを書く」ですが、ここでは逆をやります。**指定した診断をわざと出せたら正解**です。答え合わせは `lune explain CODE` と `documents/ERROR_INDEX.md` で。

1. `TYP0003`（type mismatch）を出してみよう。
2. `REC0002`（unknown record field）を、hint に「did you mean」が出る形で出してみよう。
3. `LAY0002`（unmatched closing delimiter）を出してみよう。
4. `TYP0008`（refutable pattern in let）を出してみよう。ヒント: `let Some(x) = ...`
5. `RUN0005`（recursive thunk evaluation）は REPL でしか出せません。なぜか考えてみよう。ヒント: `--check` が先に何を見つけますか?

エラーを自在に**出せる**ようになると、エラーを自在に**直せる**ようになります。

## 18. 小さなプログラムを書いてみよう

最後に、いくつかの機能をまとめた例です。

```lune
module tutorial

record User:
    name: String
    age: Int

type Greeting =
    | Greeting(text: String)

def adultLabel(user: User): String =
    if user.age >= 20 then "adult" else "young"

def greet(user: User): Greeting =
    Greeting("Hello, " + user.name + " (" + adultLabel(user) + ")")

def render(greeting: Greeting): String =
    match greeting:
        | Greeting(text) -> text

def birthdayMessage(user: User): String =
    var years = 0
    while years < 1:
        years = years + 1
    "next year: " + user.name

let ada = User(name = "Ada", age = 36)
let answer = render(greet(ada))
```

評価:

```sh
./bin/lune --eval answer tutorial.lune
```

結果:

```text
'Hello, Ada (adult)'
```

少し見えてきました。Lune は「データの形を型で表し、必要なものだけ評価し、`match` で読みやすく分解する」言語です。

`birthdayMessage` は少しわざとらしい例ですが、`while` も普通の block の中で使えることが分かります。リストを処理したい場面では、同じように `for` も block の中で使えます。

## 19. 練習問題

1. `record Book` を作り、`title: String` と `pages: Int` を持たせてください。
2. `isLong(book: Book): Bool` を作り、300 ページ以上なら `true` を返してください。
3. `type MaybeLong = LongBook(title: String) | ShortBook(title: String)` を作ってください。
4. `classify(book: Book): MaybeLong` を作り、`match` で表示用文字列に変換してください。
5. `Book(title = crash(), pages = 100)` から `pages` だけ読むとどうなるか試してください。
6. `while` を使って、`1` から `10` までの合計を計算してください。
7. `for` と `[1, 2, 3, 4, 5]` を使って、合計を計算してください。
8. REPL で上キーを使い、直前の式を少し編集して再実行してみてください。

最後の問題が、この言語らしいところです。使わないものは、まだ眠っています。

## 20. いまの制限

Lune v0.1 はまだ初期版です。

未対応の代表例:

- class / interface。
- 実 Java 呼び出し。
- record update。
- record pattern。
- mutable record field。
- `try` / `catch`。
- `break` / `continue`。
- LSP / package manager（整形は `lune fmt` として利用可能）。

一方で、以前は「未対応」だった機能のいくつかは、もう使えます: `for`、`T?`（null 安全）、`|>`、そして `lune explain` / `lune fmt` / `lune fix`。

でも、核になる感触はもうあります。

```lune
let add = fn x y -> x + y
let inc = add(1)
let answer = inc(41)
```

この小さな式に、Lune の方向性が詰まっています。

遅延して、必要になったら評価して、関数を値として渡し、データの形を型で表す。  
ここから少しずつ、言語を育てていきます。
