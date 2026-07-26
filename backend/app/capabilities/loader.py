"""Central capability discovery and registry integrity validation."""

from __future__ import annotations

import ast
import importlib
import importlib.util
import inspect
import pkgutil
import re
import types
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from string import Formatter
from typing import (
    Annotated,
    Any,
    Iterable,
    Iterator,
    Optional,
    Union,
    get_args,
    get_origin,
)

from pydantic import BaseModel

from app.capabilities.spec import CAPABILITIES, Capability
from app.core.config import settings


_DECLARATIONS_PACKAGE = "app.capabilities.declarations"
_ROUTES_PACKAGE = "app.api.routes"
_ROUTE_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}
_EXTERNAL_ROUTE_PREFIXES = {
    "settings": "/settings",
    "webhooks": "/webhooks",
}
_PATH_PARAMETER = re.compile(r"\{[^{}]+\}")


@dataclass(frozen=True)
class RegistryValidationIssue:
    """One actionable registry integrity problem."""

    code: str
    message: str
    capability_names: tuple[str, ...] = ()
    path: Optional[str] = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "capability_names": list(self.capability_names),
            "path": self.path,
        }


@dataclass(frozen=True)
class RegistryValidationReport:
    """Structured result returned for a valid registry and attached to errors."""

    capability_count: int
    errors: tuple[RegistryValidationIssue, ...]
    destructive_agent_exceptions: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "capability_count": self.capability_count,
            "errors": [issue.as_dict() for issue in self.errors],
            "destructive_agent_exceptions": list(
                self.destructive_agent_exceptions
            ),
        }


class RegistryValidationError(ValueError):
    """Raised when one or more real registry integrity problems are found."""

    def __init__(self, report: RegistryValidationReport):
        self.report = report
        details = "; ".join(
            f"[{issue.code}] {issue.message}" for issue in report.errors
        )
        super().__init__(
            f"Capability registry validation failed with "
            f"{len(report.errors)} problem(s): {details}"
        )


def _declaration_module_names() -> list[str]:
    package = importlib.import_module(_DECLARATIONS_PACKAGE)
    return sorted(
        module.name
        for module in pkgutil.walk_packages(
            package.__path__,
            prefix=f"{_DECLARATIONS_PACKAGE}.",
        )
        if not module.ispkg
    )


def _restore_module_declarations(module: Any) -> None:
    """Restore cached declarations after a test or caller clears the registry."""

    declarations = {
        declaration.name: declaration
        for value in vars(module).values()
        if isinstance(
            declaration := getattr(value, "__capability__", None),
            Capability,
        )
    }
    for name, declaration in declarations.items():
        registered = CAPABILITIES.get(name)
        if registered is None:
            CAPABILITIES[name] = declaration
        elif registered is not declaration:
            raise ValueError(f"Duplicate capability name: {name}")


def load_all_capabilities() -> None:
    """Import every declaration module when the registry feature is enabled.

    Package walking is intentional: declarations have a single well-defined home,
    and adding a domain module there requires no central list or startup edit.
    Discovered names are sorted so import and duplicate-error order is deterministic.
    Python's module cache makes repeat calls idempotent; the restore step also makes
    test isolation safe when a caller clears ``CAPABILITIES`` between calls.
    """

    if not settings.CAPABILITY_REGISTRY_ENABLED:
        return

    for module_name in _declaration_module_names():
        module = importlib.import_module(module_name)
        _restore_module_declarations(module)


def _is_pydantic_model(model: Any) -> bool:
    try:
        return inspect.isclass(model) and issubclass(model, BaseModel)
    except TypeError:
        return False


def _is_pydantic_output_model(model: Any) -> bool:
    """Accept a Pydantic model or a typed collection/union of those models."""

    if _is_pydantic_model(model):
        return True

    origin = get_origin(model)
    arguments = get_args(model)
    if origin is Annotated:
        return bool(arguments) and _is_pydantic_output_model(arguments[0])
    if origin in {list, set, frozenset}:
        return len(arguments) == 1 and _is_pydantic_output_model(arguments[0])
    if origin is tuple:
        item_types = [argument for argument in arguments if argument is not Ellipsis]
        return bool(item_types) and all(
            _is_pydantic_output_model(argument) for argument in item_types
        )
    if origin is dict:
        return len(arguments) == 2 and _is_pydantic_output_model(arguments[1])
    if origin in {Union, types.UnionType}:
        item_types = [argument for argument in arguments if argument is not type(None)]
        return bool(item_types) and all(
            _is_pydantic_output_model(argument) for argument in item_types
        )
    return False


