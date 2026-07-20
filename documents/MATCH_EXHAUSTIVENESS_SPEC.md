# Match 網羅性チェック仕様

Version: 0.1 draft  
Implementation target: `lune_v0_1` Python prototype (`lune/typechecker.py`)  
Related: `TYPE_CHECKER_SPEC.md`, `ERROR_DIAGNOSTICS_SPEC.md`, `LANGUAGE_SPEC.md` §11

この文書は、`match` 式の網羅性チェックと、`let` / `for` パターン束縛の反駁可能性チェックの実装仕様を定義する。

## 1. 目的

現状の v0.1 では、`match` のケース漏れと `let Some(x) = ...` の照合失敗はすべて実行時エラーになる。ADT + `match` を中核とする言語として、これらを型チェック時に静的検出する。

達成目標:

- ケース漏れのある `match` を型チェック時にエラーとして報告する。
- 欠落しているパターンの具体例 (witness) をエラーメッセージに含める。
- 実行時に失敗しうるパターン (反駁可能パターン) の `let` / `for` での使用をエラーとして報告する。
- 先行ケースに完全に覆われた到達不能ケースを warning として報告する (Phase 2、実装済み)。

## 2. 用語

- **網羅的 (exhaustive)**: scrutinee 型のあらゆる値が、いずれかのケースに必ず照合されること。
- **有用 (useful)**: パターン `q` が、先行するパターン行列 `P` に照合されない値を少なくとも 1 つ照合できること。
- **witness**: `match` に照合されない値を表すパターン例。例: `Some(None)`。
- **反駁可能 (refutable)**: 照合に失敗する値が存在するパターン。例: `Some(x)` (scrutinee 型が `Option[T]` のとき)。
- **反駁不能 (irrefutable)**: あらゆる値に照合するパターン。例: `_`、名前、単一コンストラクタ ADT のコンストラクタパターン、要素がすべて反駁不能なタプルパターン。

## 3. 対象と非対象

対象:

- すべての `match` 式 (typechecker が `ast.MatchExpr` を検査する箇所)。
- `let` のパターン束縛 (`bind_pattern_types` を通る `ast.LetDecl`)。
- `for pattern in xs:` のループパターン。

非対象 (v0.1 では検査しない):

- 実行時のみ評価されるコード経路の網羅性 (型チェックを通過した AST のみが対象)。
- guard 式の意味解析。guard 付きケースは網羅性に **寄与しない** ものとして保守的に扱う。

`Nullable[T]` (`T?`) は網羅性検査の対象である。詳細は「§4 型ドメイン」を参照。

## 4. 型ドメイン

scrutinee 型ごとに「完全なコンストラクタ集合 Σ」を次のように定める。

| scrutinee 型 | Σ (完全集合) | 備考 |
| --- | --- | --- |
| ユーザー定義/標準 ADT (`TypeEnv.types` に登録があり `constructors` が非空) | 宣言された全コンストラクタ | `Option` → `{Some, None}` |
| `Bool` | `{true, false}` | リテラルパターンで網羅できる唯一の基本型 |
| `Tuple[T1, ..., Tn]` | 単一の n 要素タプル | 要素ごとに再帰的に検査 |
| `Unit` | 開いた型 | `()` リテラルパターンは現行構文に存在しないため、ワイルドカードのみが網羅する |
| `Int` `Double` `String` `Char` | 無限 (開いた型) | ワイルドカード/名前パターンのみが網羅する |
| `Nullable[T]` (`T?`) | `null` と 内部型 `T` の完全集合 | 下記の分割検査で扱う |
| `Any`、型変数、`Lazy[T]`、関数型、record 型、`Nothing` | 開いた型 | 同上 |

開いた型に対するリテラルパターンやコンストラクタパターンは、何個並べても網羅とはみなさない。

record 型は record パターン未実装 (`RECORD_FIELD_SPEC.md`) のため開いた型として扱う。record パターン導入時に本仕様を拡張する。

`Nullable[T]` の網羅性は「null 被覆」と「内部型 `T` の網羅」に分割して検査する。`null` パターンは null のみに、それ以外のパターン（名前・ワイルドカード・内部値パターン）は非 null の内部値にマッチする（`null` を被覆した後の名前束縛は非 null `T` にナローイングされる）。`null` の被覆が無ければ欠落パターン `null` として `TYP0007`、内部 `T` が網羅されていなければ内部の欠落パターンとして `TYP0007` になる。内部の網羅判定には ADT/`Bool` 等と同じ有用性アルゴリズムを再利用する。

## 5. パターンの正規化

網羅性判定の前に、各ケースのパターンを次の規則で正規化する。

