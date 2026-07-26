# 付録A 言語リファレンスマニュアル

本文と独立に引ける、Lune v0.1 の規範的な一覧です。ここは「そういえば規則はどうだった
か」を確かめる場所で、なぜそうなっているかは本文（と付録E）にあります。

規範の正は `documents/` の仕様書群です。この付録はそこから引いていますが、表の内容は
実装から機械的に取り出すか、実際に処理系に通して確かめています（末尾の「この付録の
出どころ」を参照）。

## A.1 字句

### キーワード

48 語が予約されています。**このうち多くは将来のためのもので、v0.1 では構文エラーに
なります**（A.6 を参照）。

```text
IO            abstract      as            catch         class         deepForce
def           elif          else          extends       false         final
finally       fn            for           force         if            implements
import        in            init          interface     internal      lazy
let           match         module        new           null          override
private       protected     public        raise         record        seq
static        strict        super         then          this          throw
throws        true          try           type          var           while
```

`break` / `continue` / `return` / `export` / `use` は**予約されていません**。ただの識別子
として扱われるので、書くと「未定義の名前」（`TYP0001`）になります。A.6 を参照。

### 識別子

```text
IDENT_START = [A-Za-z_]
IDENT_PART  = [A-Za-z0-9_]
IDENT       = IDENT_START IDENT_PART*
```

`_` 単独はワイルドカードパターン、`_name` は識別子です。

### リテラル

| 種類 | 例 | 型 |
| --- | --- | --- |
| 整数 | `42`、`1_000_000` | `Int`（任意精度） |
| 浮動小数 | `3.14`、`1e-3` | `Double` |
| 文字列 | `"hello"` | `String` |
| 文字 | `'x'` | `String`（下記） |
| 真偽値 | `true`、`false` | `Bool` |
| null | `null` | `Null` |
| ユニット | `()` | `Unit` |
| リスト | `[1, 2, 3]` | `List[T]` |
| タプル | `(1, "a")` | `Tuple[Int, String]` |

整数リテラルの `_` は桁区切りとして無視されます。文字列のエスケープは
`\n` `\r` `\t` `\\` `\"` `\'` `\0`。

> **文字リテラルと `Char` 型** — `'x'` は字句としては専用のトークンで、中身が1文字で
> なければ `LXL0002` になります。しかし**型は `String` です**。`Char` という型名は
> 型の一覧（A.4）にありますが、v0.1 ではこれを生む式がなく、`let c: Char = 'x'` は
> `TYP0003` になります。`Char` は将来のための予約と考えてください。

### コメント

```lune
# 行コメント

###
ブロックコメント（ネスト不可）
###
```

`//` は**コメントではありません** — 床除算の演算子です（2.2 節）。`/* ... */` も
コメントではありません。

### 演算子表

優先順位は高い順。同じ行は同じ優先順位です。

| 優先度 | 演算子 | 結合 |
| --- | --- | --- |
| 1 | `.` `?.` `()` `[]` | 左 |
| 2 | 単項 `!` 単項 `-` | 右 |
| 3 | `*` `/` `//` `%` | 左 |
| 4 | `+` `-` | 左 |
| 5 | `::` `++` | 右 |
| 6 | `==` `!=` `<` `<=` `>` `>=` | 非結合 |
| 7 | `&&` | 左 |
| 8 | `\|\|` | 左 |
| 9 | `??` | 右 |
| 10 | `\|>` | 左 |
| 11 | `=` `+=` `-=` `*=` `/=` `//=` `%=` | 右 |

**非結合**は連鎖できないという意味です。ただし止めるのはパーサではなく型検査で、
`1 < 2 < 3` は構文としては通り、`<` の左辺が `Bool` になったところで `TYP0003` に
なります（「`<`: 数値型が必要ですが、Bool が見つかりました」）。

`::` と `++` はパーサにはありますが、v0.1 の型検査・評価では実用対象外です。

## A.2 レイアウト規則

ブロックはインデントで表します。行頭に使えるのは**スペースだけ**で、タブが混じると
字句エラー `LXL0004`（インデントにタブは使えません）になります。caret はタブそのものを
指すので、どこに紛れ込んだかがすぐ分かります。

