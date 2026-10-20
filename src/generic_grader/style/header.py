"""Check the program header and the help lines of each function.

The header is the template's module docstring (a comment block before the
first line of code also counts).  It must give a real
description of the program and fill in the Assignment and Author fields, with
none of the template's placeholder text left.  Every function other than
`main` needs a docstring naming each of its parameters, and saying what it
returns when it returns a value.
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

MIN_DESCRIPTION_WORDS = 8
LABEL = re.compile(r"^\s*([A-Za-z][A-Za-z ]*?)\s*:\s*(.*?)\s*$")
PLACEHOLDER = re.compile(
    r"replace this line|#(?!\d)|name,\s*login@purdue|\bX\.|\.X\b|\[.*here.*\]",
    re.IGNORECASE,
)
RETURN_WORDS = re.compile(r"\b(return|returns|output|outputs)\b", re.IGNORECASE)
HINT = (
    "Start the program with the template's header: a description of what"
    " the program does, plus the assignment and author information, with all"
    " placeholder text replaced.  Give every function other than main() a"
    " docstring that describes each input and output, with units."
)


def header_lines(sub):
    """Return [(line number, text)] for the program header: the module
    docstring, or else the comment block before the first line of code.
    """
    body = sub.tree.body
    if body and is_docstring(body[0]):
        node = body[0]
        return [
            (node.lineno + i, t) for i, t in enumerate(node.value.value.splitlines())
        ]
    first_code = body[0].lineno if body else len(sub.lines) + 1
    return [
        (n, text)
        for n, (text, inline) in sorted(sub.comments.items())
        if n < first_code and not inline
    ]


def header_fields(lines):
    """Return {label: (value, line)} for the header, with the description's
    text gathered from the lines that follow its label.
    """
    fields, current = {}, None
    for lineno, line in lines:
        match = LABEL.match(line)
        if match:
            label = match.group(1).lower()
            fields[label] = (match.group(2), lineno)
            current = label if label == "description" else None
        elif current == "description" and line.strip():
            value, start = fields["description"]
            fields["description"] = ((value + " " + line.strip()).strip(), start)
    return fields


def describes(doc, param):
    """Whether `doc` mentions `param` by name or by its main word, so that
    "the radius in meters" describes `radius_m`.
    """
    words = [param] + [w for w in param.split("_") if len(w) >= 3]
    return any(re.search(rf"\b{re.escape(w)}", doc, re.IGNORECASE) for w in words)


def returns_value(func):
    """Whether `func` itself (not a nested function) returns a value."""
    stack = list(func.body)
    while stack:
        node = stack.pop()
        if isinstance(node, ast.Return) and node.value is not None:
            return True
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            stack.extend(ast.iter_child_nodes(node))
    return False


def analyze(sub, ref, options):
    violations = []
    lines = header_lines(sub)
    if not lines:
        violations.append(
            Violation(
                1, "There is no program header (a docstring at the top of the file)."
            )
        )
    else:
        fields = header_fields(lines)
        top = lines[0][0]

        description, line = fields.get("description", ("", top))
        words = re.findall(r"[A-Za-z]+", description)
        if "description" not in fields:
            violations.append(Violation(top, "The header has no Description."))
        elif PLACEHOLDER.search(description):
            violations.append(
                Violation(line, "The description is still the template's placeholder.")
            )
        elif len(words) < MIN_DESCRIPTION_WORDS:
            violations.append(
                Violation(
                    line,
                    f"The description is {len(words)} words; describe what the"
                    " program does and how.",
                )
            )

        for label in ("assignment", "author"):
            value, line = fields.get(label, ("", top))
            if label not in fields:
                violations.append(
                    Violation(top, f"The header has no {label.title()} field.")
                )
            elif not value or PLACEHOLDER.search(value):
                violations.append(
                    Violation(line, f"Fill in the {label.title()} field.")
                )

    for func in functions(sub.tree):
        if func.name == "main":
            continue
        doc = ast.get_docstring(func) or ""
        if not doc:
            violations.append(
                Violation(
                    func.lineno,
                    f"`{func.name}()` has no docstring describing its inputs and outputs.",
                )
            )
            continue
        args = func.args
        params = [a.arg for a in args.posonlyargs + args.args + args.kwonlyargs]
        params += [a.arg for a in (args.vararg, args.kwarg) if a is not None]
        missing = [
            p for p in params if p not in ("self", "cls") and not describes(doc, p)
        ]
        if missing:
            violations.append(
                Violation(
                    func.lineno,
                    f"The docstring of `{func.name}()` does not describe"
                    f" {', '.join(f'`{p}`' for p in missing)}.",
                )
            )
        if returns_value(func) and not RETURN_WORDS.search(doc):
            violations.append(
                Violation(
                    func.lineno,
                    f"The docstring of `{func.name}()` does not say what it returns.",
                )
            )
    return violations


def doc_func(func, num, param):
    """Return docstring when checking the program header."""
    return "Check the program header and function help lines."


def build(the_options):
    """Create a class for program header tests."""

    the_params = options_to_params(the_options)

    class TestHeader(unittest.TestCase):
        """A class for program header tests."""

        @parameterized.expand(the_params, doc_func=doc_func)
        @weighted
        def test_header(self, options):
            """Check the program header and function help lines."""
            run_check(self, options, analyze, 0, HINT)

    return TestHeader
