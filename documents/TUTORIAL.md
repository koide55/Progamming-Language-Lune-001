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

このチュートリアルでは、Lune の「書いていて楽しいところ」を、実際に動くコードで順番に見ていきます。

## 1. はじめの一歩

作業ディレクトリ:

```sh
cd lune_v0_1
```

式や宣言を試すなら REPL が便利です。

```sh
PYTHONPATH=. python3 -m lune.cli --repl
```

端末で起動した REPL は、Bash のコマンドラインのように行編集できます。

- 左右キーでカーソル移動。
- 上下キーで履歴をたどる。
- Backspace / Delete で編集。
- `Ctrl-A` で行頭、`Ctrl-E` で行末へ移動。

履歴は可能なら `~/.lune_history` に保存されます。少し前に試した式を上キーで呼び戻せるので、試行錯誤がぐっと楽になります。

ファイルを評価する場合:

```sh
PYTHONPATH=. python3 -m lune.cli --eval answer samples/records.lune
```

型チェックだけしたい場合:

```sh
PYTHONPATH=. python3 -m lune.cli --check samples/records.lune
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
PYTHONPATH=. python3 -m lune.cli --eval answer your_file.lune
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

この「必要になるまで待つ」と「一度計算したら覚える」の組み合わせが、Lune の遅延評価の核です。

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

`add(1)` は、「あと 1 つ引数を受け取ったら足し算する関数」を返します。

つまり、こういう小さな道具を簡単に作れます。

```lune
let double = fn x -> x * 2
let add10 = fn x -> x + 10

let answer = add10(double(16))
```

将来的には、このあたりを `|>` と組み合わせて、もっと気持ちよく書けるようにしていく余地があります。

## 8. ADT で「形」を作る

Lune は代数的データ型を持っています。

```lune
type Option[T] =
    | Some(value: T)
    | None
```

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

ADT と `match` は、Lune の関数型らしさがよく出る部分です。

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

## 11. 標準ライブラリの小さな道具

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
PYTHONPATH=. python3 -m lune.cli --check samples/list_tools.lune
PYTHONPATH=. python3 -m lune.cli --eval doubled samples/list_tools.lune
PYTHONPATH=. python3 -m lune.cli --eval adultNames samples/list_tools.lune
```

`Option` も組み込み済みです。

```lune
let value = Some(42)
let answer = getOrElse(value, 0)
```

標準ライブラリはまだ小さいですが、「毎回自分で `Option` や `List` を定義しなくてよい」だけでも、試し書きがずいぶん楽になります。

## 12. `while` で小さなループを書く

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

## 13. `for` でリストを歩く

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

## 14. モジュールに分ける

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
PYTHONPATH=. python3 -m lune.cli --eval answer main.lune
```

v0.1 では import したモジュールのトップレベル名が同じ環境に入ります。そのため `math.add` ではなく `add` と書きます。

## 15. 型チェックしてみる

Lune には小さな型チェッカがあります。

```lune
let answer: Int = true
```

これは型エラーです。

```sh
PYTHONPATH=. python3 -m lune.cli --check bad.lune
```

エラーはコード位置つきで表示されます。

型チェッカはまだ完全ではありませんが、基本的なミスをかなり見つけてくれます。

## 16. 小さなプログラムを書いてみよう

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
PYTHONPATH=. python3 -m lune.cli --eval answer tutorial.lune
```

結果:

```text
'Hello, Ada (adult)'
```

少し見えてきました。Lune は「データの形を型で表し、必要なものだけ評価し、`match` で読みやすく分解する」言語です。

`birthdayMessage` は少しわざとらしい例ですが、`while` も普通の block の中で使えることが分かります。リストを処理したい場面では、同じように `for` も block の中で使えます。

## 17. 練習問題

1. `record Book` を作り、`title: String` と `pages: Int` を持たせてください。
2. `isLong(book: Book): Bool` を作り、300 ページ以上なら `true` を返してください。
3. `type MaybeLong = LongBook(title: String) | ShortBook(title: String)` を作ってください。
4. `classify(book: Book): MaybeLong` を作り、`match` で表示用文字列に変換してください。
5. `Book(title = crash(), pages = 100)` から `pages` だけ読むとどうなるか試してください。
6. `while` を使って、`1` から `10` までの合計を計算してください。
7. `for` と `[1, 2, 3, 4, 5]` を使って、合計を計算してください。
8. REPL で上キーを使い、直前の式を少し編集して再実行してみてください。

最後の問題が、この言語らしいところです。使わないものは、まだ眠っています。

## 18. いまの制限

Lune v0.1 はまだ初期版です。

未対応の代表例:

- class / interface。
- 実 Java 呼び出し。
- record update。
- record pattern。
- mutable record field。
- `try` / `catch`。
- `for`。
- `break` / `continue`。
- LSP / formatter / package manager。

でも、核になる感触はもうあります。

```lune
let add = fn x y -> x + y
let inc = add(1)
let answer = inc(41)
```

この小さな式に、Lune の方向性が詰まっています。

遅延して、必要になったら評価して、関数を値として渡し、データの形を型で表す。  
ここから少しずつ、言語を育てていきます。