```text,diagnostic
error[LXL0004]: インデントにタブは使えません
  --> tabs.lune:2:3
  |
2 |   	1
  |   ^ インデントにはスペースを使う
   = hint: 行頭のタブをスペースに置き換えてください
```

ただし**空行とコメントのみの行はインデント判定の対象外**なので（下記の規則を参照）、
そこにタブがあっても叱られません。文字列の中や、コードより後ろのタブも対象外です。

字句解析のあと、レイアウト処理が `NEWLINE` / `INDENT` / `DEDENT` を生成します。

- 行頭の空白幅 `n` を、インデントスタックの先頭 `top` と比べる。
- `n == top` → `NEWLINE` だけを出す。
- `n > top` → `INDENT` を出し、`n` を push する。
- `n < top` → `n` と一致する値が出るまで `DEDENT` を出す。一致しなければインデント
  エラー（`LAY0001`）。
- ファイル終端では、スタックが空になるまで `DEDENT` を出してから `EOF`。

**括弧の中ではレイアウトトークンを作りません。** `(` `[` `{` で深さ +1、`)` `]` `}` で
-1 とし、深さが 0 より大きい間、物理改行はただの空白として扱われます。だから括弧の中は
自由に改行できます。

```lune
let xs = [
    1,
    2,
]
```

`:` の直後にブロックを期待する構文（`if` / `while` / `for` / `match` / `record` など）
では、次の有効トークンが `NEWLINE INDENT` でなければなりません。`=` の後は 1 行でも
ブロックでも書けます。

```lune
def f(): Int = 1

def g(): Int =
    1
```

REPL での複数行入力は、行末が `=` `:` `->` のいずれかなら継続に入り、空行で確定します
（付録D）。

## A.3 文法

以下では `NL` を 1 個以上の `NEWLINE` とします。完全な EBNF は
`documents/LEXER_PARSER_SPEC.md` の §5〜§10 にあり、ここはそこから引いた骨格です。

### ファイルと宣言

```ebnf
file        ::= NL* module_decl? import_decl* top_decl* EOF
module_decl ::= "module" qualified_name NL+
import_decl ::= "import" qualified_name ("as" IDENT)? NL+
qualified_name ::= IDENT ("." IDENT)*

top_decl    ::= function_decl | type_decl | record_decl | let_decl | var_decl

function_decl ::= "def" IDENT type_params? "(" params? ")" (":" type)? "=" body
let_decl      ::= ("strict" "let" | "let") pattern (":" type)? "=" body
var_decl      ::= "var" IDENT (":" type)? "=" body
type_decl     ::= "type" IDENT type_params? "=" NL INDENT constructor+ DEDENT
record_decl   ::= "record" IDENT type_params? ":" NL INDENT field+ DEDENT

constructor   ::= "|" IDENT ("(" ctor_fields? ")")? NL
ctor_fields   ::= ctor_field ("," ctor_field)*
ctor_field    ::= ("strict" | "!")? IDENT ":" type
field         ::= ("strict" | "!")? IDENT ":" type NL
params        ::= param ("," param)*
param         ::= ("strict" | "!")? IDENT ":" type
type_params   ::= "[" IDENT ("," IDENT)* "]"
body          ::= expr | NL INDENT block DEDENT
```

### 式

式は Pratt パーサで解析します。優先順位は A.1 の表のとおりです。

```ebnf
expr    ::= assign
assign  ::= pipeline (assign_op assign)?
primary ::= literal | IDENT | "(" expr ")" | list | tuple
          | if_expr | match_expr | lambda | block_expr
          | "lazy" expr | "force" expr | "deepForce" expr
          | "seq" expr expr | "while" expr ":" block | "for" pattern "in" expr ":" block
          | "IO" ":" block | "raise" expr

if_expr    ::= "if" expr ":" NL INDENT block DEDENT elif* else?
             | "if" expr "then" expr "else" expr
match_expr ::= "match" expr ":" NL INDENT match_case+ DEDENT
match_case ::= "|" pattern ("if" expr)? "->" body NL
lambda     ::= "fn" lambda_param* "->" body
list       ::= "[" (expr ("," expr)* ","?)? "]"
tuple      ::= "(" expr "," expr ("," expr)* ")"
```