1. `TypedPattern` は内側のパターンに置き換える (型の整合は既存の `bind_pattern_types` が検査済み)。
2. `OrPattern` は複数の行に展開する。`| A | B -> e` は `A -> e` と `B -> e` の 2 行になる。ネストした OR も再帰的に展開する。
3. `NamePattern` と `WildcardPattern` はワイルドカード `_` として扱う。
4. guard 付きケースは行列に **加えない**。guard が `false` になりうるため、そのケースは値を照合する保証がない。
5. `LiteralPattern` はリテラル値ごとの擬似コンストラクタ (アリティ 0) として扱う。
6. タプルパターンは、要素数 n の単一擬似コンストラクタ (アリティ n) として扱う。

正規化の結果、パターンは「ワイルドカード」または「コンストラクタ + 部分パターン列」の 2 形に還元される。

## 6. アルゴリズム

Maranget の usefulness アルゴリズムの簡約版を用いる。パターン行列 `P` (各行はパターンのベクトル) とパターンベクトル `q` に対し、`U(P, q)` を「`q` が `P` に対して有用か」と定義する。

網羅性判定: `match` の全ケースを正規化した行列を `P` とするとき、`U(P, [_])` が真なら非網羅である。このとき `U` が構築する witness をエラーに使う。

補助定義:

- `S(c, P)`: コンストラクタ `c` (アリティ a) による特殊化。先頭が `c(p1..pa)` の行は `p1..pa + 残り` に置換、先頭が `_` の行は `_ * a + 残り` に置換、他のコンストラクタで始まる行は削除する。
- `D(P)`: デフォルト行列。先頭が `_` の行のみ残し、先頭要素を落とす。

擬似コード:

```python
def useful(P, q, types) -> Witness | None:
    if not P:                       # 行がない: q は有用
        return witness_from(q)
    if not q:                       # 幅 0: P に行がある → 有用でない
        return None
    head, rest = q[0], q[1:]
    if is_constructor(head):
        c = constructor_of(head)
        return useful(S(c, P), sub_patterns(head) + rest, types)
    # head はワイルドカード
    sigma = head_constructors(P)    # P の先頭列に現れるコンストラクタ集合
    if is_complete_signature(sigma, column_type, types):
        for c in sigma:
            w = useful(S(c, P), wildcards(arity(c)) + rest, types)
            if w is not None:
                return wrap(c, w)   # witness を c(...) で包む
        return None
    # 不完全: Σ に現れないコンストラクタが witness になる
    w = useful(D(P), rest, types)
    if w is not None:
        return prepend(missing_constructor(sigma, column_type, types), w)
    return None
```

`is_complete_signature` は §4 の表に従う。開いた型では常に偽 (ただし `sigma` が空でなくても偽) とする。

witness の表示規則:

- コンストラクタ: `Some(_)` のように、部分に情報がなければ `_` を使う。
- ネスト: 再帰的に構築する。例: `Cons(_, Cons(_, _))`。
- 開いた型の欠落: `_` と表示する。
- 複数の欠落がある場合は最初に発見した 1 つを表示すればよい。

計算量はパターン数と ADT サイズに対して指数的になりうるが、v0.1 の規模では問題としない。再帰深さの上限は設けない。

## 7. let / for パターンの反駁可能性

`irrefutable(pattern, type, env)` を次のように定義する。

- `WildcardPattern`、`NamePattern`: 反駁不能。
- `TypedPattern`: 内側で判定。
- `TuplePattern`: 全要素が反駁不能なら反駁不能。
- `ConstructorPattern`: パターンのコンストラクタが属す ADT のコンストラクタが **ちょうど 1 個** であり、かつ全フィールドパターンが反駁不能なら反駁不能。
- `LiteralPattern`: scrutinee 型が `Unit` の `()` のみ反駁不能。それ以外は反駁可能。
- `OrPattern`: いずれかの枝が反駁不能なら反駁不能。そうでなければ、展開した枝の集合が §6 のアルゴリズムで網羅的なら反駁不能。

`let` 宣言・`let-in` 式・`for` のパターンが反駁可能な場合は型エラーとする。

これは **破壊的変更** である。`LANGUAGE_SPEC.md` §7.4 の「パターンが合わない場合は実行時エラーになる」挙動を廃止し、`match` の使用を要求する。単一コンストラクタの分解 (`let Pair(l, r) = p`、`let (x, y) = t`) は引き続き利用できる。

## 8. 診断

新規コード (`ERROR_DIAGNOSTICS_SPEC.md` のコード表に追加する):

| code | source | 意味 | severity |
| --- | --- | --- | --- |
| `TYP0007` | typechecker | non-exhaustive match | error |
| `TYP0008` | typechecker | refutable pattern in let/for binding | error |
| `TYP0009` | typechecker | unreachable match case | warning |

表示例 (非網羅 match):

```text
error[TYP0007]: non-exhaustive match: missing case None
  --> sample.lune:4:5
  |
4 |     match value:
  |     ^^^^^ pattern None is not covered
   = hint: add a case for None, or a wildcard case `| _ -> ...`
```

