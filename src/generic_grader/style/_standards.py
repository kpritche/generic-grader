"""Shared parsing and scoring for the programming-standards checks.

The six checks (`header`, `structure`, `comment_coverage`, `formatting`,
`names` and `hardcoding`) each read the submission through `Source`, collect
`Violation`s, and hand them to `run_check`, which fails the test with every
violation listed by line number.  A check also reads the reference solution:
a name or number the reference uses is never a violation, so each task's
reference sets what that task allows.

A check with `weight=0` and a `deduction` scores `-deduction` when it fails and
0 when it passes, which is how the rubric's deductions reach the autograder
without changing a task's point total.
"""

import ast
import io
import os
import re
import tokenize
from dataclasses import dataclass
from functools import cached_property

from generic_grader.utils.docs import get_wrapper

SHOWN = 10  # violations listed in one failure message


@dataclass(frozen=True, order=True)
class Violation:
    line: int
    text: str

    def __str__(self):
        return f"line {self.line}: {self.text}"


def module_path(module):
    """Return the file path of `module`, e.g. "tests.reference" -> tests/reference.py."""
    return module.replace(".", os.path.sep) + ".py"


class Source:
    """A Python file parsed once: its text, AST, tokens and comments."""

    def __init__(self, path):
        self.path = path
        self.error = None
        self.tree = None
        self.tokens = []
        try:
            with tokenize.open(path) as fo:
                self.text = fo.read()
        except (OSError, SyntaxError, UnicodeDecodeError) as e:
            self.text = ""
            self.error = f"it could not be read ({e})"
        self.lines = self.text.splitlines()
        if self.error:
            return
        try:
            self.tree = ast.parse(self.text)
        except SyntaxError as e:
            self.error = f"it has a syntax error on line {e.lineno}: {e.msg}"
            return
        try:
            readline = io.StringIO(self.text).readline
            self.tokens = list(tokenize.generate_tokens(readline))
        except (tokenize.TokenError, SyntaxError) as e:
            self.error = f"it could not be tokenized ({e})"

    @classmethod
    def load(cls, module):
        """Return the parsed file for `module`, or None if there is no file."""
        path = module_path(module)
        return cls(path) if os.path.isfile(path) else None

    @cached_property
    def comments(self):
        """Map each line holding a comment to (comment text, is_inline)."""
        found, code_lines = {}, set()
        skip = (
            tokenize.NL,
            tokenize.NEWLINE,
            tokenize.INDENT,
            tokenize.DEDENT,
            tokenize.ENCODING,
            tokenize.ENDMARKER,
        )
        for tok in self.tokens:
            if tok.type == tokenize.COMMENT:
                text = tok.string.lstrip("#").strip()
                found[tok.start[0]] = (text, tok.start[0] in code_lines)
            elif tok.type not in skip:
                code_lines.update(range(tok.start[0], tok.end[0] + 1))
        return found

    @cached_property
    def parents(self):
        """Map each AST node to its parent node."""
        return {
            child: parent
            for parent in ast.walk(self.tree)
            for child in ast.iter_child_nodes(parent)
        }


def load_reference(options):
    """Return the parsed reference, or None if it is missing or unparsable."""
    ref = Source.load(options.ref_module)
    return ref if ref is not None and ref.error is None else None


def is_docstring(node):
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def functions(tree):
    """Yield every function definition in `tree`, nested ones included."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


def is_number(node):
    """Whether `node` is a numeric literal such as 5, 2.5 or -9.81."""
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        node = node.operand
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, (int, float, complex))
        and not isinstance(node.value, bool)
    )


def is_prose(text):
    """Whether a comment says something, as opposed to commented-out code
    or a divider line like "=====".
    """
    if not re.search(r"[A-Za-z]{2,}", text):
        return False
    try:
        body = ast.parse(text).body
    except SyntaxError:
        return True
    # A lone word such as "seconds" parses as a name, and it is still prose.
    return (
        len(body) == 1
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, (ast.Name, ast.Constant))
    )


def run_check(test, options, analyze, default_limit, hint):
    """Analyze the submission and pass, or fail with each violation listed.

    `analyze(sub, ref, options)` returns a list of `Violation`s.  The test
    fails when there are more than `options.max_violations` of them (or
    `default_limit` when that is None).  A submission that cannot be read or
    parsed always fails.
    """
    limit = default_limit if options.max_violations is None else options.max_violations
    sub = Source.load(options.sub_module)
    if sub is None:
        violations = [
            Violation(0, f"`{module_path(options.sub_module)}` was not found.")
        ]
        limit = 0
    elif sub.error:
        violations = [Violation(0, f"The program could not be checked: {sub.error}.")]
        limit = 0
    else:
        violations = analyze(sub, load_reference(options), options)

    violations = sorted(set(violations))
    if len(violations) > limit:
        if options.deduction:
            test.set_score(test, -abs(options.deduction))
        listed = "\n".join(f"  {v}" for v in violations[:SHOWN])
        if len(violations) > SHOWN:
            listed += f"\n  ... and {len(violations) - SHOWN} more"
        allowed = f" ({limit} allowed)" if limit else ""
        message = (
            "\n\nHint:\n"
            + get_wrapper().fill(hint)
            + f"\n\nFound {len(violations)}{allowed}:\n"
            + listed
        )
        test.fail(message)
    test.set_score(test, options.weight)