`record` の構築は呼び出し構文の特別形で、**フィールド名が必須**です
（`User(name = "Ada", age = 36)`）。関数と ADT のコンストラクタは位置引数で呼びます
（名前付きにすると `TYP0012`）。

### パターン

```ebnf
pattern ::= "_"                       # ワイルドカード
          | "null"                    # null
          | IDENT                     # 名前束縛
          | literal                   # リテラル
          | "(" pattern ("," pattern)+ ")"      # タプル
          | IDENT "(" pattern ("," pattern)* ")" # コンストラクタ
          | pattern "|" pattern       # or パターン
          | pattern ":" type          # 型注釈付き
```

`let` のパターンは**反駁不能**でなければなりません。`let Some(x) = ...` は `TYP0008`
です（`match` を使う）。

## A.4 型

### 基本型

```text
Bool  Int  Double  String  Char  Unit  Any  Nothing  Null
```

`Int` は任意精度です。`Nothing` は値を持たない型（`crash()` の戻り値型）。
`Char` は型名としては存在しますが、v0.1 でこれを生む式はありません（A.1 の囲みを参照）。

### 複合型

```text
Option[Int]        Result[Int, String]     List[Int]
Lazy[Int]          IO[String]              Tuple[Int, String]
String?
```

`T?` は AST・型表現の上では `Nullable[T]` です。

### 関数型

カリー化表記が正規形で、`->` は**右結合**です。

```text
Int -> Int
Int -> Int -> Int
```

`(Int, Int) -> Int` は `Int -> Int -> Int` の糖衣として扱われます。タプル 1 個を受け取る
関数は `Tuple[Int, Int] -> Int` と書きます。

### null 安全

`null` と非 null の `T` はどちらも `T?` に渡せますが、**`null` を非 null の型に渡すことは
できず、`T?` を `T` が要る位置でそのまま使うこともできません**。アンラップの手段:

| 手段 | 書き方 |
| --- | --- |
| `match` の null パターン | `\| null -> …`。被覆後の名前は非 null に絞られる |
| null 合体 | `a ?? b`（`a` が null なら `b`。短絡する） |
| セーフナビゲーション | `x?.m`（null なら null に短絡。結果は nullable） |
| フロー・ナローイング | `if x != null:` の分岐で `x` が `T` になる |

ナローイングが働くのは単純な `if x != null` / `if x == null`（`x` は変数）だけです。
複合条件（`&&` など）、`elif`、`while` でのナローイングと、`!!` 断言演算子はまだ
ありません。

### 局所型推論

`def` の引数には型注釈が必要です。戻り値型は省略できます（ただし**再帰関数には必須**
— `TYP0011`）。

未注釈のラムダ引数は文脈から型を受け取ります。文脈になるのは `let` / `var` の型注釈、
`def` の戻り値注釈、関数呼び出しの引数位置です。

```lune
let inc: Int -> Int = fn x -> x + 1          # x : Int
let doubled = map([1, 2, 3], fn x -> x * 2)  # x : Int
```

文脈がないと `Any` に落ち、警告 `TYP0010` が出ます。

## A.5 評価

Lune は**デフォルト遅延**です。

### 遅延されるもの

- 通常の `let` の右辺
- 通常の関数引数
- 通常のコンストラクタフィールド
- 通常の record フィールド
- `lazy expr` の body

### 評価が起きる境界

- 変数参照
- `force` / `deepForce`
- `seq` の第 1 引数
- 条件式（`if`）の条件、`while` の条件
- 二項演算に必要な引数
- `match` の scrutinee の外側コンストラクタ
- リテラルパターンの比較
- 正格引数（`!x: Int` / `strict x: Int`）
- `strict let`（`!let` も同じ）
- 正格コンストラクタフィールド、正格 record フィールド

### メモ化

