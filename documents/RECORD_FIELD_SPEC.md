# Lune レコード / フィールドアクセス仕様

Version: 0.1 draft  
Related: `LANGUAGE_SPEC.md`, `SYNTAX_SPEC.md`, `LEXER_PARSER_SPEC.md`, `TYPE_CHECKER_SPEC.md`, `LAZY_EVALUATION_SPEC.md`

この文書は、Lune v0.1 の次段階として追加するレコードとフィールドアクセスの仕様を定義する。

## 1. 目的

レコードは、クラスより軽量な名前付きフィールドの product type である。

目標:

- 名前付きフィールドを持つ値を定義できる。
- `value.field` でフィールドへアクセスできる。
- 型チェッカがフィールド存在とフィールド型を検査できる。
- 既存の遅延評価モデルと整合する。
- 将来の class / Java object / record update の土台にする。

非目標:

- メソッド定義。
- 継承。
- 可視性制御。
- mutable field。
- record update。
- Java record との相互運用。

## 2. 構文

### 2.1 record 宣言

```lune
record User:
    name: String
    age: Int
```

generic record:

```lune
record Box[T]:
    value: T
```

正格フィールド:

```lune
record Point:
    !x: Double
    !y: Double
```

`strict x: Double` も `!x: Double` と同じ意味にする。

v0.1 では record field はすべて immutable である。`var field` は構文予約に留め、実装しない。

### 2.2 record construction

レコード名は同名のコンストラクタとして利用できる。

```lune
let ada = User(name = "Ada", age = 36)
```

初期実装では named argument のみを許可する。

許可:

```lune
User(name = "Ada", age = 36)
```

非推奨 / 未対応:

```lune
User("Ada", 36)
```

field の指定順は宣言順と異なってもよい。

```lune
User(age = 36, name = "Ada")
```

すべての field はちょうど 1 回指定しなければならない。

### 2.3 field access

```lune
let name = ada.name
let age = ada.age
```

field access は postfix expression であり、既存の member access 構文 `expr.name` を使う。

連鎖:

```lune
let city = user.address.city
```

method call との違い:

```lune
user.name      # field access
user.name()    # method/member call
```

v0.1 では record に method はないため、record field に関数値が入っている場合のみ `user.fnField()` のような呼び出しが可能である。

## 3. AST

追加 AST:

```text
RecordDecl(name, typeParams, fields, span)
RecordField(name, type, isStrict, span)
```

既存 AST を使うもの:

```text
CallExpr(NameExpr("User"), named arguments)
MemberExpr(receiver, fieldName)
```

record construction 専用の `RecordExpr` は v0.1 では導入しない。parser は通常の call として AST を作り、typechecker/evaluator が record constructor value として解釈する。

## 4. 型システム

### 4.1 型環境

型環境は record 情報を保持する。

```text
RecordInfo(
    name: String,
    typeParams: [String],
    fields: [RecordFieldInfo]
)

RecordFieldInfo(
    name: String,
    type: Type,
    isStrict: Bool
)
```

record 宣言:

```lune
record User:
    name: String
    age: Int
```

は以下を型環境へ登録する。

```text
type User
value User : (name: String, age: Int) -> User
field User.name : String
field User.age  : Int
```

内部表現として named parameter を持てない場合、constructor type は declaration order の function type として保持してよい。ただし呼び出し検査では named argument を必須とする。

### 4.2 generic record

```lune
record Box[T]:
    value: T

let box = Box(value = 42)
let value = box.value
```

型:

```text
box   : Box[Int]
value : Int
```

constructor call 時に field の実引数型から型変数を単一化する。

### 4.3 field access の型

`expr.field` の型推論:

1. `expr` の型を推論する。
2. 型が record type であることを確認する。
3. record 定義に `field` が存在することを確認する。
4. generic type argument を field type へ代入し、その型を返す。

例:

```lune
record Pair[A, B]:
    first: A
    second: B

let pair = Pair(first = 1, second = "one")
let x = pair.first
let y = pair.second
```

