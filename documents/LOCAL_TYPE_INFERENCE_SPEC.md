# ローカル型推論仕様

Version: 0.1 draft  
Implementation target: `lune_v0_1` Python prototype (`lune/typechecker.py`)  
Related: `TYPE_CHECKER_SPEC.md`, `FUNCTION_TYPE_SPEC.md`, `ERROR_DIAGNOSTICS_SPEC.md`, `LANGUAGE_FUTURE_SPEC.md` §3

この文書は、期待型伝播 (bidirectional checking) によるローカル型推論と、`Any` への暗黙フォールバックの解消を定義する。

## 1. 目的

現状の v0.1 typechecker は合成 (synthesis) のみの検査器であり、未注釈ラムダ引数が `Any` になる。`Any` は任意の型に代入可能なため、次の問題が起きる。

- `let f: Int -> Int = fn x -> x + 1` でも body は `x: Any` で検査され、body 内の型誤りを見逃す。
- `map(numbers, fn x -> x * 2)` は型変数 `U` が `Any` に汚染され、結果が `List[Any]` になる。以降の検査がすべて素通りする。
- ラムダ引数の `Any` フォールバックが暗黙で、利用者に見えない。

達成目標:

- 注釈・呼び出し文脈から得られる期待型をラムダ・リスト・分岐へ伝播し、実型で検査する。
- 高階関数呼び出しで型変数が正しく解決される (`map(xs, fn x -> x * 2)` が `List[Int]` になる)。
- 文脈がなく `Any` へフォールバックした場合に warning を報告する。
- 戻り値注釈のない再帰関数へ actionable な診断を出す。

## 2. 用語

- **合成モード (synthesis)**: 式から型を導く。従来の `infer_expr`。
- **検査モード (checking)**: 期待型を与えて式を検査する。期待型は式形式に応じて内側へ分配される。
- **期待型 (expected type)**: 注釈または呼び出しシグネチャ由来の型。
- **Any フォールバック**: 文脈から型が決まらず `Any` を採用すること。

## 3. 現状 (この仕様の実装前)

| 箇所 | 現状 |
| --- | --- |
| `def` 引数 | 注釈必須 (`TYP0003` 系エラー)。変更しない |
| `def` 戻り値 | 省略時は body から推論。ただし predeclare されず再帰・前方参照が不可 (`TYP0001` undefined name) |
| ラムダ引数 | 未注釈は無条件で `Any`。文脈からの伝播なし |
| `let` / `var` 注釈 | 値を合成推論後に代入可能性検査のみ。期待型は値式へ伝播しない |
| 空リスト `[]` | `List[Any]` |
| call 引数 | 左から逐次 unify。ラムダは `Any` 引数のまま unify され型変数を汚染する |

## 4. 期待型の供給源

検査モードは次の位置で開始される。

1. `let` / `var` の型注釈 → 右辺式。
2. `def` の戻り値注釈 → body 式。
3. 関数・コンストラクタ呼び出しの引数位置 → 対応するパラメータ型 (§6 の 2 パス方式)。
4. record construction の named field → フィールド型。
5. 型注釈付きリスト・コンストラクタフィールド経由で決まったリスト要素型 → 各要素式。

## 5. 検査モードの分配規則

`check_expr(expr, expected, env)` は式形式ごとに期待型を分配する。以下に該当しない式形式は、合成モードで推論して従来の代入可能性検査を行う (`require_value_assignable`)。

### 5.1 ラムダ

期待型が関数型のとき (`flatten_function_type` 後):

- 期待パラメータ数 ≧ ラムダ引数数であること。不足時は従来エラー。余剰の期待パラメータはカリー化として戻り値側に残す。
- 未注釈引数は対応する期待パラメータ型を採用する。
- 注釈付き引数は注釈を採用し、期待パラメータ型との代入可能性を検査する。
- body は残りの期待戻り値型で検査モード検査する。
- ラムダ全体の型は期待型で確定する。