サンクは**成功も失敗もメモ化されます**。一度失敗したサンクを再び force すると、同じ
エラーが再び出ます（計算はやり直しません）。

**再入評価は実行時エラー**です（`RUN0005`）。`let x = x + 1` のように自分の結果に
依存する値は、force した瞬間に自分に戻ってくるので、待たずにその場で報告されます
（第4章 4.7）。

`let x = x + 1` を `--check` すると、報告されるのは `TYP0001`（未定義の名前 `x`）です。
右辺の `x` は、その `let` がまだ環境に入る前に解決されるからです。`RUN0005` が出るのは
`--eval` で実際に force したときで、同じコードが検査段階と実行段階で別の診断を出す例に
なっています。

観察の道具は `:thunks`（評価せずに状態を見る）と `:trace` / `--trace`（force の実況）
です。第4章と付録B・D。

## A.6 v0.1 で未対応のもの

キーワードとして予約されているのに、まだ動かないものがあります。**何が返ってくるかを
併記しました** — 診断コードから引けるようにするためです。

| 書いたもの | 出る診断 |
| --- | --- |
| `class` | `PRS0001` 予期しないトークン（CLASS） |
| `interface` | `PRS0001` 予期しないトークン（INTERFACE） |
| `new Foo()` | `TYP0003` サポートされていない式（NewExpr） |
| `this` / `super` | `TYP0003` サポートされていない式（ThisExpr） |
| `try` / `catch` / `finally` | `PRS0001` 式が必要（TRY） |
| record update `r { x = 2 }` | `PRS0001`（LBRACE） |
| record pattern `R { x }` | `PRS0002` ARROW が必要（LBRACE） |
| mutable record field `var x: Int` | `PRS0002` IDENT が必要（VAR） |
| annotation `@inline` | `PRS0001`（AT） |
| `throws` | `PRS0002` ASSIGN が必要（THROWS） |
| `import a.b.{C, D}` | `PRS0002` IDENT が必要（LBRACE） |
| ADT のフィールドアクセス `c.v` | `TYP0003` サポートされていないメンバアクセス |

**予約すらされていないもの** — `break` / `continue` / `return` / `export` / `use` は
キーワードではないので、ただの識別子と見なされ `TYP0001`（未定義の名前）になります。
ループを途中で抜けたいときは条件をループ条件に織り込みます（第9章 9.3）。

言語の外側で未対応なもの: JVM バイトコード生成、実 Java ライブラリ呼び出し、
`Stream` / `Map` / `Set` / `Promise` / `Iterator`、パッケージマネージャ、LSP。

将来こうしたい、という話は `documents/LANGUAGE_FUTURE_SPEC.md` にあります。なぜ
v0.1 をこの範囲で切ったのかは付録E。

## この付録の出どころ

| 節 | 出どころ |
| --- | --- |
| A.1 キーワード | `lune/tokens.py` の `KEYWORDS` から生成（48 語） |
| A.1 演算子表 | `documents/SYNTAX_SPEC.md` 14 節。中置部分は `lune/parser.py` の `INFIX` と照合済み |
| A.1 リテラル | 各リテラルを REPL に通して型を確認 |
| A.2 レイアウト | `documents/LEXER_PARSER_SPEC.md` §3 |
| A.3 文法 | 同 §5〜§10 の EBNF から骨格を抜粋 |
| A.4 型 | `documents/LANGUAGE_SPEC.md` §6・§8 |
| A.5 評価 | 同 §17 |
| A.6 未対応 | 同 §21。**各項目を実際に `--check` に通し、出る診断を記録した** |

書きながら仕様書と実装が食い違っている箇所を2つ見つけました。うち `LXL0004`
（タブのインデント）は**実装側を直しました** — 診断は用意されていたのに、インデント幅を
先頭スペースだけで数えていたため一度も出せない状態でした。

もう1つは残っています。`LANGUAGE_SPEC.md` §5 は文字リテラルの型を `Char` としていますが、
実際は `String` です（A.1 の囲み）。文字リテラルを `Char` にするか `Char` を仕様から
降ろすかは設計判断なので、この付録は実装の側に合わせてあります。
