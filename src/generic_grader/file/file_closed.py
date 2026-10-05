"""Test that all files are closed."""

import functools
import unittest
import warnings

from parameterized import parameterized

from generic_grader.utils.decorators import weighted
from generic_grader.utils.docs import get_wrapper, oxford_list
from generic_grader.utils.options import options_to_params
from generic_grader.utils.reference_test import reference_test


def doc_func(func, num, param):
    """Return parameterized docstring when checking that opened files have been
    closed."""
    o = param.args[0]

    call_str = o.call_str()
    docstring = f"Check that all files are closed after calling `{call_str}`" + (
        o.entries and f" with entries={o.entries}." or "."
    )

    return docstring


def catch_warnings(func):
    """Decorator to add warning tracking."""

    @functools.wraps(func)
    def wrapper(self, options):
        with warnings.catch_warnings(record=True) as self.warning_list:
            # Don't suppress any warnings
            warnings.simplefilter("always")

            func(self, options)

    return wrapper


def build(the_options):
    """Create a class for file closing tests."""

    the_params = options_to_params(the_options)

    class TestFileClosed(unittest.TestCase):
        """A class for file closing tests."""

        wrapper = get_wrapper()

        @parameterized.expand(the_params, doc_func=doc_func)
        @weighted
        @catch_warnings
        @reference_test
        def test_file_closed(self, options):
            """Catch warnings from a reference test and then fail if a
            ResouceWarning is raised.
            """
            o = options

            # Build a list of unclosed files (ResourceWarnings).
            unclosed_files = []
            for warning in self.warning_list:
                if issubclass(warning.category, ResourceWarning):
                    unclosed_files.append(f"`{warning.source.name}`")

            file_list_str = "file " if len(unclosed_files) == 1 else "files "
            file_list_str += oxford_list(unclosed_files)
            call_str = o.call_str()
            message = (
                "\n\nHint:\n"
                + self.wrapper.fill(
                    f"Your `{o.obj_name}` {o.obj_noun()} failed to close the"
                    f" {file_list_str} {o.call_phrase()} `{call_str}`"
                    + (f" with entries={o.entries}." if o.entries else ".")
                    + (o.hint if o.hint else "")
                )
                + self.student_user.format_log()
            )

            self.assertEqual(len(unclosed_files), 0, message)

            self.set_score(self, options.weight)

    return TestFileClosed
