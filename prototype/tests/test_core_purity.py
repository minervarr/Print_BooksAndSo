"""core/ imports nothing but the standard library, and this is what says so.

CLAUDE.md claims the boundary; without this test that claim decays the first
time someone reaches for pikepdf "just to read the page size". The C++ side
enforces the same rule structurally -- no core test target may list a backend
source -- which is visible in one CMake file.

Implemented with ast rather than by importing: a module that violates the rule
would import its dependency as a side effect of being checked, and on a machine
where that dependency happens to be installed the test would pass.
"""

import ast
import pathlib
import sys

CORE = pathlib.Path(__file__).resolve().parent.parent / "core"


def _imported_modules(path: pathlib.Path) -> set[str]:
    """Top-level module names imported anywhere in one source file."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # a relative import is always a sibling
                continue
            if node.module:
                names.add(node.module.split(".")[0])
    return names


def test_core_has_sources_to_check():
    # Guards against the whole suite passing because the glob found nothing.
    assert sorted(p.name for p in CORE.glob("*.py")) != []


def test_core_imports_only_stdlib_and_itself():
    allowed = set(sys.stdlib_module_names) | {"core"}
    offenders: dict[str, set[str]] = {}

    for source in sorted(CORE.glob("*.py")):
        extra = _imported_modules(source) - allowed
        if extra:
            offenders[source.name] = extra

    assert not offenders, (
        "core/ must import only the standard library. A PDF library, a font "
        f"library or a subprocess belongs in backend/. Offenders: {offenders}"
    )
