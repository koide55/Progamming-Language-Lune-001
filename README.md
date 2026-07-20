# Lune v0.1 Prototype

This is the first lexer/layout/parser/AST prototype for Lune. Specifications and the tutorial are collected under `documents/`.

Implemented:

- lexer for identifiers, keywords, literals, comments, and operators
- Python-style layout processor that emits `INDENT` and `DEDENT`
- AST dataclasses
- recursive descent parser with a Pratt expression parser
- parsing for `module`, `import`, `let`, `var`, `def`, `type`, `if`, `match`, `fn`, `IO:`, calls, member access, and basic types
- type checker for basic types, functions, ADTs, generic constructor/function calls, `if`, `match`, `lazy`, and `force`
- match exhaustiveness checking with missing-pattern witnesses (`TYP0007`)
- refutable pattern rejection in `let` / `for` bindings (`TYP0008`)
- unreachable match case warnings (`TYP0009`)
- "did you mean" suggestions for undefined names (`TYP0001`) and unknown record fields (`REC0002`, `REC0005`)
- local type inference via expected-type propagation into lambdas, lists, and branches (`TYP0010`, `TYP0011`)
- null safety for `T?`: `null`/`match` patterns with narrowing, `T?`-aware exhaustiveness, the `??` operator, `?.` safe navigation, `if x != null` flow narrowing, and `== null` / `!= null`
- pipeline operator `|>` (`x |> f` is `f(x)`)
- teaching-oriented diagnostics: every code has a detailed explanation via `lune explain <CODE>` (and `:explain` in the REPL); diagnostics link to it
- canonical formatter `lune fmt`: AST-based pretty-printer, idempotent and meaning-preserving (re-parse check), preserves `#` comments, `--write` / `--check` modes
- evaluator for `let`, function calls, lazy thunks, constructors, and `match`
- prelude standard library with `Option`, `Result`, `List`, `print`, `println`, `show`, `map`, `filter`, `fold`, `head`, `tail`, `length`, and `range`
- file module loading for local `.lune` imports, dependency ordering, external Java/std import stubs, and `--module-path`
- partial application for user-defined functions, lambdas, and data constructors
- records with named construction, generic fields, strict fields, and field access
- `while` loops for small imperative blocks with `var`

Run tests:

```sh
PYTHONPATH=. python3 -m unittest discover -s tests
```

Run Lune:

```sh
./bin/lune
```

`./bin/lune` starts the REPL when called without arguments. With arguments, it forwards to the normal CLI.

Parse a sample:

```sh
./bin/lune samples/option.lune
./bin/lune --tokens samples/basics.lune
```

Type-check a sample:

```sh
./bin/lune --check samples/option.lune
./bin/lune --check samples/eval.lune
./bin/lune --check samples/stdlib.lune
./bin/lune --check samples/modules/main.lune
./bin/lune --check samples/records.lune
./bin/lune --check samples/while.lune
./bin/lune --check samples/pipeline.lune
./bin/lune --check samples/nullable.lune
```

Start the REPL:

```sh
./bin/lune
```

When started in a terminal, the REPL supports readline-style line editing and command history.

REPL commands:

```text
:help
:env
:type NAME
:explain CODE
:quit
```

Errors are rendered as diagnostics with codes and source excerpts:

```text
error[LXL0001]: unexpected character '$'
  --> sample.lune:1:9
  |
1 | let x = $1
  |         ^ unexpected character
```

Every diagnostic code has a detailed, teaching-oriented explanation (what it
means, an example that triggers it, and how to fix it). Diagnostics point you
to it, and you can ask for it directly:

```sh
./bin/lune explain TYP0007
```

In the REPL, use `:explain CODE`.

Format source to a canonical style:

```sh
./bin/lune fmt samples/records.lune          # print formatted source to stdout
./bin/lune fmt --write samples/records.lune  # rewrite the file(s) in place
./bin/lune fmt --check samples/records.lune  # exit non-zero if not formatted (CI)
```

`lune fmt` pretty-prints the parsed AST, so output is canonical and idempotent. It re-parses its own output and checks the AST is unchanged, so formatting never alters a program's meaning. `#` comments are preserved; files with `###` block comments are left untouched with an error (not yet supported).

Evaluate a top-level binding:

```sh
./bin/lune --eval lazySafe samples/eval.lune
./bin/lune --eval matched samples/eval.lune
./bin/lune --eval total samples/stdlib.lune
./bin/lune --eval answer samples/modules/main.lune
./bin/lune --eval answer samples/records.lune
./bin/lune --eval answer samples/while.lune
./bin/lune --eval result samples/pipeline.lune
./bin/lune --eval present samples/nullable.lune
```

Add extra module search roots with repeated `--module-path PATH` flags:

```sh
./bin/lune --module-path samples/modules --check samples/modules/main.lune
```

The evaluator is intentionally small. It supports default-lazy `let` bindings and function arguments, `lazy` / `force`, arithmetic, booleans, ADT constructors, and pattern matching. Lazy evaluation includes success memoization, failed-thunk memoization, recursive thunk detection, strict parameters, strict constructor fields, `seq`, and `deepForce`.

The current language behavior is specified in `documents/LANGUAGE_SPEC.md`. The future target language is described in `documents/LANGUAGE_FUTURE_SPEC.md`. Lazy evaluation behavior is specified in `documents/LAZY_EVALUATION_SPEC.md`. The current type checker behavior is specified in `documents/TYPE_CHECKER_SPEC.md`. REPL behavior is specified in `documents/REPL_SPEC.md`. Module loading is specified in `documents/MODULE_LOADING_SPEC.md`. Later features such as class/interface parsing, richer type inference, Java type resolution, and code generation remain for later phases.
