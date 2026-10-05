"""Test that an options subclass can change how messages name the callable."""

import unittest

import pytest
from attrs import define

from generic_grader.output import output_lines_match_reference
from generic_grader.utils.options import Options


@define(kw_only=True, frozen=True)
class ScriptOptions(Options):
    """Options describing a script that is run rather than a called function."""

    def call_str(self) -> str:
        return self.obj_name

    def obj_noun(self) -> str:
        return "script"

    def call_phrase(self) -> str:
        return "when run as"


def test_default_wording_methods():
    o = Options(obj_name="f", args=(1,), kwargs={"b": 2})
    assert o.call_str() == "f(1, b=2)"
    assert o.obj_noun() == "function"
    assert o.call_phrase() == "when called as"


def test_wording_methods_are_not_fields():
    assert {"call_str", "obj_noun", "call_phrase"}.isdisjoint(
        a.name for a in Options.__attrs_attrs__
    )


def failure_text(fix_syspath, options_type):
    """Return the whitespace-normalized failure message and docstring."""
    fix_syspath.joinpath("ref.py").write_text('def main():\n    print("Hello")\n')
    fix_syspath.joinpath("sub.py").write_text('def main():\n    print("Bye")\n')
    o = options_type(ref_module="ref", sub_module="sub", obj_name="main", weight=1)
    test_class = output_lines_match_reference.build(o)
    test = test_class(methodName="test_output_lines_match_reference_0")
    result = unittest.TestResult()
    test.run(result)
    assert len(result.failures) == 1
    message = " ".join(result.failures[0][1].split())
    doc = test.test_output_lines_match_reference_0.__doc__
    return message, doc


@pytest.mark.parametrize(
    "options_type, phrase",
    [
        (Options, "of your `main` function when called as `main()`."),
        (ScriptOptions, "of your `main` script when run as `main`."),
    ],
)
def test_options_type_sets_failure_wording(fix_syspath, options_type, phrase):
    message, doc = failure_text(fix_syspath, options_type)
    assert phrase in message


def test_default_wording_unchanged(fix_syspath):
    message, doc = failure_text(fix_syspath, Options)
    assert "script" not in message
    assert doc == (
        "Check that the formatting of output lines 1 through the end"
        " from your `main` function when called as `main()`"
        " matches the reference formatting."
    )


def test_subclass_wording_in_docstring(fix_syspath):
    message, doc = failure_text(fix_syspath, ScriptOptions)
    assert "function" not in message
    assert "from your `main` script when run as `main`" in doc
