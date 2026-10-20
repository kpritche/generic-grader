"""Check that code sits in the template's sections.

The template orders a program as: header, imports, function definitions, then
the `if __name__ == "__main__":` block that calls main().  Imports belong at
the top of the file, code belongs inside functions, and the template's
instruction lines ("... and delete this line") must be gone.  A module-level
assignment of a literal (a named constant) is allowed.  main() and the
`__main__` block are required only when the reference has them.
"""

import ast
import re
import unittest

from parameterized import parameterized

from generic_grader.style._standards import (
    Violation,
    functions,
    is_docstring,
    run_check,
)
from generic_grader.utils.decorators import weighted
from generic_grader.utils.options import options_to_params

LEFTOVER = re.compile(
    r"delete this line|write (any import statements|your code) here", re.I
)
HINT = (
    "Keep the template's layout: the header, then all imports, then function"
    ' definitions, then the `if __name__ == "__main__":` block that calls'
    " main().  Put the program's code inside main() or another function, and"
    " delete the template's instruction lines."
)


def is_main_guard(node):
    """Whether `node` is `if __name__ == "__main__":`."""
    if not isinstance(node, ast.If) or not isinstance(node.test, ast.Compare):
        return False
    sides = [node.test.left, *node.test.comparators]
    names = [s.id for s in sides if isinstance(s, ast.Name)]
    strings = [s.value for s in sides if isinstance(s, ast.Constant)]
    return names == ["__name__"] and strings == ["__main__"]


def is_constant(node):
    """Whether `node` assigns a literal value, such as `HEATER_W = 2000`."""
    if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.value is None:
        return False
    try:
        ast.literal_eval(node.value)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        return False
    return True


def defines_main(tree):
    return any(
        isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "main"
        for n in tree.body
    )


def has_guard(tree):
    return any(is_main_guard(n) for n in tree.body)


def analyze(sub, ref, options):
    violations = []
    tree = sub.tree

    for node in ast.walk(tree):
        if is_docstring(node) and LEFTOVER.search(node.value.value):
            violations.append(
                Violation(
                    node.lineno,
                    "The template's instruction line is still here; delete it.",
                )
            )

    after_code = False
    for i, node in enumerate(tree.body):
        if is_docstring(node):
            continue  # the header, or leftover template text reported above
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if after_code:
                violations.append(
                    Violation(
                        node.lineno,
                        "Imports belong at the top of the file, before any code.",
                    )
                )
            continue
        after_code = True
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            or is_main_guard(node)
            or is_constant(node)
        ):
            continue
        violations.append(
            Violation(
                node.lineno, "This code is outside any function; put it in main()."
            )
        )

    for func in functions(tree):
        for node in ast.walk(func):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                violations.append(
                    Violation(
                        node.lineno,
                        "Imports belong at the top of the file, not inside a function.",
                    )
                )

    if (ref is None or defines_main(ref.tree)) and not defines_main(tree):
        violations.append(
            Violation(1, "There is no main() function to hold the program.")
        )
    if (ref is None or has_guard(ref.tree)) and not has_guard(tree):
        violations.append(
            Violation(
                len(sub.lines),
                'The file does not end with the template\'s `if __name__ == "__main__":`'
                " block that calls main().",
            )
        )
    return violations


def doc_func(func, num, param):
    """Return docstring when checking the program structure."""
    return "Check that code is organized in the template's sections."


def build(the_options):
    """Create a class for program structure tests."""

    the_params = options_to_params(the_options)

    class TestStructure(unittest.TestCase):
        """A class for program structure tests."""

        @parameterized.expand(the_params, doc_func=doc_func)
        @weighted
        def test_structure(self, options):
            """Check that code is organized in the template's sections."""
            run_check(self, options, analyze, 0, HINT)

    return TestStructure