def _template_fields(template: str) -> Iterator[str]:
    for _, field_name, format_spec, _ in Formatter().parse(template):
        if field_name is not None:
            if not field_name:
                raise ValueError("positional replacement fields are not supported")
            yield re.split(r"[.[]", field_name, maxsplit=1)[0]
        if format_spec:
            yield from _template_fields(format_spec)


def _join_route_path(*parts: str) -> str:
    joined = "/".join(part.strip("/") for part in parts if part.strip("/"))
    return f"/{joined}" if joined else "/"


def _router_prefix(tree: ast.AST) -> str:
    for node in getattr(tree, "body", []):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(isinstance(target, ast.Name) and target.id == "router" for target in targets):
            continue
        value = node.value
        if not isinstance(value, ast.Call):
            continue
        function_name = (
            value.func.id
            if isinstance(value.func, ast.Name)
            else getattr(value.func, "attr", "")
        )
        if function_name != "APIRouter":
            continue
        for keyword in value.keywords:
            if (
                keyword.arg == "prefix"
                and isinstance(keyword.value, ast.Constant)
                and isinstance(keyword.value.value, str)
            ):
                return keyword.value.value
    return ""


def _declared_route_paths() -> set[str]:
    """Read route decorators without importing route modules or starting the app."""

    package_spec = importlib.util.find_spec(_ROUTES_PACKAGE)
    if package_spec is None or package_spec.submodule_search_locations is None:
        raise RuntimeError(f"Could not locate route package {_ROUTES_PACKAGE}")

    paths: set[str] = set()
    for package_path in package_spec.submodule_search_locations:
        for source_path in sorted(Path(package_path).glob("*.py")):
            if source_path.name == "__init__.py":
                continue
            tree = ast.parse(source_path.read_text(encoding="utf-8"), source_path)
            router_prefix = _router_prefix(tree)
            mount_prefix = _EXTERNAL_ROUTE_PREFIXES.get(source_path.stem, "")
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for decorator in node.decorator_list:
                    if not isinstance(decorator, ast.Call):
                        continue
                    function = decorator.func
                    if (
                        not isinstance(function, ast.Attribute)
                        or not isinstance(function.value, ast.Name)
                        or function.value.id != "router"
                        or function.attr not in _ROUTE_METHODS
                        or not decorator.args
                        or not isinstance(decorator.args[0], ast.Constant)
                        or not isinstance(decorator.args[0].value, str)
                    ):
                        continue
                    paths.add(
                        _join_route_path(
                            mount_prefix,
                            router_prefix,
                            decorator.args[0].value,
                        )
                    )
    return paths


def _canonical_path(path: str) -> str:
    api_prefix = settings.API_V1_STR.rstrip("/")
    if api_prefix and (path == api_prefix or path.startswith(f"{api_prefix}/")):
        path = path[len(api_prefix) :] or "/"
    normalized = _join_route_path(path)
    return _PATH_PARAMETER.sub("{}", normalized)


def _existing_route_paths(existing_routes: Optional[Iterable[Any]]) -> set[str]:
    if existing_routes is None:
        paths = _declared_route_paths()
    else:
        paths = {
            path
            for route in existing_routes
            if isinstance(path := route if isinstance(route, str) else getattr(route, "path", None), str)
        }
    return {_canonical_path(path) for path in paths}


