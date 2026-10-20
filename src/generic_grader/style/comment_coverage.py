"""Check that variables, calculations and output are commented.

Two rules, from the course's programming standards:

- A variable initialized to a number needs a comment, on its line or the line
  above, that describes it and gives its units.  A variable read with
  `input()` passes when either the comment or the prompt gives its units.
- Calculations and output (assignments, calls such as `print()`, returns)
  need a comment nearby.  A block comment covers the statements under it, up to
  `WINDOW` of them, counting an `if`/`for`/`while` and everything inside it as
  one statement; an inline comment covers its own line; a function's docstring
  covers the start of the function.  Commented-out code and divider lines do
  not count as comments.

Each run of uncommented statements is one violation.
"""

import ast
import re
import unittest

from parameterized import parameterized

from generic_grader.style._standards import (
    Violation,
    is_docstring,
    is_number,
    is_prose,
    run_check,
)
from generic_grader.utils.decorators import weighted
from generic_grader.utils.options import options_to_params

WINDOW = 6  # statements one block comment covers
UNIT_WORDS = set("""
    m cm mm km um nm ft feet foot inch inches mi mile miles yd meter meters
    metre metres l ml liter liters litre litres gal gallon gallons s sec
    secs second seconds ms min mins minute minutes h hr hrs hour hours day
    days week weeks yr year years sol sols g mg kg lb lbs lbm lbf oz ton
    tons n kn newton newtons j kj joule joules cal kcal w kw mw watt watts
    kwh pa kpa mpa psi atm bar hp k c f celsius fahrenheit kelvin deg
    degree degrees rad radian radians hz khz rpm v volt volts amp amps
    ampere ohm ohms mah mph kph ppm ppb percent percentage dollar dollars
    usd cent cents unitless dimensionless count counts number index none
    ratio fraction items people students samples points pts pixels px bytes
    bits times trials steps
    """.split())
HINT = (
    "Comment your code.  Every variable initialized to a value needs a comment"
    " describing it with its units, and every calculation and display needs a"
    " descriptive comment, either inline or as a block comment above it."
)


def names_unit(text):
    """Whether `text` gives a unit, e.g. "(m/s)", "[kg]", "in seconds", "%"."""
    text = re.sub(r"'s\b", "", text)  # "the ball's span": that s is not seconds
    if re.search(r"[%$°µ]", text):
        return True
    if re.search(r"[(\[][^)\]]*[A-Za-z][^)\]]*[)\]]", text):
        return True
    if re.search(r"[A-Za-z]+\s*/\s*[A-Za-z]+", text):
        return True
    return any(word in UNIT_WORDS for word in re.findall(r"[a-z]+", text.lower()))


def input_prompt(node):
    """Return the prompt of `input(...)`, `float(input(...))` or `int(input(...))`,
    or None when `node` is not one of those.
    """
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in ("float", "int", "eval")
        and len(node.args) == 1
    ):
        node = node.args[0]
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "input"
    ):
        if node.args and isinstance(node.args[0], ast.Constant):
            return str(node.args[0].value)
        return ""
    return None


def is_numeric_literal(node):
    """Whether `node` is a number or a list/tuple of numbers."""
    if isinstance(node, (ast.List, ast.Tuple)):
        return bool(node.elts) and all(is_number(e) for e in node.elts)
    return is_number(node)


def blocks(node):
    """Return the statement lists inside a compound statement, or [] for a
    simple statement.
    """
    if isinstance(node, ast.Match):
        return [case.body for case in node.cases]
    found = [
        getattr(node, f)
        for f in ("body", "orelse", "finalbody")
        if getattr(node, f, None)
    ]
    found += [handler.body for handler in getattr(node, "handlers", [])]
    return found if isinstance(getattr(node, "body", None), list) else []


