from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from . import nodes as ast
from .diagnostics import Diagnostic, DiagnosticError, Label, SourceMap, SourceSpan
from .evaluator import Env, eval_module_into, initial_env
from .parser import parse_source
from .typechecker import ANY, TypeEnv, check_module_into, initial_type_env
from .messages import t


EXTERNAL_IMPORT_PREFIXES = ("java.", "javax.", "kotlin.", "std.")


class ModuleLoadError(DiagnosticError):
    def __init__(
        self,
        message: str,
        code: str,
        span: SourceSpan | None = None,
        label: str | None = None,
        hints: list[str] | None = None,
    ):
        super().__init__(
            Diagnostic(
                code=code,
                severity="error",
                message=message,
                primary=Label(span, label) if span is not None else None,
                hints=hints or [],
            )
        )


@dataclass(frozen=True)
class LoadedModule:
    path: Path
    import_path: str | None
    module: ast.ModuleFile
    source: str


@dataclass(frozen=True)
class LoadedProgram:
    entry_path: Path
    modules: list[LoadedModule]


def is_external_import(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in EXTERNAL_IMPORT_PREFIXES)


def load_program(
    entry_file: str | Path,
    module_paths: Iterable[str | Path] = (),
    source_map: SourceMap | None = None,
) -> LoadedProgram:
    entry_path = Path(entry_file).resolve()
    search_roots = _search_roots(entry_path, module_paths)
    loaded_by_path: dict[Path, LoadedModule] = {}
    visiting: list[Path] = []
    ordered: list[LoadedModule] = []

    def visit(path: Path, import_path: str | None, import_span: SourceSpan | None = None) -> LoadedModule:
        path = path.resolve()
        if path in loaded_by_path:
            return loaded_by_path[path]
        if path in visiting:
            cycle = " -> ".join([_display_path(item) for item in visiting[visiting.index(path) :]] + [_display_path(path)])
            raise ModuleLoadError(
                t("mod.cyclic-import", cycle=cycle),
                "MOD0002",
                import_span,
                t("label.cyclic-import"),
            )

        visiting.append(path)
        source = _read_source(path, import_span)
        if source_map is not None:
            source_map.add(str(path), source)
        module = parse_source(source, str(path))

        if import_path is not None and module.module_name is not None and module.module_name != import_path:
            raise ModuleLoadError(
                t("mod.declaration-mismatch", expected=import_path, got=module.module_name),
                "MOD0003",
                module.span or import_span,
                t("label.declaration-mismatch"),
                [t("hint.declaration-mismatch", expected=import_path, got=module.module_name)],
            )

        for import_decl in module.imports:
            if is_external_import(import_decl.path):
                continue
            resolved = resolve_module_path(import_decl.path, search_roots)
            if resolved is None:
                raise ModuleLoadError(
                    t("mod.not-found", path=import_decl.path),
                    "MOD0001",
                    import_decl.span,
                    t("label.module-not-found"),
                    [t("hint.module-searched", roots=", ".join(str(root) for root in search_roots))],
                )
            visit(resolved, import_decl.path, import_decl.span)

        visiting.pop()
        loaded = LoadedModule(path, import_path, module, source)
        loaded_by_path[path] = loaded
        ordered.append(loaded)
        return loaded

    visit(entry_path, None)
    return LoadedProgram(entry_path, ordered)


def resolve_module_path(import_path: str, search_roots: Iterable[Path]) -> Path | None:
    relative = Path(*import_path.split(".")).with_suffix(".lune")
    for root in search_roots:
        candidate = (root / relative).resolve()
        if candidate.is_file():
            return candidate
    return None


def check_file(
    entry_file: str | Path,
    module_paths: Iterable[str | Path] = (),
    source_map: SourceMap | None = None,
) -> TypeEnv:
    program = load_program(entry_file, module_paths, source_map)
    env = initial_type_env()
    for loaded in program.modules:
        _define_external_imports(loaded.module, env)
        check_module_into(loaded.module, env, process_imports=False)
    return env


def eval_file(
    entry_file: str | Path,
    module_paths: Iterable[str | Path] = (),
    source_map: SourceMap | None = None,
) -> Env:
    program = load_program(entry_file, module_paths, source_map)
    env = initial_env()
    for loaded in program.modules:
        eval_module_into(loaded.module, env)
    return env


def _search_roots(entry_path: Path, module_paths: Iterable[str | Path]) -> list[Path]:
    roots = [entry_path.parent.resolve(), Path.cwd().resolve()]
    roots.extend(Path(path).resolve() for path in module_paths)
    unique: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if root not in seen:
            unique.append(root)
            seen.add(root)
    return unique


def _read_source(path: Path, span: SourceSpan | None) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ModuleLoadError(
            t("mod.unreadable", path=path),
            "MOD0001",
            span,
            t("label.module-unreadable"),
        ) from exc


def _define_external_imports(module: ast.ModuleFile, env: TypeEnv) -> None:
    for import_decl in module.imports:
        if is_external_import(import_decl.path):
            imported_name = import_decl.alias or import_decl.path.rsplit(".", 1)[-1]
            env.define_value(imported_name, ANY)


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)
