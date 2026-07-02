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
- local type inference via expected-type propagation into lambdas, lists, and branches (`TYP0010`, `TYP0011`)
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

Evaluate a top-level binding:

```sh
./bin/lune --eval lazySafe samples/eval.lune
./bin/lune --eval matched samples/eval.lune
./bin/lune --eval total samples/stdlib.lune
./bin/lune --eval answer samples/modules/main.lune
./bin/lune --eval answer samples/records.lune
./bin/lune --eval answer samples/while.lune
```

Add extra module search roots with repeated `--module-path PATH` flags:

```sh
./bin/lune --module-path samples/modules --check samples/modules/main.lune
```

The evaluator is intentionally small. It supports default-lazy `let` bindings and function arguments, `lazy` / `force`, arithmetic, booleans, ADT constructors, and pattern matching. Lazy evaluation includes success memoization, failed-thunk memoization, recursive thunk detection, strict parameters, strict constructor fields, `seq`, and `deepForce`.

The current language behavior is specified in `documents/LANGUAGE_SPEC.md`. The future target language is described in `documents/LANGUAGE_FUTURE_SPEC.md`. Lazy evaluation behavior is specified in `documents/LAZY_EVALUATION_SPEC.md`. The current type checker behavior is specified in `documents/TYPE_CHECKER_SPEC.md`. REPL behavior is specified in `documents/REPL_SPEC.md`. Module loading is specified in `documents/MODULE_LOADING_SPEC.md`. Later features such as class/interface parsing, richer type inference, Java type resolution, and code generation remain for later phases.
