"""Check for values typed into calculations and output instead of stored in
variables.

Two kinds of violation:

- A number typed into an expression, such as `force = 9.81 * mass` or
  `if speed > 25:`.  The number belongs in a named variable with a comment
  giving its units.  Exempt: assigning a literal to a variable (that is how it
  gets stored), keyword arguments such as `fontsize=12`, indices and slices,
  default parameter values, the second argument of `round()`, the common
  constants in `COMMON`, every number the reference itself types into an
  expression, and `allowed_literals`.  A number the reference stores in a
  variable stays a violation: inlining the reference's `g = 9.81` is the
  hardcoding this check exists to catch.
- A decimal number typed into a string, such as `print("The mean is 4.73")`,
  where the program should print the variable holding the result.  Exempt when
  the reference's own strings contain the same number.
"""

import ast
import re
import unittest

from parameterized import parameterized

from generic_grader.style._standards import Violation, is_number, run_check
from generic_grader.utils.decorators import weighted
from generic_grader.utils.options import options_to_params

COMMON = {0, 1, 2, -1, 0.5, 10, 100, 1000, 60, 3600, 24, 180, 360}
DECIMAL = re.compile(r"(?<![\w.])\d+\.\d+(?![\w.])")
HINT = (
    "Store values in named variables instead of typing them into"
    " calculations or output.  Only constants, indices, and values that do"
    " not come from the problem's data may be typed in directly."
)


def inline_numbers(source):
    """Return the numbers `source` types into expressions, with negated forms."""
    values = set()
    for node in ast.walk(source.tree):
        if is_number(node) and isinstance(node, ast.Constant):
            if not exempt(node, source.parents):
                values |= {node.value, -node.value}
    return values


def string_numbers(source):
    """Return the decimal numbers written inside `source`'s strings."""
    return {
        number
        for node in ast.walk(source.tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
        for number in DECIMAL.findall(node.value)
    }


def exempt(node, parents):
    """Whether the literal `node` sits where typing a number is acceptable."""
    child = node
    parent = parents.get(child)
    if isinstance(parent, ast.UnaryOp):
        child, parent = parent, parents.get(parent)
    # Literals inside a literal container assigned to a variable, e.g. a list.
    while isinstance(parent, (ast.Tuple, ast.List, ast.Set, ast.Dict)):
        child, parent = parent, parents.get(parent)
    if isinstance(parent, (ast.Assign, ast.AnnAssign)) and child is parent.value:
        return True
    if isinstance(parent, ast.Call) and isinstance(parent.func, ast.Name):
        if parent.func.id == "round" and child in parent.args[1:]:
            return True
    current = node
    while current in parents:
        current, above = parents[current], current
        if isinstance(current, ast.keyword):
            return True
        if isinstance(current, ast.Subscript) and above is current.slice:
            return True
        if isinstance(current, ast.arguments):
            return True
    return False


def in_format_spec(node, parents):
    current = node
    while current in parents:
        current = parents[current]
        if isinstance(current, ast.FormattedValue):
            return True
    return False


def analyze(sub, ref, options):
    allowed = COMMON | set(options.allowed_literals)
    ref_strings = set()
    if ref is not None:
        allowed |= inline_numbers(ref)
        ref_strings = string_numbers(ref)
    parents = sub.parents

    violations = []
    for node in ast.walk(sub.tree):
        if not isinstance(node, ast.Constant):
            continue
        if is_number(node):
            value = node.value
            if isinstance(parents.get(node), ast.UnaryOp):
                value = -value if isinstance(parents[node].op, ast.USub) else value
            if value in allowed or exempt(node, parents):
                continue
            violations.append(
                Violation(
                    node.lineno,
                    f"The number {ast.unparse(node)} is typed into a calculation;"
                    " store it in a named variable.",
                )
            )
        elif isinstance(node.value, str) and not in_format_spec(node, parents):
            parent = parents.get(node)
            if isinstance(parent, ast.Expr):
                continue  # a docstring or a bare string, not output
            for number in DECIMAL.findall(node.value):
                if number not in ref_strings:
                    violations.append(
                        Violation(
                            node.lineno,
                            f"The value {number} is typed into text; print the"
                            " variable that holds it.",
                        )
                    )
    return violations


def doc_func(func, num, param):
    """Return docstring when checking for hardcoded values."""
    return "Check for values typed in instead of stored in variables."


def build(the_options):
    """Create a class for hardcoding tests."""

    the_params = options_to_params(the_options)

    class TestHardcoding(unittest.TestCase):
        """A class for hardcoding tests."""

        @parameterized.expand(the_params, doc_func=doc_func)
        @weighted
        def test_hardcoding(self, options):
            """Check for values typed in instead of stored in variables."""
            run_check(self, options, analyze, 0, HINT)

    return TestHardcoding
