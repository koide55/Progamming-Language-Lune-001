from __future__ import annotations

from dataclasses import dataclass
import sys
from typing import TextIO

from . import nodes as ast
from .diagnostics import DiagnosticError, SourceMap, format_diagnostic, format_exception
from .evaluator import (
    Env,
    LazyValue,
    Thunk,
    ThunkState,
    eval_module_into,
    force_value,
    format_value,
    initial_env,
    preview_value,
    set_trace_hook,
)
from .explanations import LANGUAGES, render_explanation
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
        self.trace_enabled = False

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

        trace_lines: list[str] = []
        if self.trace_enabled:
            set_trace_hook(lambda depth, message: trace_lines.append("  " * depth + message))
        try:
            eval_module_into(module, self.eval_env)
            if is_expr:
                value = force_value(self.eval_env.lookup_raw(REPL_VALUE))
                typ = self.type_env.lookup_value(REPL_VALUE)
                rendered = format_value(value)
        finally:
            if self.trace_enabled:
                set_trace_hook(None)

        if is_expr:
            message = "\n".join([*trace_lines, f"{rendered} : {typ!r}"])
            return ReplResult("value", message, value, repr(typ), warnings)
        return ReplResult("ok", "\n".join([*trace_lines, "ok"]), warnings=warnings)

    def run_command(self, command: str) -> ReplResult:
        parts = command.split()
        name = parts[0]
        if name in {":quit", ":q"}:
            return ReplResult("quit", "bye")
        if name == ":help":
            return ReplResult(
                "info",
                "commands: :help, :quit, :q, :env, :type NAME, :thunks [NAME], :trace [on|off], :explain CODE",
            )
        if name == ":env":
            public = sorted(key for key in self.type_env.values if not key.startswith("__"))
            lines = [f"{key} : {self.type_env.values[key]!r}" for key in public]
            return ReplResult("info", "\n".join(lines))
        if name == ":type":
            if len(parts) != 2:
                return ReplResult("error", "usage: :type NAME")
            typ = self.type_env.lookup_value(parts[1])
            return ReplResult("info", f"{parts[1]} : {typ!r}")
        if name == ":thunks":
            if len(parts) > 2:
                return ReplResult("error", "usage: :thunks [NAME]")
            if len(parts) == 2:
                target = parts[1]
                if target not in self.eval_env.values:
                    return ReplResult("error", f"unknown name: {target}")
                return ReplResult("info", _describe_binding(target, self.eval_env.values[target]))
            lines = [
                _describe_binding(key, value)
                for key, value in self.eval_env.values.items()
                if not key.startswith("__") and isinstance(value, (Thunk, LazyValue))
            ]
            if not lines:
                return ReplResult("info", "no thunks: nothing is bound lazily yet (try `let x = 1 + 1`)")
            return ReplResult("info", "\n".join(lines))
        if name == ":trace":
            if len(parts) == 1:
                return ReplResult("info", f"trace is {'on' if self.trace_enabled else 'off'}")
            if len(parts) == 2 and parts[1] in {"on", "off"}:
                self.trace_enabled = parts[1] == "on"
                return ReplResult("info", f"trace {parts[1]}")
            return ReplResult("error", "usage: :trace [on|off]")
        if name == ":explain":
            if len(parts) not in {2, 3} or (len(parts) == 3 and parts[2] not in LANGUAGES):
                return ReplResult("error", "usage: :explain CODE [en|ja]")
            lang = parts[2] if len(parts) == 3 else "en"
            text = render_explanation(parts[1], lang)
            if text is None:
                return ReplResult("error", f"no explanation for diagnostic code {parts[1]!r}")
            return ReplResult("info", text)
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
                stderr.write(format_diagnostic(warning, source_map, explain_hint=True) + "\n")
            stdout.write(result.message + "\n")
            if result.kind == "quit":
                return 0
        except Exception as exc:
            stderr.write(format_exception(exc, source_map, explain_hint=True) + "\n")


def _describe_binding(name: str, value: object) -> str:
    if not isinstance(value, (Thunk, LazyValue)):
        return f"{name} : value = {preview_value(value)}"
    if value.state == ThunkState.EVALUATED:
        return f"{name} : evaluated = {preview_value(value.value)}"
    if value.state == ThunkState.FAILED:
        error = value.error
        if isinstance(error, DiagnosticError):
            return f"{name} : failed = error[{error.diagnostic.code}] {error.diagnostic.message}"
        return f"{name} : failed = {error}"
    if value.state == ThunkState.EVALUATING:
        return f"{name} : evaluating"
    return f"{name} : unevaluated"


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
