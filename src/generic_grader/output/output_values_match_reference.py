"""Test all values in the output from a function."""

import unittest

from parameterized import parameterized

from generic_grader.utils.decorators import weighted
from generic_grader.utils.docs import get_wrapper, ordinalize
from generic_grader.utils.options import options_to_params
from generic_grader.utils.reference_test import reference_test
from generic_grader.utils.safe_equal import safe_assert_equal


def doc_func(func, num, param):
    """Return parameterized docstring when checking output values."""

    o = param.args[0]

    call_str = o.call_str()

    nth_value_string = f"{ordinalize(o.value_n)} value" if o.value_n else "values"

    docstring = (
        f"Check that the {nth_value_string} on output line {o.line_n}"
        + f" from your `{o.obj_name}` {o.obj_noun()} {o.call_phrase()} `{call_str}`"
        + (o.entries and f" with entries={o.entries}" or "")
        + " match the reference values."
    )

    return docstring


def build(the_options):
    """Create a class for output value tests."""

    the_params = options_to_params(the_options)

    class TestOutputValuesMatchReference(unittest.TestCase):
        """A class for formatting tests."""

        wrapper = get_wrapper()

        @parameterized.expand(the_params, doc_func=doc_func)
        @weighted
        @reference_test
        def test_output_values_match_reference(self, options):
            """Compare values in the output to reference values."""

            o = options

            line_nth = ordinalize(o.line_n)
            call_str = o.call_str()

            # Get the actual and expected values
            actual = (
                self.student_user.get_value()
                if o.value_n
                else self.student_user.get_values()
            )
            expected = (
                self.ref_user.get_value() if o.value_n else self.ref_user.get_values()
            )

            value_string = f"{ordinalize(o.value_n)} value" if o.value_n else "values"

            message = (
                "\n\nHint:\n"
                + self.wrapper.fill(
                    "Your output values did not match the expected values."
                    + f"  Double check the {value_string} in the {line_nth} output line"
                    + f" of your `{o.obj_name}` {o.obj_noun()} {o.call_phrase()} `{call_str}`"
                    + (o.entries and f" with entries={o.entries}." or ".")
                    + (o.hint and f"  {o.hint}")
                )
                + f"{self.student_user.format_log()}"
            )

            safe_assert_equal(self, actual, expected, msg=message)

            self.set_score(self, o.weight)  # Full credit

    return TestOutputValuesMatchReference
