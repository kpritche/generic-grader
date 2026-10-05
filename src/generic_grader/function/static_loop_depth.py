"""Test the loop depth of a function."""

import ast
import unittest

from parameterized import parameterized

from generic_grader.utils.decorators import weighted
from generic_grader.utils.options import options_to_params
from generic_grader.utils.static import LoopDepthTracker


def doc_func(func, num, param):
    """Return parameterized docstring when checking loop depth."""

    o = param.args[0]

    call_str = o.call_str()
    docstring = (
        f"Check that the loop depth"
        f" in your `{o.obj_name}` {o.obj_noun()} {o.call_phrase()} `{call_str}`"
        + (o.entries and f" with entries={o.entries}" or "")
        + " meets the minimum requirements."
    )

    return docstring


def build(the_options):
    the_params = options_to_params(the_options)

    class TestStaticLoopDepth(unittest.TestCase):
        """A class for static loop depth tests."""

        @parameterized.expand(the_params, doc_func=doc_func)
        @weighted
        def test_static_loop_depth(self, options):
            o = options

            """Check that loop depth meets requirements."""

            with open(o.sub_module + ".py") as fo:
                self.tree = ast.parse(fo.read())

            self.depth_tracker = LoopDepthTracker()
            self.depth_tracker.visit(self.tree)

            actual = self.depth_tracker.max_depth
            expected = o.expected_minimum_depth

            if expected > 1:
                message = str(
                    "\nThis assignment requires the use of nested loops,"
                    f" but your `{o.obj_name}` {o.obj_noun()}'s maximum loop depth"
                    f" of {actual}, does not meet the assignment's"
                    f" minimum loop depth requirement of {expected}."
                    + (o.hint and f" {o.hint}" or ""),
                )
            else:
                message = str(
                    "\nThis assignment requires the use of at least one loop,"
                    f" but your `{o.obj_name}` {o.obj_noun()} doesn't have any loops."
                    + (o.hint and f" {o.hint}" or ""),
                )

            self.assertGreaterEqual(actual, expected, msg=message)

            self.set_score(self, o.weight)  # Full credit

    return TestStaticLoopDepth
