"""Message catalog for diagnostic text (messages, labels, hints).

Every user-facing diagnostic string is built through `t(key, **params)` so the
whole compiler can speak more than one language. The English text is the
source of truth (tests assert against it); the Japanese text must cover every
key — parity is enforced by tests/test_messages.py, which also scans the
source tree so that a `t("...")` call with an unknown key cannot ship.

The active language is process-wide state, set once at the entry points
(CLI `--lang`, REPL `:lang`, playground selector) via `set_language`. The
CLI entry point also honors the `LUNE_LANG` environment variable (en/ja)
as the default; an explicit `--lang` flag overrides it, and invalid values
fall back to English.
"""

from __future__ import annotations

LANGUAGES = ("en", "ja")

_current = "en"


def set_language(lang: str) -> None:
    global _current
    _current = lang if lang in LANGUAGES else "en"


def get_language() -> str:
    return _current


def t(key: str, **params: object) -> str:
    en, ja = MESSAGES[key]
    template = ja if _current == "ja" else en
    return template.format(**params) if params else template


# key: (english, japanese)
MESSAGES: dict[str, tuple[str, str]] = {
    # --- lexer / layout ---
    "lex.tabs-in-indentation": ("tabs are not allowed in indentation", "インデントにタブは使えません"),
    "lex.use-spaces": ("use spaces for indentation", "インデントにはスペースを使う"),
    "lex.replace-tabs": ("replace tabs with spaces", "行頭のタブをスペースに置き換えてください"),
    "lex.unterminated-block-comment": ("unterminated block comment", "ブロックコメントが閉じていません"),
    "lex.unterminated-string": ("unterminated string literal", "文字列リテラルが閉じていません"),
    "lex.char-literal-one": (
        "character literal must contain exactly one character",
        "文字リテラルの中身はちょうど 1 文字でなければなりません",
    ),
    "lex.unexpected-character": ("unexpected character {ch}", "予期しない文字 {ch}"),
    "label.unexpected-character": ("unexpected character", "予期しない文字"),
    "lay.bad-indentation": (
        "indentation does not match any outer indentation level",
        "インデントがどの外側のインデントレベルとも一致しません",
    ),
    "label.bad-indentation": ("indentation does not match an outer level", "外側のレベルと揃っていない"),
    "lay.unmatched-delimiter": ("unmatched closing delimiter", "対応しない閉じ括弧です"),
    "label.unmatched-delimiter": ("unmatched closing delimiter", "対応する開き括弧がない"),
    # --- parser ---
    "prs.expected-token": ("expected {expected}, got {got}", "{expected} が必要ですが、{got} が見つかりました"),
    "label.expected-token": ("expected {expected}", "{expected} が必要"),
    "label.unexpected-token": ("unexpected token", "予期しないトークン"),
    "prs.expected-top-level": (
        "expected top-level declaration, got {got}",
        "トップレベル宣言が必要ですが、{got} が見つかりました",
    ),
    "prs.expected-newline": ("expected newline or end of block", "改行またはブロックの終わりが必要です"),
    "prs.expected-expression": ("expected expression, got {got}", "式が必要ですが、{got} が見つかりました"),
    "prs.expected-pattern": ("expected pattern, got {got}", "パターンが必要ですが、{got} が見つかりました"),
    "prs.param-annotation": ("parameter requires a type annotation", "引数には型注釈が必要です"),
    # --- modules ---
    "mod.cyclic-import": ("cyclic module import detected: {cycle}", "モジュールの循環 import を検出しました: {cycle}"),
    "label.cyclic-import": ("this import closes the cycle", "この import が循環を閉じている"),
    "mod.declaration-mismatch": (
        "module declaration mismatch: expected {expected}, got {got}",
        "module 宣言の不一致: {expected} のはずが {got} でした",
    ),
    "label.declaration-mismatch": ("module name does not match the import path", "モジュール名が import パスと一致しない"),
    "hint.declaration-mismatch": (
        "change the declaration to `module {expected}` or import it as `{got}`",
        "宣言を `module {expected}` に直すか、`{got}` として import してください",
    ),
    "mod.not-found": ("module not found: {path}", "モジュールが見つかりません: {path}"),
    "label.module-not-found": ("no matching .lune file was found", "対応する .lune ファイルが見つからない"),
    "hint.module-searched": ("searched: {roots}", "検索した場所: {roots}"),
    "mod.unreadable": ("failed to read module file: {path}", "モジュールファイルを読み取れませんでした: {path}"),
    "label.module-unreadable": ("module file could not be read", "ファイルを読み取れない"),
    # --- typechecker: names ---
    "typ.undefined-name": ("undefined name: {name}", "未定義の名前: {name}"),
    "typ.undefined-constructor": ("undefined constructor: {name}", "未定義のコンストラクタ: {name}"),
    "typ.undefined-record-type": ("undefined record type: {name}", "未定義のレコード型: {name}"),
    "label.name-not-defined": ("name is not defined", "この名前は定義されていない"),
    "hint.did-you-mean": ("did you mean `{name}`?", "もしかして `{name}` ですか?"),
    "fix.replace-with": ("replace with `{name}`", "`{name}` に置き換える"),
    # --- typechecker: types ---
    "typ.expected-got": ("expected {expected}, got {actual}", "{expected} が必要ですが、{actual} が見つかりました"),
    "typ.context-expected-got": (
        "{context}: expected {expected}, got {actual}",
        "{context}: {expected} が必要ですが、{actual} が見つかりました",
    ),
    "label.expression-has-type": ("this expression has type {type}", "この式の型は {type}"),
    "label.function-body-has-type": ("function body has type {type}", "関数本体の型は {type}"),
    "label.element-has-type": ("this element has type {type}", "この要素の型は {type}"),
    "label.lambda-body-has-type": ("lambda body has type {type}", "ラムダ本体の型は {type}"),
    "label.annotation-rejects-expected": (
        "annotation {annotation} does not accept expected {expected}",
        "注釈 {annotation} は期待される型 {expected} を受け付けない",
    ),
    # --- typechecker: context strings (fill the {context} slot of the type
    #     errors above and the {label} slot of typ.annotation-required;
    #     operator contexts like `??` or `&&` stay raw — symbols need no
    #     translation) ---
    "ctx.let-annotation": ("let annotation", "let の型注釈"),
    "ctx.var-annotation": ("var annotation", "var の型注釈"),
    "ctx.list-element": ("list element", "リストの要素"),
    "ctx.unary-minus": ("unary -", "単項 -"),
    "ctx.unary-not": ("unary !", "単項 !"),
    "ctx.if-condition": ("if condition", "if の条件"),
    "ctx.elif-condition": ("elif condition", "elif の条件"),
    "ctx.while-condition": ("while condition", "while の条件"),
    "ctx.match-guard": ("match guard", "match のガード"),
    "ctx.branch": ("branch", "分岐"),
    "ctx.assignment": ("assignment", "代入"),
    "ctx.lambda-body": ("lambda body", "ラムダ本体"),
    "ctx.literal-pattern": ("literal pattern", "リテラルパターン"),
    "ctx.typed-pattern": ("typed pattern", "型付きパターン"),
    "ctx.return-type-of": ("return type of {name}", "{name} の戻り値型"),
    "ctx.parameter": ("parameter {name}", "引数 {name}"),
    "ctx.type-parameter": ("type parameter {name}", "型パラメータ {name}"),
    "label.condition-must-be-bool": ("condition must be Bool", "条件は Bool でなければならない"),
    "typ.expected-numeric": (
        "{context}: expected numeric type, got {type}",
        "{context}: 数値型が必要ですが、{type} が見つかりました",
    ),
    "typ.cannot-compare": ("{context}: cannot compare {left} and {right}", "{context}: {left} と {right} は比較できません"),
    "typ.branch-mismatch": ("branch type mismatch: {current} vs {other}", "分岐の型が一致しません: {current} と {other}"),
    "typ.fn-param-count": (
        "expected {expected} function parameters, got {actual}",
        "関数の引数は {expected} 個のはずですが、{actual} 個です",
    ),
    "typ.expected-value-type": (
        "expected value type, got function type {type}",
        "値の型が必要ですが、関数型 {type} が見つかりました",
    ),
    "typ.annotation-required": ("{label} requires a type annotation in v0.1", "v0.1 では {label} に型注釈が必要です"),
    "typ.nullable-fn": (
        "function type cannot be nullable in v0.1: {type}",
        "v0.1 では関数型を nullable にはできません: {type}",
    ),
    "typ.safe-nav-receiver": (
        "?. expects a nullable receiver, got {type}",
        "?. の左辺は nullable でなければなりませんが、{type} でした",
    ),
    "typ.null-coalesce-left": (
        "?? expects a nullable left operand, got {type}",
        "?? の左辺は nullable でなければなりませんが、{type} でした",
    ),
    "label.not-nullable": ("this expression is not nullable", "この式は nullable ではない"),
    # --- typechecker: calls ---
    "typ.not-callable": ("value is not callable: {type}", "呼び出せない値です: {type}"),
    "label.not-callable": ("this value is not callable", "この値は呼び出せない"),
    "typ.arity-most": ("expected at most {max} arguments, got {got}", "引数は最大 {max} 個ですが、{got} 個渡されました"),
    "typ.arity-exact": ("expected {expected} arguments, got {got}", "引数は {expected} 個のはずですが、{got} 個です"),
    "label.wrong-arg-count": ("wrong number of arguments", "引数の個数が違う"),
    "typ.lambda-params": (
        "lambda takes {got} parameters, but expected type has {expected}",
        "ラムダの引数は {got} 個ですが、期待される型では {expected} 個です",
    ),
    "label.lambda-params": ("too many lambda parameters", "ラムダの引数が多すぎる"),
    # --- typechecker: match ---
    "typ.non-exhaustive": ("non-exhaustive match: missing case {witness}", "網羅的でない match: {witness} のケースがありません"),
    "label.non-exhaustive": ("pattern {witness} is not covered", "パターン {witness} がカバーされていない"),
    "hint.add-case": (
        "add a case for {witness}, or a wildcard case `| _ -> ...`",
        "{witness} のケースを追加するか、ワイルドカードケース `| _ -> ...` を追加してください",
    ),
    "hint.guarded-cases": (
        "guarded cases do not count toward exhaustiveness",
        "ガード付きケースは網羅性の判定に数えられません",
    ),
    "typ.unreachable-case": ("unreachable match case: {pattern}", "到達しない match ケース: {pattern}"),
    "label.unreachable-case": ("this case can never match", "このケースには決して到達しない"),
    "hint.unreachable-case": (
        "remove this case, or move it before the cases that cover it",
        "このケースを削除するか、これをカバーしているケースより前に移動してください",
    ),
    "typ.refutable-pattern": (
        "refutable pattern in {context} binding: {pattern}",
        "{context} の束縛に反駁可能パターンは使えません: {pattern}",
    ),
    "label.refutable-pattern": ("this pattern can fail to match", "このパターンはマッチに失敗し得る"),
    "hint.refutable-uncovered": ("the pattern does not cover {witness}", "このパターンは {witness} をカバーしていません"),
    "hint.refutable-use-match": (
        "use `match` to handle all cases of {type}",
        "`match` を使って {type} の全ケースを場合分けしてください",
    ),
    "typ.ctor-pattern-arity": (
        "constructor pattern {name} expects {expected} fields, got {got}",
        "コンストラクタパターン {name} のフィールドは {expected} 個ですが、{got} 個です",
    ),
    "typ.tuple-pattern": ("tuple pattern cannot match {type}", "タプルパターンは {type} にはマッチできません"),
    # --- typechecker: inference / declarations ---
    "typ.recursive-return-type": (
        "recursive function requires a return type annotation: {name}",
        "再帰関数には戻り値型の注釈が必要です: {name}",
    ),
    "label.recursive-return-type": (
        "the function calls itself before its type is known",
        "型が確定する前に関数が自分自身を呼んでいる",
    ),
    "hint.recursive-return-type": (
        "add a return type, e.g. `def {name}(...): T = ...`",
        "戻り値型を追加してください。例: `def {name}(...): T = ...`",
    ),
    "typ.cannot-infer-param": ("cannot infer type of parameter {name}", "引数 {name} の型を推論できません"),
    "label.param-falls-back": ("parameter type falls back to Any", "引数の型が Any にフォールバックする"),
    "hint.annotate-param": (
        "add a type annotation, e.g. `fn {name}: Int -> ...`",
        "型注釈を追加してください。例: `fn {name}: Int -> ...`",
    ),
    "typ.for-iterable": ("for iterable must be List, got {type}", "for の対象は List でなければなりませんが、{type} でした"),
    "label.for-iterable": ("iterable must be List[T]", "走査対象は List[T] でなければならない"),
    "typ.only-name-assign": (
        "only name assignment is supported by the type checker",
        "型チェッカは名前への代入だけをサポートしています",
    ),
    # --- typechecker: records ---
    "rec.duplicate-field": ("duplicate record field: {field}", "レコードフィールドの重複宣言: {field}"),
    "label.duplicate-field": ("field is declared more than once", "フィールドが複数回宣言されている"),
    "rec.unknown-field": ("unknown record field: {record}.{field}", "存在しないレコードフィールド: {record}.{field}"),
    "label.unknown-field": ("field is not declared by this record", "このレコードにそのフィールドは宣言されていない"),
    "rec.missing-field": (
        "missing record field for {record}: {field}",
        "レコード {record} のフィールドが不足しています: {field}",
    ),
    "label.missing-field": ("record construction is missing a required field", "必要なフィールドが与えられていない"),
    "rec.duplicate-init": ("duplicate record initializer field: {field}", "初期化でフィールドが二重に指定されています: {field}"),
    "label.duplicate-init": ("field is initialized more than once", "フィールドが複数回初期化されている"),
    "rec.unexpected-field": (
        "unexpected record field for {record}: {field}",
        "レコード {record} に宣言されていないフィールドです: {field}",
    ),
    "label.unexpected-field": ("this field is not declared by the record", "このフィールドはレコードに宣言されていない"),
    "rec.named-fields": ("{record} requires named record fields", "{record} の構築には名前付きフィールドが必要です"),
    "label.named-fields": ("use field = value", "フィールド = 値 の形で書く"),
    # --- typechecker/evaluator: unsupported (v0.1 gaps) ---
    "typ.unsupported-declaration": ("unsupported declaration: {kind}", "サポートされていない宣言です: {kind}"),
    "typ.unsupported-expression": ("unsupported expression: {kind}", "サポートされていない式です: {kind}"),
    "typ.unsupported-member": (
        "unsupported member access on {type}: {name}",
        "{type} へのメンバアクセスはサポートされていません: {name}",
    ),
    "typ.unsupported-binary-op": ("unsupported binary operator: {op}", "サポートされていない二項演算子です: {op}"),
    "typ.unsupported-pattern": ("unsupported pattern: {kind}", "サポートされていないパターンです: {kind}"),
    "typ.unsupported-type-syntax": ("unsupported type syntax: {kind}", "サポートされていない型構文です: {kind}"),
    "typ.unsupported-generic-base": ("unsupported generic type base: {type}", "サポートされていないジェネリック型ベースです: {type}"),
    # --- evaluator (runtime) ---
    "run.recursive-thunk": (
        "recursive thunk evaluation: this value's definition depends on its own result",
        "再帰的なサンク評価: この値の定義が自分自身の結果に依存しています",
    ),
    "hint.recursive-thunk": (
        "recursive values cannot be computed; use a recursive function (`def`) instead, or break the reference cycle",
        "再帰的な値は計算できません。再帰関数 (`def`) として書くか、参照の循環を断ち切ってください",
    ),
    "run.division-by-zero": ("division by zero", "ゼロ除算です"),
    "hint.division-by-zero": (
        "the right operand of `{op}` evaluated to 0",
        "`{op}` の右オペランドが 0 に評価されました",
    ),
    "run.undefined-variable": ("undefined variable: {name}", "未定義の変数: {name}"),
    "run.crash-evaluated": ("crash() was evaluated", "crash() が評価されました"),
    "run.expects": ("{func} expects {expected}, got {got}", "{func} には {expected} を渡す必要がありますが、{got} でした"),
    "run.expects-lists": ("{func} expects Lists", "{func} には List を渡す必要があります"),
    "run.not-callable": ("value is not callable: {value}", "呼び出せない値です: {value}"),
    "run.non-exhaustive": ("non-exhaustive match for value: {value}", "値がどの match ケースにも一致しません: {value}"),
    "run.let-pattern": ("let pattern did not match", "let のパターンがマッチしませんでした"),
    "run.for-iterable": ("for iterable must be List, got {got}", "for の対象は List でなければなりませんが、{got} でした"),
    "run.for-pattern": ("for pattern did not match: {value}", "for のパターンがマッチしませんでした: {value}"),
    "run.arity-fn": (
        "{func} expects at most {max} arguments, got {got}",
        "{func} の引数は最大 {max} 個ですが、{got} 個渡されました",
    ),
    "run.arity-ctor-more": (
        "{ctor} expects at most {max} more arguments, got {got}",
        "{ctor} に渡せる残りの引数は最大 {max} 個ですが、{got} 個渡されました",
    ),
    "run.named-fields": ("{ctor} requires named record fields", "{ctor} の構築には名前付きフィールドが必要です"),
    "run.unexpected-record-field": (
        "unexpected record field for {ctor}: {field}",
        "レコード {ctor} に宣言されていないフィールドです: {field}",
    ),
    "run.duplicate-init": ("duplicate record initializer field: {field}", "初期化でフィールドが二重に指定されています: {field}"),
    "run.missing-record-field": (
        "missing record field for {ctor}: {field}",
        "レコード {ctor} のフィールドが不足しています: {field}",
    ),
    "run.unknown-record-field": ("unknown record field: {record}.{field}", "存在しないレコードフィールド: {record}.{field}"),
    "run.unsupported-declaration": ("unsupported declaration: {kind}", "サポートされていない宣言です: {kind}"),
    "run.unsupported-expression": ("unsupported expression: {kind}", "サポートされていない式です: {kind}"),
    "run.unsupported-pattern": ("unsupported pattern: {kind}", "サポートされていないパターンです: {kind}"),
    "run.unsupported-binary-op": ("unsupported binary operator: {op}", "サポートされていない二項演算子です: {op}"),
    "run.unsupported-unary-op": ("unsupported unary operator: {op}", "サポートされていない単項演算子です: {op}"),
    "run.unsupported-member": (
        "unsupported member access: {receiver}.{name}",
        "サポートされていないメンバアクセスです: {receiver}.{name}",
    ),
    "run.data-field-access": (
        "data field access is not implemented yet; use match",
        "データ型のフィールドアクセスは未実装です。match を使ってください",
    ),
    "run.only-var-assign": ("only variable assignment is implemented", "代入は変数に対してのみ実装されています"),
    # --- renderer ---
    "diag.explain-footer": (
        "run `lune explain {code}` for a detailed explanation",
        "詳しくは `lune explain {code} --lang ja` を実行してください",
    ),
}
