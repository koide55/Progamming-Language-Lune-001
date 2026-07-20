"""Long-form explanations for diagnostic codes.

This is the content behind `lune explain <CODE>` and the `:explain` REPL
command. Each entry teaches: what the error means, a small example that
triggers it, and how to fix it. Keeping every code that the compiler can emit
explained here is enforced by tests/test_explanations.py.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Explanation:
    code: str
    title: str
    summary: str
    example: str | None
    fix: str


def _e(code: str, title: str, summary: str, example: str | None, fix: str) -> tuple[str, Explanation]:
    return code, Explanation(code, title, summary.strip(), example.strip() if example else None, fix.strip())


EXPLANATIONS: dict[str, Explanation] = dict(
    [
        # --- layout ---
        _e(
            "LAY0001",
            "inconsistent indentation",
            """
Lune uses indentation (layout) to delimit blocks, like Python. A line's
indentation did not line up with any enclosing block, so the compiler could
not tell where the block starts or ends.
            """,
            """
def f(x: Int): Int =
    let y = x
      y + 1        # over-indented: does not match the block above
            """,
            """
Indent continuation lines consistently under their block. Use the same number
of spaces for lines at the same level, and do not mix indentation widths.
            """,
        ),
        _e(
            "LAY0002",
            "unmatched closing delimiter",
            """
A closing `)`, `]`, or `}` was found without a matching opener.
            """,
            """
let x = (1 + 2))   # one `)` too many
            """,
            "Remove the extra delimiter, or add the opener it was meant to close.",
        ),
        # --- lexer ---
        _e(
            "LXL0001",
            "unexpected character",
            """
The lexer found a character that is not part of any Lune token.
            """,
            """
let x = $1         # `$` is not a valid character here
            """,
            "Remove or replace the stray character.",
        ),
        _e(
            "LXL0002",
            "unterminated string or character literal",
            """
A string `"..."` or character `'.'` literal was not closed on its line, or a
character literal did not contain exactly one character.
            """,
            """
let s = "hello     # missing closing quote
let c = 'ab'       # a char literal holds exactly one character
            """,
            'Close the quote. Use `"..."` for strings and `\'x\'` for a single character.',
        ),
        _e(
            "LXL0003",
            "unterminated block comment",
            """
A `###` block comment was opened but never closed.
            """,
            """
### this comment never ends
let x = 1
            """,
            "Add the closing `###`.",
        ),
        _e(
            "LXL0004",
            "tabs are not allowed in indentation",
            """
Lune requires spaces for indentation. A tab character appeared at the start of
a line, which would make layout ambiguous.
            """,
            None,
            "Replace leading tabs with spaces (configure your editor to insert spaces).",
        ),
        # --- parser ---
        _e(
            "PRS0001",
            "unexpected token",
            """
The parser met a token that cannot start or continue the construct it was
reading.
            """,
            None,
            "Check the syntax around the caret; a keyword, operator, or delimiter is likely missing or misplaced.",
        ),
        _e(
            "PRS0002",
            "expected a specific token",
            """
The parser required a particular token (such as a NEWLINE or `)`) but found a
different one. A common cause is writing a `type` declaration on one line.
            """,
            """
type Color = | Red | Green | Blue      # not allowed on one line

type Color =                           # constructors go on indented lines
    | Red
    | Green
    | Blue
            """,
            "Follow the expected form shown by the message; add the missing token or split across lines.",
        ),
        # --- modules ---
        _e(
            "MOD0001",
            "module not found or unreadable",
            """
An `import` could not be resolved to a `.lune` file on the module search path,
or the file existed but could not be read.
            """,
            """
import math        # no math.lune found on the search path
            """,
            "Check the module name and file path. Add search roots with `--module-path PATH`.",
        ),
        _e(
            "MOD0002",
            "cyclic module import",
            """
Two or more modules import each other, forming a cycle. Lune loads modules in
dependency order, which a cycle makes impossible.
            """,
            None,
            "Break the cycle: move the shared definitions into a third module that both import.",
        ),
        _e(
            "MOD0003",
            "module declaration mismatch",
            """
A file's `module X` declaration does not match the path it was imported under.
            """,
            None,
            "Rename the `module` declaration to match the import path, or import it under its declared name.",
        ),
        # --- types ---
        _e(
            "TYP0001",
            "undefined name",
            """
A name was used that is not bound in the current scope and is not provided by
the prelude or an import.
            """,
            """
let y = x + 1      # x was never defined
            """,
            "Define or import the name before using it, and check the spelling.",
        ),
        _e(
            "TYP0003",
            "type mismatch",
            """
An expression's type does not match the type required by its context: a `let`
or parameter annotation, a function argument, a branch of `if`/`match`, an
operator, or a return type.
            """,
            """
let x: Int = "hi"  # expected Int, got String
            """,
            "Make the value's type match the expected type, or change the annotation.",
        ),
        _e(
            "TYP0004",
            "value is not callable",
            """
A value that is not a function or data constructor was applied to arguments.
            """,
            """
let x = 1
let y = x(2)       # x is an Int, not a function
            """,
            "Only call functions, lambdas, or constructors.",
        ),
        _e(
            "TYP0005",
            "wrong number of arguments",
            """
A function or constructor was given too many arguments, or too few for
something that is not partially applicable.
            """,
            """
