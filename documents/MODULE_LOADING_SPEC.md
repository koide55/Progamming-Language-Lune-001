# Lune モジュール読み込み仕様

Version: 0.1 draft  
Related: `LANGUAGE_SPEC.md`, `LEXER_PARSER_SPEC.md`, `TYPE_CHECKER_SPEC.md`, `STANDARD_LIBRARY_SPEC.md`, `ERROR_DIAGNOSTICS_SPEC.md`

この文書は Lune v0.1 のモジュール読み込み機能を定義する。

## 1. 目的

v0.1 のモジュール読み込みは、複数ファイルに分けた小さなプログラムを型チェック・評価できるようにするための最小機能である。

目標:

- `import foo.bar` で別ファイルを読み込む。
- 依存モジュールを entry file より先に型チェック・評価する。
- 循環 import を検出する。
- Java import など外部 import と Lune モジュール import を区別する。
- 既存の prelude 標準ライブラリと共存する。

非目標:

- パッケージ管理。
- 公開/非公開 API 制御。
- qualified name による名前空間アクセス。
- incremental compilation。
- Java 型の実解決。

## 2. ファイル解決

`import foo.bar` は探索 root ごとに次のパスへ解決する。

```text
<root>/foo/bar.lune
```

探索 root:

1. entry file の親ディレクトリ。
2. カレントワーキングディレクトリ。
3. CLI の `--module-path PATH` で追加されたディレクトリ。

同じファイルが複数 root から見つかる場合、最初に見つかったものを採用する。

## 3. 外部 import

次の import は v0.1 では外部 import として扱う。

```text
java.*
javax.*
kotlin.*
std.*
```

外部 import はファイル解決しない。typechecker では import 末尾名または alias を `Any` として登録する。

例:

```lune
import java.time.LocalDate
```

は `LocalDate: Any` を登録する。

## 4. module 宣言

読み込まれるファイルは、可能なら module 宣言を持つ。

```lune
module foo.bar
```

`import foo.bar` で読み込んだファイルの module 宣言が `foo.bar` と異なる場合はエラーにする。

entry file の module 宣言は任意であり、ファイルパスと一致しなくてもよい。

## 5. 名前の扱い

v0.1 では import されたモジュールのトップレベル宣言を、同じグローバル環境へ直接登録する。

```lune
import math

let answer = add(20, 22)
```

`math.lune` に `def add(...)` があれば、import 側では `add` を非修飾で参照できる。

名前空間アクセス:

```lune
math.add(1, 2)
```

は v0.1 では未対応である。

## 6. 読み込み順

依存モジュールは entry module より先に処理する。

```text
entry -> imports A, B
A -> imports C

processing order:
C, A, B, entry
```

同じファイルは一度だけ読み込む。

## 7. 循環 import

循環 import はエラーにする。

例:

```text
a imports b
b imports a
```

診断:

```text
error[MOD0002]: cyclic import: a -> b -> a
```

## 8. 型チェック

module loader は次の順で型チェックする。

1. entry file から import graph を構築する。
2. 依存順に各モジュールを型環境へ追加する。
3. 外部 import は `Any` として登録する。
4. Lune モジュール import は、依存モジュールの宣言が同じ型環境に登録済みであるため、追加の alias 登録は行わない。

v0.1 ではすべてのトップレベル名が公開される。

## 9. 評価

module loader は依存順に各モジュールを評価する。

評価は同じ runtime 環境に対して行う。依存モジュールの `let` / `def` / `type` は entry file から参照できる。

注意:

- トップレベル `let` は遅延束縛なので、import しただけでは右辺は評価されない。
- `strict let` はモジュール評価時に評価される。

## 10. CLI

v0.1 CLI は file mode で module loader を使う。

```sh
PYTHONPATH=. python3 -m lune.cli --check src/main.lune
PYTHONPATH=. python3 -m lune.cli --eval answer src/main.lune
```

追加 option:

```sh
--module-path PATH
```

複数指定できる。

## 11. REPL

REPL の `import` は v0.1 では外部 import と同じく型環境への `Any` 登録に留める。

ファイルモジュールを REPL に読み込む `:load` は将来対応とする。

## 12. 診断コード

| Code | Meaning |
| --- | --- |
| `MOD0001` | module file not found |
| `MOD0002` | cyclic import |
| `MOD0003` | module declaration does not match import path |

## 13. v0.1 の制限

- import alias は外部 import にのみ意味を持つ。
- Lune module import は全トップレベル名をグローバルに取り込む。
- 名前衝突は後から処理された宣言が上書きする。
- qualified access は未対応。
- package metadata は未対応。
