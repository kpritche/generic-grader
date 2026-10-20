"""Check that variable names are acceptable.

A name fails when it overwrites one of Python's built-in names (`sum`, `max`,
`input`, `list`, ...) or a module the program imports, or when it says
nothing about its value: a single letter, or a filler word such as `tmp` or
`foo`.  Loop and comprehension variables may be single letters.  Any name the
reference solution uses is allowed, as is any name in `allowed_names`, except
that overwriting a built-in is never allowed.
"""

import ast
import builtins
import unittest

from parameterized import parameterized

from generic_grader.style._standards import Violation, run_check
from generic_grader.utils.decorators import weighted
from generic_grader.utils.options import options_to_params

BUILTIN_NAMES = {n for n in dir(builtins) if not n.startswith("_")}
FILLER = set(
    "tmp var val foo bar baz stuff thing things asdf blah dummy xxx abc"
    " my_var my_variable variable".split()
)
HINT = (
    "Choose variable names that describe the value they hold, and never reuse"
    " the name of a Python built-in (such as sum, max, min, list, input or"
    " type) or of an imported module."
)


def bindings(tree):
    """Yield (name, line, kind) for every name the program binds.

    kind is "loop" for loop and comprehension variables, "import" for
    imported names, "except" for `except ... as e`, and "var" otherwise.
    """

    def targets(node, kind):
        for sub in ast.walk(node):
            if isinstance(sub, ast.Name):
                yield sub.id, sub.lineno, kind

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                yield from targets(target, "var")
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign, ast.NamedExpr)):
            yield from targets(node.target, "var")
        elif isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
            line = getattr(node, "lineno", None) or node.target.lineno
            for name, _, kind in targets(node.target, "loop"):
                yield name, line, kind
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                if item.optional_vars is not None:
                    yield from targets(item.optional_vars, "var")
        elif isinstance(node, ast.ExceptHandler) and node.name:
            yield node.name, node.lineno, "except"
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node.name, node.lineno, "var"
            args = node.args
            for arg in args.posonlyargs + args.args + args.kwonlyargs:
                yield arg.arg, arg.lineno, "var"
            for arg in (args.vararg, args.kwarg):
                if arg is not None:
                    yield arg.arg, arg.lineno, "var"
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                name = alias.asname or alias.name.split(".")[0]
                yield name, node.lineno, "import"


def analyze(sub, ref, options):
    allowed = set(options.allowed_names)
    if ref is not None:
        allowed |= {name for name, _, _ in bindings(ref.tree)}
    found = sorted(bindings(sub.tree), key=lambda b: b[1])
    modules = {name for name, _, kind in found if kind == "import"}

    violations, reported = [], set()
    for name, line, kind in found:
        if kind == "import" or name in reported:
            continue
        if name in BUILTIN_NAMES:
            text = f"`{name}` overwrites Python's built-in `{name}`."
        elif name in modules:
            text = f"`{name}` overwrites the imported module `{name}`."
        elif (
            name in allowed
            or kind in ("loop", "except")
            or name in ("_", "self", "cls")
        ):
            continue
        elif len(name) == 1:
            text = f"`{name}` is a single letter; name it for the value it holds."
        elif name.lower() in FILLER:
            text = f"`{name}` does not describe the value it holds."
        else:
            continue
        reported.add(name)
        violations.append(Violation(line, text))
    return violations


def doc_func(func, num, param):
    """Return docstring when checking variable names."""
    return "Check that variable names are valid and descriptive."


def build(the_options):
    """Create a class for variable name tests."""

    the_params = options_to_params(the_options)

    class TestNames(unittest.TestCase):
        """A class for variable name tests."""

        @parameterized.expand(the_params, doc_func=doc_func)
        @weighted
        def test_names(self, options):
            """Check that variable names are valid and descriptive."""
            run_check(self, options, analyze, 0, HINT)

    return TestNames