- primary span は `MatchExpr.span` を使う。
- message は `non-exhaustive match: missing case <witness>` とする。
- guard のみでカバーされているケースが原因の場合、hint に `guarded cases do not count toward exhaustiveness` を追加する。

表示例 (反駁可能 let):

```text
error[TYP0008]: refutable pattern in let binding: Some(value)
  --> sample.lune:1:5
  |
1 | let Some(value) = compute()
  |     ^^^^^^^^^^^ this pattern can fail to match
   = hint: use `match` to handle all cases of Option
```

## 9. 実装ガイド

変更はすべて `lune/typechecker.py` に閉じる想定である。

1. `TypeEnv` に `lookup_type(name) -> TypeInfo | None` を追加する (現状 `types` dict はあるが親を辿る lookup がない)。
2. 新モジュール関数群を追加する: パターン正規化、`useful`、witness 構築、`irrefutable`。既存の `bind_pattern_types` は変更しない (型検査と束縛は従来どおり先に行う)。
3. `infer_expr` の `ast.MatchExpr` 分岐 (現行 422–431 行付近) の末尾で、全ケースの型検査後に網羅性を判定し、非網羅なら `LuneTypeError(..., "TYP0007", expr.span, ...)` を送出する。
4. `check_decl` の `ast.LetDecl` 分岐 (現行 299 行付近)、`let-in`、`ast.ForExpr` 分岐で `irrefutable` を判定し、偽なら `TYP0008` を送出する。
5. scrutinee 型が `Any` または型変数の場合は網羅性チェックをスキップする (常に網羅とみなす)。`Any` は v0.1 の逃げ道であるという既存方針に従う。
6. evaluator の照合失敗時の実行時エラーは defense-in-depth として残す。

Phase 2 (実装済み):

- 到達不能ケース検出: ケース i のパターン (OR 展開後の全行) が、先行する guard なしケースの行列 `P[0..i-1]` に対して有用でなければ `TYP0009` を warning として報告する。guard 付きケースも検査対象になるが、行列には追加されない。
- warning 収集: `TypeEnv` が root に `warnings: list[Diagnostic]` を持ち、`report_warning` で親を辿って追加する。warning は型チェックを中断しない。CLI の `--check` は完了後に stderr へまとめて表示し、REPL は入力ごとに表示する。

## 10. 既存コード・文書への影響

- `samples/*.lune` と `tests/` を監査し、非網羅 match と反駁可能 let を修正する (`samples/option.lune` の `let Some(value) = ...` 系は `match` へ書き換え)。
- prelude (`lune/evaluator.py` / typechecker 内の標準ライブラリ定義) に Lune ソースで書かれた match があれば同様に監査する。
- `LANGUAGE_SPEC.md`: §7.4 (パターン束縛)、§11 (網羅性チェックは未実装、の記述)、§16 (制限)、§21 を更新する。
- `TYPE_CHECKER_SPEC.md`: 検査対象に網羅性を追加する。
- `ERROR_DIAGNOSTICS_SPEC.md`: コード表に TYP0007–TYP0009 を追加する。
- `TUTORIAL.md` / `TUTORIAL_EN.md`: 反駁可能 let の例があれば書き換える。

## 11. テスト計画

`tests/test_typechecker.py` に追加する。

網羅 (通過すべきもの):

- `Option[Int]` に対する `Some(x)` + `None`。
- `Some(x)` + `_`。
- `Bool` に対する `true` + `false`。
- guard 付き `Some(x) if ...` + guard なし `Some(x)` + `None`。
- OR パターン `| Some(x) | None -> ...` (束縛変数なしの形)。
- タプル `(Bool, Bool)` に対する 4 ケース、および `(_, _)`。
- `Int` scrutinee に対するリテラル + `_`。
- ネスト: `Option[Option[Int]]` に対する `Some(Some(x))` + `Some(None)` + `None`。
- 単一コンストラクタ ADT の `let Pair(l, r) = ...`、タプル `let (x, y) = ...`。
- scrutinee 型が `Any` の match (スキップ確認)。

非網羅 (TYP0007 を期待、witness を検証):

- `Some(x)` のみ → witness `None`。
- `None` のみ → witness `Some(_)`。
- `true` のみ → witness `false`。
- `Int` に対するリテラルのみ → witness `_`。
- guard 付き `Some(x) if p` + `None` → witness `Some(_)`。
- `List[Int]` に対する `Nil` + `Cons(x, Nil)` → witness `Cons(_, Cons(_, _))`。
- タプル `(Bool, Bool)` の 3 ケース → 欠落組を witness。

反駁可能束縛 (TYP0008 を期待):

- `let Some(x) = ...`。
- `let (1, y) = ...` (リテラルを含むタプル)。
- `for Some(x) in xs:`。

回帰:

- 既存の全テストが通ること (`PYTHONPATH=. python3 -m unittest discover -s tests`)。
- 全 `samples/*.lune` が `--check` を通過すること。
