"""Test the execution-backend seam on `RefUser` and `SubUser`.

An options type can carry a `user_backend` class attribute naming classes
to allocate whenever `RefUser` or `SubUser` is constructed.  These tests
register a stub backend whose users never import a module, then run every
place in the package that constructs a user and check that each one built
a stub.

Each construction is recorded with the file and source line that made it,
so every site is identified by its own code rather than by a count.

Control: `test_control_without_seam_stub_is_not_reached` replaces the
`__new__` methods with a plain allocation, which restores the behaviour the
package had before the seam existed, and shows the stub is then never
constructed.  On code without the seam, every site test here fails at its
`assert expected in sites()` line, because the real users are built (and
fail to import the stub module names) instead of the stubs.
"""

import linecache
import os
import sys
import unittest

import matplotlib.pyplot as plt
import pytest
from attrs import define, evolve

from generic_grader.file import file_lines_are_random
from generic_grader.function import (
    function_not_defined,
    function_random_return_length,
    random_func_return_range,
    random_function_calls,
)
from generic_grader.image import plot_prop_matches_reference
from generic_grader.output import output_lines_are_random, output_lines_match_reference
from generic_grader.utils import turtle_canvas
from generic_grader.utils.options import Options
from generic_grader.utils.user import RefUser, SubUser

CONSTRUCTED = []


class Halt(Exception):
    """Raised by a stub to stop a site's code after construction."""


def _record(user):
    """Record the class and the construction site of a stub user."""
    # Frame 0 is `_record`, 1 the stub `__init__`, 2 the construction site.
    frame = sys._getframe(2)
    filename = frame.f_code.co_filename
    line = linecache.getline(filename, frame.f_lineno).strip()
    CONSTRUCTED.append((type(user).__name__, os.path.basename(filename), line))


class _StubMixin:
    def _stub_init(self, test, options, module):
        self.module = module
        self.test = test
        self.options = options
        self.entries = iter("")
        self.log = self.LogIO()
        self.interactions = [0]
        self.returned_values = None
        self.patches = []

    def call_obj(self):
        """Return canned output without running any code."""
        o = self.options
        for filename in o.filenames:
            with open(filename, "w") as fo:
                fo.write("canned\n")
        if o.prop:
            plt.plot([0, 1], [0, 1])
        self.log.write("canned output\n")
        self.returned_values = "ab"
        return self.returned_values


class StubRefUser(_StubMixin, RefUser):
    def __init__(self, test, options):
        self._stub_init(test, options, options.ref_module)
        _record(self)


class StubSubUser(_StubMixin, SubUser):
    def __init__(self, test, options):
        self._stub_init(test, options, options.sub_module)
        _record(self)


class StubBackend:
    RefUser = StubRefUser
    SubUser = StubSubUser


@define(kw_only=True, frozen=True)
class StubOptions(Options):
    user_backend = StubBackend  # A class attribute, not an attrs field.


# Module names that do not exist, so a real user fails to import them.
STUB_OPTIONS = StubOptions(
    ref_module="no_such_reference_module",
    sub_module="no_such_submission_module",
    obj_name="main",
    weight=1,
)


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """Run in a scratch directory with an empty construction record."""
    monkeypatch.chdir(tmp_path)
    CONSTRUCTED.clear()
    yield
    CONSTRUCTED.clear()
    plt.close("all")


def sites():
    return set(CONSTRUCTED)


def run_check(module, method, options):
    """Build a check class from `module` and run its single test method."""
    test_class = module.build(options)
    test = test_class(methodName=f"{method}_0")
    test.run(unittest.TestResult())


def test_stub_options_has_no_backend_field():
    """The backend is a class attribute, so it is not an attrs field."""
    assert "user_backend" not in {a.name for a in StubOptions.__attrs_attrs__}
    assert StubOptions.user_backend is StubBackend


def test_plain_options_allocate_base_classes():
    """Without a backend the base classes are allocated unchanged."""
    o = Options()
    assert type(RefUser.__new__(RefUser, None, o)) is RefUser
    assert type(SubUser.__new__(SubUser, None, o)) is SubUser


def test_backend_subclass_constructed_directly():
    """A subclass constructed directly is not redirected."""

    class Child(StubSubUser):
        pass

    assert type(Child(None, STUB_OPTIONS)) is Child
    assert type(SubUser(None, STUB_OPTIONS)) is StubSubUser


REF = "StubRefUser"
SUB = "StubSubUser"