```lune
let inc: Int -> Int = fn x -> x + 1      # x は Int で検査される
let bad: Int -> Int = fn x -> x && true  # 型エラーになる (従来は素通り)
```

期待型が関数型でない場合 (`Any` 含む) は合成モードへフォールバックする。

### 5.2 リストリテラル

期待型が `List[T]` のとき、各要素を `T` で検査する。空リストは `List[T]` になる。

```lune
let xs: List[Int] = []            # List[Int]
let ys: List[Int -> Int] = [fn x -> x + 1]
```

### 5.3 if / match

期待型 `T` を各分岐 (then / elif / else、各 case body) へ分配する。分岐型の合流検査は従来どおり行う。

### 5.4 block / let-in / lazy / IO

- `BlockExpr`: 期待型を result 式へ分配する。文は従来どおり検査する。
- `LazyExpr` ← `Lazy[T]`: body を `T` で検査する。
- `IOBlockExpr` ← `IO[T]`: body を `T` で検査する。v0.1 の IO は通常 block 評価に近いため、分配のみ行う。

### 5.5 タプル

期待型が `Tuple[T1, ..., Tn]` で要素数が一致するとき、各要素へ分配する。

## 6. 呼び出し引数の 2 パス検査

`infer_call` を次の 2 パスに変更する。部分適用・可変長引数の規則は従来を維持する。

- **パス 1**: ラムダ以外の引数を合成推論し、対応パラメータ型と unify して置換を蓄積する。
- **パス 2**: ラムダ引数を、置換適用後のパラメータ型で検査モード検査する。検査結果を再度 unify し、未解決の型変数 (ラムダの戻り値由来など) を解決する。

```lune
let numbers = [1, 2, 3]
let doubled = map(numbers, fn x -> x * 2)
# パス1: List[T] ~ List[Int] → T = Int
# パス2: fn x -> x * 2 を Int -> U で検査 → x: Int、U = Int
# doubled : List[Int]
```

record construction の named field も同じ方式で、ラムダ値のフィールドを後に検査する。

引数の評価順は型検査上のみの並べ替えであり、実行時セマンティクス (遅延評価) には影響しない。

## 7. def 戻り値推論と再帰

- 戻り値注釈がある場合: 従来どおり predeclare され、再帰・前方参照が可能。body は戻り値注釈で検査モード検査する。
- 戻り値注釈がない場合: 従来どおり body から合成推論する。body 内に自分自身への参照がある場合、`TYP0001` (undefined name) の代わりに `TYP0011` を報告する。

```text
error[TYP0011]: recursive function requires a return type annotation: fact
  --> sample.lune:2:5
   = hint: add a return type, e.g. `def fact(n: Int): Int = ...`
```

判定は「`def` body の検査中に未定義名がその `def` 自身の名前と一致した」ことで行う。相互再帰は対象外 (従来どおり `TYP0001`) とする。

## 8. Any フォールバック warning

検査モード・合成モードのいずれでも期待型が得られず、ラムダ引数が `Any` になった場合、warning `TYP0010` を報告する。

```text
warning[TYP0010]: cannot infer type of parameter x
  --> sample.lune:1:14
  |
1 | let f = fn x -> x
  |            ^ parameter type falls back to Any
   = hint: add a type annotation, e.g. `fn x: Int -> ...`
```

warning は TYP0009 と同じ収集基盤 (`TypeEnv.warnings`) を使う。型は従来どおり `Any` として続行する。

## 9. 診断一覧

| code | source | 意味 | severity |
| --- | --- | --- | --- |
| `TYP0010` | typechecker | lambda parameter type falls back to Any | warning |
| `TYP0011` | typechecker | recursive function requires return type annotation | error |

## 10. 対象外 (将来仕様)