def validate_registry(
    existing_routes: Optional[Iterable[Any]] = None,
) -> RegistryValidationReport:
    """Validate the loaded registry and raise with a structured report on errors.

    ``existing_routes`` may be supplied with mounted FastAPI route objects at
    startup. With no argument, route source declarations are inspected statically,
    which keeps unit tests and validation free of import-time application effects.
    """

    entries = list(CAPABILITIES.items())
    errors: list[RegistryValidationIssue] = []
    destructive_exceptions: set[str] = set()
    names: defaultdict[str, list[str]] = defaultdict(list)
    http_paths: defaultdict[str, list[str]] = defaultdict(list)

    for registry_key, declaration in entries:
        name = getattr(declaration, "name", registry_key)
        if isinstance(name, str):
            names[name].append(registry_key)

    for name, registry_keys in names.items():
        if len(registry_keys) > 1:
            errors.append(
                RegistryValidationIssue(
                    code="duplicate_capability_name",
                    message=(
                        f"Capability name '{name}' is registered more than once "
                        f"under keys {sorted(registry_keys)}"
                    ),
                    capability_names=(name,),
                )
            )

    for registry_key, declaration in entries:
        name_value = getattr(declaration, "name", registry_key)
        name = name_value if isinstance(name_value, str) else str(registry_key)

        input_model = getattr(declaration, "input_model", None)
        model_is_valid = _is_pydantic_model(input_model)
        if not model_is_valid:
            errors.append(
                RegistryValidationIssue(
                    code="invalid_input_model",
                    message=(
                        f"Capability '{name}' input_model is not a Pydantic "
                        "BaseModel subclass"
                    ),
                    capability_names=(name,),
                )
            )

        output_model = getattr(declaration, "output_model", None)
        if output_model is not None and not _is_pydantic_output_model(output_model):
            errors.append(
                RegistryValidationIssue(
                    code="invalid_output_model",
                    message=(
                        f"Capability '{name}' output_model is not a Pydantic "
                        "BaseModel subclass or typed collection of BaseModel "
                        "subclasses"
                    ),
                    capability_names=(name,),
                )
            )

        if not inspect.iscoroutinefunction(getattr(declaration, "handler", None)):
            errors.append(
                RegistryValidationIssue(
                    code="handler_not_async",
                    message=f"Capability '{name}' handler is not async",
                    capability_names=(name,),
                )
            )

        scopes = getattr(declaration, "scopes", None)
        if not isinstance(scopes, list) or not scopes:
            errors.append(
                RegistryValidationIssue(
                    code="empty_scopes",
                    message=f"Capability '{name}' must declare at least one scope",
                    capability_names=(name,),
                )
            )

        if (
            getattr(declaration, "danger", None) == "destructive"
            and getattr(declaration, "agent_allowed", None) is True
        ):
            destructive_exceptions.add(name)

        http = getattr(declaration, "http", None)
        if (
            isinstance(http, tuple)
            and len(http) == 2
            and isinstance(http[1], str)
        ):
            http_paths[_canonical_path(http[1])].append(name)

        if model_is_valid:
            summary_template = getattr(declaration, "summary_template", "")
            try:
                if not isinstance(summary_template, str):
                    raise ValueError("template is not a string")
                missing_fields = sorted(
                    set(_template_fields(summary_template))
                    - set(input_model.model_fields)
                )
                if missing_fields:
                    raise ValueError(
                        f"unknown input field(s): {', '.join(missing_fields)}"
                    )
            except ValueError as exc:
                errors.append(
                    RegistryValidationIssue(
                        code="invalid_summary_template",
                        message=(
                            f"Capability '{name}' has an invalid summary_template: "
                            f"{exc}"
                        ),
                        capability_names=(name,),
                    )
                )

    existing_paths = _existing_route_paths(existing_routes)
    for path, owners in http_paths.items():
        unique_owners = tuple(sorted(set(owners)))
        if len(owners) > 1:
            errors.append(
                RegistryValidationIssue(
                    code="capability_http_path_collision",
                    message=(
                        f"Capability HTTP path '{path}' is declared by "
                        f"{', '.join(unique_owners)}"
                    ),
                    capability_names=unique_owners,
                    path=path,
                )
            )
        if path in existing_paths:
            errors.append(
                RegistryValidationIssue(
                    code="existing_http_path_collision",
                    message=(
                        f"Capability HTTP path '{path}' collides with an existing "
                        "API route"
                    ),
                    capability_names=unique_owners,
                    path=path,
                )
            )

    report = RegistryValidationReport(
        capability_count=len(entries),
        errors=tuple(
            sorted(
                errors,
                key=lambda issue: (
                    issue.code,
                    issue.capability_names,
                    issue.path or "",
                    issue.message,
                ),
            )
        ),
        destructive_agent_exceptions=tuple(sorted(destructive_exceptions)),
    )
    if not report.valid:
        raise RegistryValidationError(report)
    return report
