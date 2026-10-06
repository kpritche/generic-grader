"""Test all values in the output from a function."""

import functools
import os

from attrs import evolve

from generic_grader.utils.docs import get_wrapper
from generic_grader.utils.exceptions import RefFileNotFoundError
from generic_grader.utils.math_utils import calc_log_limit
from generic_grader.utils.user import RefUser, SubUser

text_wrapper = get_wrapper()


def reference_test(func):
    """Decorator for tests that make comparisons between files produced by a
    reference program and student submitted program.
    """

    @functools.wraps(func)
    def wrapper(self, options):
        o = options

        # Make sure the expected output files don't already exist.
        for filename in o.filenames:
            try:
                os.remove(filename)
            except FileNotFoundError:
                pass

        # Run an optional initialization function.
        if o.init:
            o.init(self, o)

        # Create the reference user.
        self.ref_user = RefUser(self, options=o)

        # Run the reference code.
        self.ref_user.call_obj()
        log_limit = calc_log_limit(self.ref_user.log)  # Get log_limit here

        # Rename reference files
        for filename in o.filenames:
            # Silent overwrite if exists.
            try:
                os.replace(filename, f"ref_{filename}")
            except FileNotFoundError:
                raise RefFileNotFoundError(filename)

        sub_o = evolve(o, log_limit=log_limit)

        # Run an optional initialization function.
        if sub_o.init:
            sub_o.init(self, sub_o)

        # Create the student user.
        self.student_user = SubUser(self, options=sub_o)

        # Run the submitted code.
        self.student_user.call_obj()

        # Rename submission files.
        for filename in o.filenames:
            message = ""
            try:
                # Silent overwrite if exists.
                os.replace(filename, f"sub_{filename}")
            except FileNotFoundError:
                call_str = o.call_str()
                self.failureException = FileNotFoundError
                message = (
                    "\n\nHint:\n"
                    + text_wrapper.fill(
                        f"The file `{filename}` was not found.  Make sure your"
                        f" `{o.obj_name}` {o.obj_noun()} creates a file named"
                        f" `{filename}` {o.call_phrase()} `{call_str}`"
                        + (o.entries and f" with entries={o.entries}." or ".")
                    )
                    + f"\n\n{self.student_user.format_log()}"
                )
            if message:
                self.fail(message)

        func(self, o)

    return wrapper