- body 制約からの単一化推論 (`fn x -> x + 1` 単独で `Int -> Int` と推論すること)。
- let 多相 (ジェネリックなラムダ束縛)。
- `|>` パイプライン経由の期待型伝播 (runtime 未対応のため)。
- `def` 引数注釈の省略。
- Java 型解決による外部 import の `Any` 解消。

## 11. 実装ガイド

変更は `lune/typechecker.py` に閉じる想定である。

1. `check_expr(expr, expected: ValueType, env) -> ValueType` を追加する。§5 の式形式のみ期待型を消費し、他は `infer_expr` + `require_value_assignable` に委譲する。
2. `check_decl` の `LetDecl` / `VarDecl`: 注釈がある場合 `infer_expr` の代わりに `check_expr` を使う。
3. `check_function_decl`: 戻り値注釈がある場合 body を `check_expr` で検査する。§7 の TYP0011 は body 検査を try で包み、`TYP0001` かつ名前一致のとき変換する。
4. `infer_call` / `infer_record_constructor_call`: §6 の 2 パス化。「ラムダ引数」の判定は AST が `ast.LambdaExpr` であること (paren 化された `(fn ...)` を含む)。
5. `LambdaExpr` の合成推論 (文脈なし): 従来どおり `Any` フォールバックし、`TYP0010` を報告する。
6. 検査モードのラムダは戻り型を期待型で確定させ、型変数を含む場合は呼び出し側の置換で解決する。

## 12. 互換性

- ラムダ body が実型で検査されるため、従来 `Any` で素通りしていた誤りがエラーになる (意図した厳格化)。
- `map` 等の結果型が `List[Any]` から実型に変わるため、下流の検査が新たに誤りを検出しうる。
- `TYP0010` は warning のため既存コードはコンパイル可能なまま。samples / tests を監査し、warning が出る箇所は注釈を追加するか文脈を与える。

## 13. テスト計画

`tests/test_typechecker.py` に追加する。

検査モード (通過し、型が実型になるもの):

- `let f: Int -> Int = fn x -> x + 1` → `f : Int -> Int`、body は Int 検査。
- `let f: (Int, Int) -> Int = fn x y -> x + y`。
- `map([1,2,3], fn x -> x * 2)` → `List[Int]`。
- `filter([1,2,3], fn x -> x % 2 == 0)` → `List[Int]`。
- `fold([1,2,3], 0, fn acc x -> acc + x)` → `Int`。
- `let xs: List[Int] = []` → `List[Int]`。
- `let f: Int -> Int = if cond then (fn x -> x) else (fn x -> x + 1)`(分岐分配)。
- 注釈付き引数と期待型の整合 (`let f: Int -> Int = fn x: Int -> x`)。
- 戻り値注釈付き def の body 内ラムダへの伝播。

エラー (新たに検出されるもの):

- `let f: Int -> Int = fn x -> x && true` → TYP0003。
- `map([1,2,3], fn x -> x && true)` → TYP0003。
- `let xs: List[Int] = [1, true]` → TYP0003。
- `let f: Int -> Int = fn x y -> x` (引数過剰) → TYP0005 相当。

TYP0010 / TYP0011:

- `let f = fn x -> x` → TYP0010 warning。
- 文脈のある `map(xs, fn x -> x)` → warning なし。
- 戻り値注釈のない再帰 def → TYP0011。
- 戻り値注釈付き再帰 def → エラーなし。

回帰:

- 既存全テストが通ること。samples の `--check` が warning なしで通ること (必要なら samples に注釈を追加)。

## 14. 文書更新

- `TYPE_CHECKER_SPEC.md`: 検査モードの節を追加し、§13 (Any) の「未注釈ラムダ引数」を更新する。
- `LANGUAGE_SPEC.md`: §8.3 (ラムダ)、§16 (型チェッカ) を更新する。
- `ERROR_DIAGNOSTICS_SPEC.md`: TYP0010 / TYP0011 をコード表へ追加する。
- `README.md`: implemented リストに追記する。
