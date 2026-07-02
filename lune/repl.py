from __future__ import annotations

from dataclasses import dataclass
import sys
from typing import TextIO

from . import nodes as ast
from .diagnostics import SourceMap, format_diagnostic, format_exception
from .evaluator import Env, eval_module_into, force_value, format_value, initial_env
from .parser import parse_source
from .tokens import LuneSyntaxError
from .typechecker import TypeEnv, check_module_into, initial_type_env


REPL_VALUE = "__repl_value"
DECLARATION_PREFIXES = (
    "module ",
    "import ",
    "let ",
    "strict let ",
    "var ",
    "def ",
    "type ",
    "record ",
    "class ",
    "interface ",
)


@dataclass(frozen=True)
class ReplResult:
    kind: str
    message: str
    value: object | None = None
    type_repr: str | None = None
    warnings: tuple = ()


class ReplSession:
    def __init__(self):
        self.type_env = initial_type_env()
        self.eval_env = initial_env()

    def submit(self, source: str, filename: str = "<repl>") -> ReplResult:
        source = source.strip("\n")
        if not source.strip():
            return ReplResult("empty", "")
        if source.lstrip().startswith(":"):
            return self.run_command(source.strip())

        module, is_expr = self._parse_input(source, filename)
        type_snapshot = _clone_type_env(self.type_env)
        warning_start = len(self.type_env.warnings)
        try:
            check_module_into(module, self.type_env)
        except Exception:
            self.type_env = type_snapshot
            raise
        warnings = tuple(self.type_env.warnings[warning_start:])
        del self.type_env.warnings[warning_start:]
        eval_module_into(module, self.eval_env)

        if is_expr:
            value = force_value(self.eval_env.lookup_raw(REPL_VALUE))
            typ = self.type_env.lookup_value(REPL_VALUE)
            message = f"{format_value(value)} : {typ!r}"
            return ReplResult("value", message, value, repr(typ), warnings)
        return ReplResult("ok", "ok", warnings=warnings)

    def run_command(self, command: str) -> ReplResult:
        parts = command.split()
        name = parts[0]
        if name in {":quit", ":q"}:
            return ReplResult("quit", "bye")
        if name == ":help":
            return ReplResult("info", "commands: :help, :quit, :q, :env, :type NAME")
        if name == ":env":
            public = sorted(key for key in self.type_env.values if not key.startswith("__"))
            lines = [f"{key} : {self.type_env.values[key]!r}" for key in public]
            return ReplResult("info", "\n".join(lines))
        if name == ":type":
            if len(parts) != 2:
                return ReplResult("error", "usage: :type NAME")
            typ = self.type_env.lookup_value(parts[1])
            return ReplResult("info", f"{parts[1]} : {typ!r}")
        return ReplResult("error", f"unknown command: {name}")

    def _parse_input(self, source: str, filename: str) -> tuple[ast.ModuleFile, bool]:
        normalized = _ensure_trailing_newline(source)
        if source.lstrip().startswith(DECLARATION_PREFIXES):
            return parse_source(normalized, filename), False
        try:
            return parse_source(normalized, filename), False
        except LuneSyntaxError:
            wrapped = f"let {REPL_VALUE} = {source}\n"
            return parse_source(wrapped, filename), True


def repl_main(stdin: TextIO, stdout: TextIO, stderr: TextIO) -> int:
    session = ReplSession()
    source_map = SourceMap()
    input_index = 1
    line_editor = _configure_line_editor(stdin, stdout)
    stdout.write("Lune v0.1 REPL. Type :help or :quit.\n")
    buffer: list[str] = []

    while True:
        prompt = "... " if buffer else "lune> "
        line = _read_line(prompt, stdin, stdout, line_editor)
        if line == "":
            stdout.write("\n")
            return 0

        if buffer:
            if not line.strip():
                source = "".join(buffer)
                buffer.clear()
            else:
                buffer.append(line)
                continue
        else:
            if _wants_more(line):
                buffer.append(line)
                continue
            source = line

        try:
            filename = f"<repl:{input_index}>"
            input_index += 1
            source_map.add(filename, source)
            result = session.submit(source, filename)
            if result.kind == "empty":
                continue
            for warning in result.warnings:
                stderr.write(format_diagnostic(warning, source_map) + "\n")
            stdout.write(result.message + "\n")
            if result.kind == "quit":
                return 0
        except Exception as exc:
            stderr.write(format_exception(exc, source_map) + "\n")


def _ensure_trailing_newline(source: str) -> str:
    return source if source.endswith("\n") else source + "\n"


def _wants_more(line: str) -> bool:
    stripped = line.rstrip()
    return stripped.endswith(":") or stripped.endswith("=") or stripped.endswith("->")


def _configure_line_editor(stdin: TextIO, stdout: TextIO) -> bool:
    if stdin is not sys.stdin or stdout is not sys.stdout:
        return False
    if not getattr(stdin, "isatty", lambda: False)() or not getattr(stdout, "isatty", lambda: False)():
        return False
    try:
        import atexit
        import os
        import readline
    except ImportError:
        return True

    history_file = os.path.expanduser("~/.lune_history")
    try:
        readline.read_history_file(history_file)
    except FileNotFoundError:
        pass
    except OSError:
        pass
    try:
        readline.set_history_length(1000)
    except AttributeError:
        pass

    def save_history() -> None:
        try:
            readline.write_history_file(history_file)
        except OSError:
            pass

    atexit.register(save_history)
    return True


def _read_line(prompt: str, stdin: TextIO, stdout: TextIO, line_editor: bool) -> str:
    if line_editor:
        try:
            return input(prompt) + "\n"
        except EOFError:
            return ""
    stdout.write(prompt)
    stdout.flush()
    return stdin.readline()


def _clone_type_env(env: TypeEnv) -> TypeEnv:
    clone = TypeEnv(env.parent)
    clone.values = dict(env.values)
    clone.constructors = dict(env.constructors)
    clone.types = dict(env.types)
    clone.records = dict(env.records)
    clone.warnings = list(env.warnings)
    return clone
