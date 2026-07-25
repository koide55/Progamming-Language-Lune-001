# Lune 診断コード索引 (Error Index)

<!-- 自動生成ファイル。手で編集しない。再生成: ./bin/lune explain --index > documents/ERROR_INDEX.md -->

コンパイラ・評価器が発行する全診断コードの詳解カタログ。同じ内容を
`lune explain <CODE>`、REPL の `:explain CODE`、Playground の explain ボタンでも読める。
発行されうる全コードに詳解があることはテストで保証される（現在 29 コード）。日本語版: `ERROR_INDEX_JA.md`。

- [`LAY0001`](#lay0001) — inconsistent indentation
- [`LAY0002`](#lay0002) — unmatched closing delimiter
- [`LXL0001`](#lxl0001) — unexpected character
- [`LXL0002`](#lxl0002) — unterminated string or character literal
- [`LXL0003`](#lxl0003) — unterminated block comment
- [`LXL0004`](#lxl0004) — tabs are not allowed in indentation
- [`MOD0001`](#mod0001) — module not found or unreadable
- [`MOD0002`](#mod0002) — cyclic module import
- [`MOD0003`](#mod0003) — module declaration mismatch
- [`PRS0001`](#prs0001) — unexpected token
- [`PRS0002`](#prs0002) — expected a specific token
- [`REC0001`](#rec0001) — duplicate record field
- [`REC0002`](#rec0002) — unknown record field
- [`REC0003`](#rec0003) — missing record field
- [`REC0004`](#rec0004) — duplicate initializer field
- [`REC0005`](#rec0005) — unexpected record field
- [`REC0006`](#rec0006) — record fields must be named
- [`RUN0005`](#run0005) — recursive thunk evaluation
- [`RUN0006`](#run0006) — runtime error
- [`TYP0001`](#typ0001) — undefined name
- [`TYP0003`](#typ0003) — type mismatch
- [`TYP0004`](#typ0004) — value is not callable
- [`TYP0005`](#typ0005) — wrong number of arguments
- [`TYP0006`](#typ0006) — for-loop iterable must be a List
- [`TYP0007`](#typ0007) — non-exhaustive match
- [`TYP0008`](#typ0008) — refutable pattern in a binding
- [`TYP0009`](#typ0009) — unreachable match case (warning)
- [`TYP0010`](#typ0010) — cannot infer parameter type (warning)
- [`TYP0011`](#typ0011) — recursive function needs a return type

## LAY0001

**inconsistent indentation**

Lune uses indentation (layout) to delimit blocks, like Python. A line's
indentation did not line up with any enclosing block, so the compiler could
not tell where the block starts or ends.

Example that triggers it:

```lune
def f(x: Int): Int =
    let y = x
      y + 1        # over-indented: does not match the block above
```

How to fix:

Indent continuation lines consistently under their block. Use the same number
of spaces for lines at the same level, and do not mix indentation widths.

## LAY0002

**unmatched closing delimiter**

A closing `)`, `]`, or `}` was found without a matching opener.

Example that triggers it:

```lune
let x = (1 + 2))   # one `)` too many
```

How to fix:

Remove the extra delimiter, or add the opener it was meant to close.

## LXL0001

**unexpected character**

The lexer found a character that is not part of any Lune token.

Example that triggers it:

```lune
let x = $1         # `$` is not a valid character here
```

How to fix:

Remove or replace the stray character.

## LXL0002

**unterminated string or character literal**

A string `"..."` or character `'.'` literal was not closed on its line, or a
character literal did not contain exactly one character.

Example that triggers it:

```lune
let s = "hello     # missing closing quote
let c = 'ab'       # a char literal holds exactly one character
```

How to fix:

Close the quote. Use `"..."` for strings and `'x'` for a single character.

## LXL0003

**unterminated block comment**

A `###` block comment was opened but never closed.

Example that triggers it:

```lune
### this comment never ends
let x = 1
```

How to fix:

Add the closing `###`.

## LXL0004

**tabs are not allowed in indentation**

Lune requires spaces for indentation. A tab character appeared at the start of
a line, which would make layout ambiguous.

How to fix:

Replace leading tabs with spaces (configure your editor to insert spaces).

## MOD0001

**module not found or unreadable**

An `import` could not be resolved to a `.lune` file on the module search path,
or the file existed but could not be read.

Example that triggers it:

```lune
import math        # no math.lune found on the search path
```

How to fix:

Check the module name and file path. Add search roots with `--module-path PATH`.

## MOD0002

**cyclic module import**

Two or more modules import each other, forming a cycle. Lune loads modules in
dependency order, which a cycle makes impossible.

How to fix:

Break the cycle: move the shared definitions into a third module that both import.

## MOD0003

**module declaration mismatch**

A file's `module X` declaration does not match the path it was imported under.

How to fix:

Rename the `module` declaration to match the import path, or import it under its declared name.

## PRS0001

**unexpected token**

The parser met a token that cannot start or continue the construct it was
reading.

How to fix:

Check the syntax around the caret; a keyword, operator, or delimiter is likely missing or misplaced.

## PRS0002

**expected a specific token**

The parser required a particular token (such as a NEWLINE or `)`) but found a
different one. A common cause is writing a `type` declaration on one line.

Example that triggers it:

```lune
type Color = | Red | Green | Blue      # not allowed on one line

type Color =                           # constructors go on indented lines
    | Red
    | Green
    | Blue
```

How to fix:

Follow the expected form shown by the message; add the missing token or split across lines.

## REC0001

**duplicate record field**

A `record` declaration names the same field more than once.

Example that triggers it:

```lune
record User:
    name: String
    name: Int      # declared twice
```

How to fix:

Rename or remove the duplicate field.

## REC0002

**unknown record field**

A field was accessed that the record type does not declare.

Example that triggers it:

```lune
record User:
    name: String
let u = User(name = "Ada")
let a = u.age      # User has no field `age`
```

How to fix:

Access a declared field, and check the spelling.

## REC0003

**missing record field**

A record was constructed without providing all of its declared fields.

Example that triggers it:

```lune
record User:
    name: String
    age: Int
let u = User(name = "Ada")   # age is missing
```

How to fix:

Provide every declared field when constructing the record.

## REC0004

**duplicate initializer field**

A record construction set the same field more than once.

Example that triggers it:

```lune
User(name = "Ada", name = "Bob")   # name set twice
```

How to fix:

Set each field exactly once.

## REC0005

**unexpected record field**

A record construction set a field that the record type does not declare.

Example that triggers it:

```lune
record User:
    name: String
User(name = "Ada", age = 36)   # User has no field `age`
```

How to fix:

Only set fields the record declares.

## REC0006

**record fields must be named**

Records are constructed with named fields (`field = value`), not positionally.

Example that triggers it:

```lune
record User:
    name: String
User("Ada")        # must be User(name = "Ada")
```

How to fix:

Construct the record with `field = value` for each field.

## RUN0005

**recursive thunk evaluation**

A lazy value's definition needs the value itself, so it can never be computed.

Lune evaluates bindings lazily: each `let` builds a thunk that is computed at
most once, when first forced. Before computing, the thunk is marked as
"evaluating". If the computation loops back and forces the same thunk again,
the definition is self-referential — no amount of waiting would produce a
value — so Lune reports this error immediately instead of running forever.

Recursive *functions* are fine: `def` bodies run only when called, so a call
like `fact(n - 1)` does not force the function's own definition. It is
recursive *values* that cannot exist.

Example that triggers it:

```lune
let x = x + 1      # x's value needs x itself

let a = b
let b = a          # forcing either one loops back to it
```

How to fix:

Express the recursion as a function (`def f(n: Int): Int = ... f(...) ...`)
and call it, or restructure the bindings so no value depends on its own
result.

## RUN0006

**runtime error**

Evaluation failed at run time. Common causes: using an undefined variable,
dividing by zero (`/`, `//` or `%`), forcing a thunk that previously failed, a
standard-library value of the wrong shape, or a `match` that no case matched
at run time.

How to fix:

Read the message for the specific cause. Many runtime errors are caught earlier by `lune --check`, so type-check the file first.

## TYP0001

**undefined name**

A name was used that is not bound in the current scope and is not provided by
the prelude or an import.

Example that triggers it:

```lune
let y = x + 1      # x was never defined
```

How to fix:

Define or import the name before using it, and check the spelling.

## TYP0003

**type mismatch**

An expression's type does not match the type required by its context: a `let`
or parameter annotation, a function argument, a branch of `if`/`match`, an
operator, or a return type.

Example that triggers it:

```lune
let x: Int = "hi"  # expected Int, got String
```

How to fix:

Make the value's type match the expected type, or change the annotation.

## TYP0004

**value is not callable**

A value that is not a function or data constructor was applied to arguments.

Example that triggers it:

```lune
let x = 1
let y = x(2)       # x is an Int, not a function
```

How to fix:

Only call functions, lambdas, or constructors.

## TYP0005

**wrong number of arguments**

A function or constructor was given too many arguments, or too few for
something that is not partially applicable.

Example that triggers it:

```lune
def add(x: Int, y: Int): Int = x + y
let z = add(1, 2, 3)   # add takes 2 arguments
```

How to fix:

Pass the right number of arguments. Passing fewer to a user-defined function returns a partial application.

## TYP0006

**for-loop iterable must be a List**

A `for` loop can only iterate over a `List[T]`.

Example that triggers it:

```lune
for x in 10:       # 10 is an Int, not a List
    print(x)
```

How to fix:

Iterate over a `List[T]`, e.g. `range(0, 10)`.

## TYP0007

**non-exhaustive match**

A `match` does not cover every possible value of the scrutinee. The message
shows a witness: an example value that no case matches. For a nullable `T?`,
both `null` and the inner values must be covered.

Example that triggers it:

```lune
type Color =
    | Red
    | Green
    | Blue

def name(c: Color): Int =
    match c:
        | Red -> 1
        | Green -> 2     # Blue is not covered
```

How to fix:

Add a case for the missing pattern, or a wildcard case `| _ -> ...`.

## TYP0008

**refutable pattern in a binding**

`let` and `for` bindings must be irrefutable — they must match every possible
value. A pattern that can fail (a constructor, literal, or `null`) is not
allowed there.

Example that triggers it:

```lune
let Some(x) = findUser()   # this can fail to match (None)
```

How to fix:

Use `match` to handle the alternatives, or bind with a plain name or `_`.

## TYP0009

**unreachable match case (warning)**

A `match` case can never match because earlier cases already cover every value
it would match. This is a warning, not an error.

Example that triggers it:

```lune
match c:
    | _ -> 0
    | Red -> 1     # unreachable: the wildcard above already matched
```

How to fix:

Remove the redundant case, or move it before the cases that cover it.

## TYP0010

**cannot infer parameter type (warning)**

A lambda parameter's type could not be inferred from context, so it falls back
to `Any`. This weakens type checking for that parameter.

Example that triggers it:

```lune
let f = fn x -> x + 1      # no context to infer x's type
```

How to fix:

Annotate the parameter (`fn x: Int -> ...`), or use the lambda where the expected type is known (e.g. as a `map` argument).

## TYP0011

**recursive function needs a return type**

A function that calls itself needs an explicit return type annotation, because
its type is not yet known when the recursive call is checked.

Example that triggers it:

```lune
def fact(n: Int) =                 # missing return type
    if n <= 1 then 1 else n * fact(n - 1)
```

How to fix:

Add a return type annotation, e.g. `def fact(n: Int): Int = ...`.