def add(x: Int, y: Int): Int = x + y
let z = add(1, 2, 3)   # add takes 2 arguments
            """,
            "Pass the right number of arguments. Passing fewer to a user-defined function returns a partial application.",
        ),
        _e(
            "TYP0006",
            "for-loop iterable must be a List",
            """
A `for` loop can only iterate over a `List[T]`.
            """,
            """
for x in 10:       # 10 is an Int, not a List
    print(x)
            """,
            "Iterate over a `List[T]`, e.g. `range(0, 10)`.",
        ),
        _e(
            "TYP0007",
            "non-exhaustive match",
            """
A `match` does not cover every possible value of the scrutinee. The message
shows a witness: an example value that no case matches. For a nullable `T?`,
both `null` and the inner values must be covered.
            """,
            """
type Color =
    | Red
    | Green
    | Blue

def name(c: Color): Int =
    match c:
        | Red -> 1
        | Green -> 2     # Blue is not covered
            """,
            "Add a case for the missing pattern, or a wildcard case `| _ -> ...`.",
        ),
        _e(
            "TYP0008",
            "refutable pattern in a binding",
            """
`let` and `for` bindings must be irrefutable — they must match every possible
value. A pattern that can fail (a constructor, literal, or `null`) is not
allowed there.
            """,
            """
let Some(x) = findUser()   # this can fail to match (None)
            """,
            "Use `match` to handle the alternatives, or bind with a plain name or `_`.",
        ),
        _e(
            "TYP0009",
            "unreachable match case (warning)",
            """
A `match` case can never match because earlier cases already cover every value
it would match. This is a warning, not an error.
            """,
            """
match c:
    | _ -> 0
    | Red -> 1     # unreachable: the wildcard above already matched
            """,
            "Remove the redundant case, or move it before the cases that cover it.",
        ),
        _e(
            "TYP0010",
            "cannot infer parameter type (warning)",
            """
A lambda parameter's type could not be inferred from context, so it falls back
to `Any`. This weakens type checking for that parameter.
            """,
            """
let f = fn x -> x + 1      # no context to infer x's type
            """,
            "Annotate the parameter (`fn x: Int -> ...`), or use the lambda where the expected type is known (e.g. as a `map` argument).",
        ),
        _e(
            "TYP0011",
            "recursive function needs a return type",
            """
A function that calls itself needs an explicit return type annotation, because
its type is not yet known when the recursive call is checked.
            """,
            """
def fact(n: Int) =                 # missing return type
    if n <= 1 then 1 else n * fact(n - 1)
            """,
            "Add a return type annotation, e.g. `def fact(n: Int): Int = ...`.",
        ),
        # --- records ---
        _e(
            "REC0001",
            "duplicate record field",
            """
A `record` declaration names the same field more than once.
            """,
            """
record User:
    name: String
    name: Int      # declared twice
            """,
            "Rename or remove the duplicate field.",
        ),
        _e(
            "REC0002",
            "unknown record field",
            """
A field was accessed that the record type does not declare.
            """,
            """
record User:
    name: String
let u = User(name = "Ada")
let a = u.age      # User has no field `age`
            """,
            "Access a declared field, and check the spelling.",
        ),
        _e(
            "REC0003",
            "missing record field",
            """
A record was constructed without providing all of its declared fields.
            """,
            """
record User:
    name: String
    age: Int
let u = User(name = "Ada")   # age is missing
            """,
            "Provide every declared field when constructing the record.",
        ),
        _e(
            "REC0004",
            "duplicate initializer field",
            """
A record construction set the same field more than once.
            """,
            """
User(name = "Ada", name = "Bob")   # name set twice
            """,
            "Set each field exactly once.",
        ),
        _e(
            "REC0005",
            "unexpected record field",
            """
A record construction set a field that the record type does not declare.
            """,
            """
record User:
    name: String
User(name = "Ada", age = 36)   # User has no field `age`
            """,
            "Only set fields the record declares.",
        ),
        _e(
            "REC0006",
            "record fields must be named",
            """
Records are constructed with named fields (`field = value`), not positionally.
            """,
            """
record User:
    name: String
User("Ada")        # must be User(name = "Ada")
            """,
            "Construct the record with `field = value` for each field.",
        ),
        # --- runtime ---
        _e(
            "RUN0006",
            "runtime error",
            """
Evaluation failed at run time. Common causes: using an undefined variable,
forcing a thunk that failed or refers to itself, a standard-library value of
the wrong shape, or a `match` that no case matched at run time.
            """,
            None,
            "Read the message for the specific cause. Many runtime errors are caught earlier by `lune --check`, so type-check the file first.",
        ),
    ]
)


def has_explanation(code: str) -> bool:
    return code.upper() in EXPLANATIONS


def available_codes() -> list[str]:
    return sorted(EXPLANATIONS)


def render_explanation(code: str) -> str | None:
    entry = EXPLANATIONS.get(code.upper())
    if entry is None:
        return None
    lines = [f"error[{entry.code}]: {entry.title}", "", entry.summary]
    if entry.example is not None:
        lines.append("")
        lines.append("Example that triggers it:")
        lines.append("")
        lines.extend(f"    {line}" if line.strip() else "" for line in entry.example.splitlines())
    lines.append("")
    lines.append("How to fix:")
    lines.append(entry.fix)
    return "\n".join(lines)
