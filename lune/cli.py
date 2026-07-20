from __future__ import annotations

import argparse
import pprint
import sys

from .diagnostics import SourceMap, format_diagnostic, format_exception
from .evaluator import force_value, format_value
from .explanations import available_codes, render_explanation
from .lexer import lex
from .layout import apply_layout
from .module_loader import check_file, eval_file
from .parser import parse_source
from .repl import repl_main


def explain_command(args: list[str]) -> int:
    if len(args) != 1:
        print("usage: lune explain <CODE>", file=sys.stderr)
        print(f"available codes: {', '.join(available_codes())}", file=sys.stderr)
        return 2
    text = render_explanation(args[0])
    if text is None:
        print(f"error: no explanation for diagnostic code {args[0]!r}", file=sys.stderr)
        print(f"available codes: {', '.join(available_codes())}", file=sys.stderr)
        return 1
    print(text)
    return 0


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "explain":
        return explain_command(argv[1:])

    parser = argparse.ArgumentParser(prog="lune-v0.1")
    parser.add_argument("file", nargs="?")
    parser.add_argument("--repl", action="store_true", help="start an interactive REPL")
    parser.add_argument("--tokens", action="store_true", help="print layout-processed tokens")
    parser.add_argument("--check", action="store_true", help="type-check the file")
    parser.add_argument("--eval", metavar="NAME", help="evaluate the file and print a top-level binding")
    parser.add_argument("--module-path", action="append", default=[], help="add a module search root")
    args = parser.parse_args(argv)

    if args.repl:
        return repl_main(sys.stdin, sys.stdout, sys.stderr)

    if args.file is None:
        parser.error("file is required unless --repl is used")

    source_map = SourceMap()

    try:
        if args.check:
            env = check_file(args.file, args.module_path, source_map)
            for warning in env.warnings:
                print(format_diagnostic(warning, source_map, explain_hint=True), file=sys.stderr)
            print("type check OK")
            return 0

        if args.eval:
            env = eval_file(args.file, args.module_path, source_map)
            print(format_value(env.lookup_raw(args.eval)))
            return 0

        with open(args.file, "r", encoding="utf-8") as f:
            source = f.read()
        source_map.add(args.file, source)

        if args.tokens:
            for token in apply_layout(lex(source, args.file)):
                print(f"{token.span.line}:{token.span.column}\t{token.kind.name}\t{token.lexeme!r}\t{token.value!r}")
            return 0

        tree = parse_source(source, args.file)
        pprint.pp(tree, width=120)
        return 0
    except Exception as exc:
        print(format_exception(exc, source_map, explain_hint=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