型:

```text
pair : Pair[Int, String]
x    : Int
y    : String
```

### 4.4 Any receiver

既存の Java 外部 import 逃げ道との互換のため、`Any` receiver の member access は v0.1 では従来通り動的 member として扱う。

```lune
import java.time.LocalDate
let today = LocalDate.now()
```

typechecker は `Any.member` を完全な record field として解決しない。Java 連携が実装されるまで `Any` は逃げ道である。

## 5. 評価

### 5.1 runtime value

record value は次のような runtime value として表現する。

```text
RecordValue(
    typeName: String,
    fields: Dict[String, Value]
)
```

field order は表示や debug のために保持してよい。標準表示では record type name を省略し、フィールド中心で表示する。

```text
{ name = "Ada", age = 36 }
```

### 5.2 construction

```lune
let user = User(name = expensiveName(), age = 36)
```

非正格 field は thunk として保存する。

正格 field は construction 時点で評価する。

```lune
record Point:
    !x: Double
    !y: Double

let p = Point(x = crash(), y = 0.0)
```

この例では `Point(...)` の評価時点で失敗する。

### 5.3 field access と遅延

`user.name` は receiver を弱頭正規形まで評価し、`name` field を取り出す。

field 自体は通常 field なら thunk として保存されている。field access は選択された field を弱頭正規形まで force する。

```lune
record User:
    name: String
    age: Int

let user = User(name = crash(), age = 36)
let age = user.age
```

`age` だけを参照する場合、`name` は評価されない。

```lune
let name = user.name
```

`name` を参照すると `crash()` が評価され、失敗する。

### 5.4 deepForce

`deepForce recordValue` はすべての field を deep force する。

## 6. パターン

record pattern は v0.1 初回実装では必須にしない。field access で代替する。

将来候補:

```lune
match user:
    | User(name = name, age = age) -> name
```

record pattern を導入する場合は、field 名による照合と部分 field 指定を検討する。

## 7. 代入と更新

v0.1 の record field は immutable である。

禁止:

```lune
user.name = "Grace"
```

record update は初回実装では未対応とする。

将来候補:

```lune
let older = user{age = user.age + 1}
```

record update は元の record を変更せず、新しい record value を返す。

## 8. 名前解決

record 宣言:

```lune
record User:
    name: String
```

は同じ top-level scope に以下を導入する。

```text
type User
value User
```

`value User` は record constructor である。既存の top-level 名と衝突する場合は診断するのが望ましい。

v0.1 の module loader では imported module の top-level 名が同じ global environment に入るため、record 名も同じ規則に従う。

## 9. エラー

推奨診断:

| Code | Meaning |
| --- | --- |
| `REC0001` | duplicate record field declaration |
| `REC0002` | unknown record field |
| `REC0003` | missing required record field |
| `REC0004` | duplicate record initializer field |
| `REC0005` | unexpected record initializer field |
| `REC0006` | positional record construction is not supported |
| `REC0007` | record field assignment is not supported |

既存の `TYP000*` と統合してもよいが、実装時には record 固有エラーとして出せる方が診断が分かりやすい。

## 10. 実装ステップ

推奨順:

1. AST に `RecordDecl` / `RecordField` を追加する。
2. parser に `record` top-level declaration を追加する。
3. typechecker に `RecordInfo` と record constructor 型を追加する。
4. evaluator に `RecordConstructorValue` / `RecordValue` を追加する。
5. `CallExpr` で named argument による record construction を解釈する。
6. `MemberExpr` で record field access を型検査・評価する。
7. `deepForce` と表示を record value に対応する。
8. CLI / REPL / module loader で record declaration を通常 top-level declaration として扱う。

## 11. v0.1 制限

- record field は immutable のみ。
- record update は未対応。
- record pattern は未対応。
- record に method は持たせない。
- record は nominal type とする。構造的部分型は導入しない。
- Java record との相互運用は未対応。
- field visibility は導入しない。
