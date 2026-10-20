"""Check that the code's formatting keeps it readable.

Flags, one violation per line:

- indentation that uses tabs or is not a multiple of 4 spaces
- an assignment or comparison operator without a space on each side (the `=`
  of a keyword argument or default value is exempt)
- a comma with no space after it
- a line longer than `max_line_length`
- two statements on one line (`;`, or a body on the same line as its `if`,
  `for`, `while` or `def`)
- a top-level `def` or `class` with no blank line above it

A few slips are allowed; `DEFAULT_LIMIT` lines may have problems before the
check fails.
"""

import ast
import tokenize
import unittest

from parameterized import parameterized

from generic_grader.style._standards import Violation, run_check
from generic_grader.utils.decorators import weighted
from generic_grader.utils.options import options_to_params

DEFAULT_LIMIT = 3
SPACED_OPS = set("= += -= *= /= //= %= **= == != < > <= >=".split())
OPENERS, CLOSERS = "([{", ")]}"
COMPOUND = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith)
COMPOUND += (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
HINT = (
    "Format the code so it is easy to read: indent with 4 spaces, put a space"
    " on each side of = and comparison operators and after each comma, keep"
    " lines short, put one statement on each line, and leave a blank line"
    " before each function definition."
)


def token_problems(sub):
    """Yield (line, problem) for each spacing and indentation problem."""
    significant = [
        t
        for t in sub.tokens
        if t.type not in (tokenize.NL, tokenize.COMMENT, tokenize.ENCODING)
    ]
    depth = 0
    for i, tok in enumerate(significant):
        if tok.type == tokenize.INDENT:
            if "\t" in tok.string:
                yield tok.start[0], "indent with spaces, not tabs"
            elif len(tok.string) % 4:
                yield tok.start[0], "indent by a multiple of 4 spaces"
            continue
        if tok.type != tokenize.OP:
            continue
        if tok.string in OPENERS:
            depth += 1
        elif tok.string in CLOSERS:
            depth = max(depth - 1, 0)
        prev = significant[i - 1] if i else None
        nxt = significant[i + 1] if i + 1 < len(significant) else None
        if tok.string in SPACED_OPS and not (tok.string == "=" and depth):
            tight_before = prev is not None and prev.end == tok.start
            tight_after = nxt is not None and nxt.start == tok.end
            if tight_before or tight_after:
                yield tok.start[0], f"put a space on each side of `{tok.string}`"
        elif tok.string == ",":
            if nxt is not None and nxt.start == tok.end and nxt.string not in CLOSERS:
                yield tok.start[0], "put a space after each comma"
        elif tok.string == ";":
            yield tok.start[0], "put one statement on each line"


def analyze(sub, ref, options):
    problems = list(token_problems(sub))

    for n, line in enumerate(sub.lines, start=1):
        if len(line) > options.max_line_length:
            problems.append(
                (
                    n,
                    f"shorten the line to {options.max_line_length} characters ({len(line)} now)",
                )
            )

    for node in ast.walk(sub.tree):
        if (
            isinstance(node, COMPOUND)
            and node.body
            and node.body[0].lineno == node.lineno
        ):
            problems.append((node.lineno, "put the body on its own line"))

    for node in sub.tree.body[1:]:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            first = min([node.lineno] + [d.lineno for d in node.decorator_list])
            above = first - 1
            while above > 0 and sub.lines[above - 1].lstrip().startswith("#"):
                above -= 1
            if above > 0 and sub.lines[above - 1].strip():
                problems.append((first, f"leave a blank line before `{node.name}`"))

    by_line = {}
    for line, problem in problems:
        by_line.setdefault(line, [])
        if problem not in by_line[line]:
            by_line[line].append(problem)
    return [
        Violation(line, "; ".join(found).capitalize() + ".")
        for line, found in by_line.items()
    ]


def doc_func(func, num, param):
    """Return docstring when checking formatting."""
    return "Check that formatting keeps the code readable."


def build(the_options):
    """Create a class for formatting tests."""

    the_params = options_to_params(the_options)

    class TestFormatting(unittest.TestCase):
        """A class for formatting tests."""

        @parameterized.expand(the_params, doc_func=doc_func)
        @weighted
        def test_formatting(self, options):
            """Check that formatting keeps the code readable."""
            run_check(self, options, analyze, DEFAULT_LIMIT, HINT)

    return TestFormatting