class Coverage:
    """Walk a program in source order, recording comment violations."""

    def __init__(self, sub):
        self.sub = sub
        self.comments = sub.comments
        self.violations = []
        self.run = None  # (first line, last line) of the current uncommented run

    def above(self, lineno):
        """Return the full-line comments directly above `lineno`, nearest last."""
        found, n = [], lineno - 1
        while n > 0:
            line = self.sub.lines[n - 1].strip()
            if n in self.comments and not self.comments[n][1]:
                found.insert(0, (n, self.comments[n][0]))
            elif line:
                break
            n -= 1
        return found

    def inline(self, first, last):
        return [
            self.comments[n][0]
            for n in range(first, last + 1)
            if n in self.comments and self.comments[n][1]
        ]

    def flush(self):
        if self.run is not None:
            self.violations.append(uncommented(*self.run))
            self.run = None

    def suite(self, body, covered, documented=False):
        since = 0 if documented else None  # statements since the last block comment
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                self.flush()
                # A docstring covers the start of its function like a block comment.
                self.suite(node.body, False, ast.get_docstring(node) is not None)
                self.flush()
                continue
            above = self.above(node.lineno)
            if any(is_prose(text) for _, text in above):
                since = 0
            here = covered or (since is not None and since < WINDOW)
            inner = blocks(node)
            if inner:
                here = here or any(
                    is_prose(c) for c in self.inline(node.lineno, node.lineno)
                )
                for block in inner:
                    self.suite(block, here)
            else:
                self.simple(node, here, above)
            if since is not None:
                since += 1

    def simple(self, stmt, covered, above):
        inline = self.inline(stmt.lineno, stmt.end_lineno)
        right_above = [text for n, text in above if n == stmt.lineno - 1]
        near = " ".join(inline + right_above)
        value = getattr(stmt, "value", None)
        assigns = isinstance(stmt, (ast.Assign, ast.AnnAssign)) and value is not None
        prompt = input_prompt(value) if assigns else None
        if assigns:
            target = ast.unparse(
                stmt.targets[0] if isinstance(stmt, ast.Assign) else stmt.target
            )

        if assigns and is_numeric_literal(value):
            if not names_unit(near):
                self.violations.append(
                    Violation(
                        stmt.lineno,
                        f"`{target}` is initialized without a comment giving its"
                        " description and units.",
                    )
                )
            commented = True
        elif prompt is not None:
            if not names_unit(near + " " + prompt):
                self.violations.append(
                    Violation(
                        stmt.lineno,
                        f"`{target}` is read from input without its units in a"
                        " comment or in the prompt.",
                    )
                )
            commented = True
        elif is_docstring(stmt) or is_main_call(stmt) or isinstance(stmt, NEUTRAL):
            commented = True
        elif assigns and is_literal(value):
            commented = True  # a named constant such as a file name or a color table
        else:
            commented = covered or any(is_prose(c) for c in inline)

        if commented:
            self.flush()
        elif self.run is None:
            self.run = (stmt.lineno, stmt.end_lineno)
        else:
            self.run = (self.run[0], stmt.end_lineno)


def analyze(sub, ref, options):
    coverage = Coverage(sub)
    coverage.suite(sub.tree.body, False)
    coverage.flush()
    return coverage.violations


NEUTRAL = (
    ast.Pass,
    ast.Break,
    ast.Continue,
    ast.Global,
    ast.Nonlocal,
    ast.Import,
    ast.ImportFrom,
)


def is_main_call(stmt):
    """Whether `stmt` is the template's `main()` call."""
    return (
        isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Call)
        and isinstance(stmt.value.func, ast.Name)
        and stmt.value.func.id == "main"
    )


def is_literal(node):
    try:
        ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        return False
    return True


def uncommented(first, last):
    if first == last:
        return Violation(first, "No comment explains this calculation or display.")
    return Violation(
        first, f"No comment explains the calculations or displays through line {last}."
    )


def doc_func(func, num, param):
    """Return docstring when checking comment coverage."""
    return "Check that variables, calculations and displays are commented."


def build(the_options):
    """Create a class for comment coverage tests."""

    the_params = options_to_params(the_options)

    class TestCommentCoverage(unittest.TestCase):
        """A class for comment coverage tests."""

        @parameterized.expand(the_params, doc_func=doc_func)
        @weighted
        def test_comment_coverage(self, options):
            """Check that variables, calculations and displays are commented."""
            run_check(self, options, analyze, 0, HINT)

    return TestCommentCoverage