# The construction sites, keyed by the check that reaches them.  Each site is
# the stub class it must build, the file, and the source line that builds it.
SITES = {
    "reference_test": [
        (REF, "reference_test.py", "self.ref_user = RefUser(self, options=o)"),
        (SUB, "reference_test.py", "self.student_user = SubUser(self, options=sub_o)"),
    ],
    "turtle_canvas": [
        (REF, "turtle_canvas.py", "self.ref_start_user = RefUser(self, ref_options)"),
        (SUB, "turtle_canvas.py", "self.student_main_user = SubUser(self, o)"),
    ],
    "output_lines_are_random": [
        (REF, "output_lines_are_random.py", "self.ref_user = RefUser(self, o)"),
        (
            SUB,
            "output_lines_are_random.py",
            "self.student_user_1 = SubUser(self, sub_o)",
        ),
        (
            SUB,
            "output_lines_are_random.py",
            "self.student_user_2 = SubUser(self, sub_o)",
        ),
    ],
    "plot_prop_matches_reference": [
        (REF, "plot_prop_matches_reference.py", "self.ref_user = RefUser(self, o)"),
        (
            SUB,
            "plot_prop_matches_reference.py",
            "self.student_user = SubUser(self, student_o)",
        ),
    ],
    "file_lines_are_random": [
        (SUB, "file_lines_are_random.py", "self.student_user_2 = SubUser(self, o)"),
    ],
}
for name in [
    "function_not_defined",
    "random_function_calls",
    "function_random_return_length",
    "random_func_return_range",
]:
    SITES[name] = [(SUB, f"{name}.py", "self.student_user = SubUser(self, o)")]

# The check runs that reach each group of sites: module, method, options.
RUNS = {
    "reference_test": (
        output_lines_match_reference,
        "test_output_lines_match_reference",
        STUB_OPTIONS,
    ),
    "output_lines_are_random": (
        output_lines_are_random,
        "test_output_lines_are_random",
        STUB_OPTIONS,
    ),
    "plot_prop_matches_reference": (
        plot_prop_matches_reference,
        "test_plot_prop_matches_reference",
        evolve(STUB_OPTIONS, prop="x limits"),
    ),
    "file_lines_are_random": (
        file_lines_are_random,
        "test_file_lines_are_random",
        evolve(STUB_OPTIONS, filenames=("out.txt",)),
    ),
    "function_not_defined": (
        function_not_defined,
        "test_function_not_defined",
        STUB_OPTIONS,
    ),
    "random_function_calls": (
        random_function_calls,
        "test_random_function_calls",
        STUB_OPTIONS,
    ),
    "function_random_return_length": (
        function_random_return_length,
        "test_return_length",
        STUB_OPTIONS,
    ),
    "random_func_return_range": (
        random_func_return_range,
        "test_random_func_return_range",
        STUB_OPTIONS,
    ),
}


def run_turtle_site(monkeypatch):
    """Call `save_sub_canvas` directly, halting before a window opens."""

    def halt(self):
        raise Halt()

    # Both users are built before the reference user is first called.
    monkeypatch.setattr(StubRefUser, "call_obj", halt)
    with pytest.raises(Halt):
        turtle_canvas.save_sub_canvas(unittest.TestCase(), STUB_OPTIONS)


def test_site_list_has_fourteen_entries():
    assert sum(len(v) for v in SITES.values()) == 14


@pytest.mark.parametrize("group", sorted(RUNS))
def test_check_sites_build_stubs(group):
    """Running the check builds a stub at each of its construction sites."""
    run_check(*RUNS[group])
    for expected in SITES[group]:
        assert expected in sites()


def test_turtle_canvas_sites_build_stubs(monkeypatch):
    run_turtle_site(monkeypatch)
    for expected in SITES["turtle_canvas"]:
        assert expected in sites()


def test_all_fourteen_sites_reached(monkeypatch):
    """Every construction site in the package builds a stub, and only those."""
    for run in RUNS.values():
        run_check(*run)
    run_turtle_site(monkeypatch)
    expected = {site for group in SITES.values() for site in group}
    assert len(expected) == 14
    assert sites() == expected


def test_control_without_seam_stub_is_not_reached(monkeypatch):
    """Control: with the seam removed, no stub is constructed.

    Replacing the `__new__` methods with a plain allocation restores the
    pre-seam behaviour, so a site builds a real user, which fails to import
    the stub module name.  This proves the site tests above can fail.
    """

    def plain_new(cls, test, options):
        return object.__new__(cls)

    monkeypatch.setattr(RefUser, "__new__", plain_new)
    monkeypatch.setattr(SubUser, "__new__", plain_new)
    run_check(
        output_lines_match_reference,
        "test_output_lines_match_reference",
        STUB_OPTIONS,
    )
    run_check(function_not_defined, "test_function_not_defined", STUB_OPTIONS)
    assert sites() == set()
    for expected in SITES["reference_test"] + SITES["function_not_defined"]:
        assert expected not in sites()
