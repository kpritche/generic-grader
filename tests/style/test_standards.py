"""Tests for the programming-standards checks: header, structure,
comment_coverage, formatting, names and hardcoding.
"""

import io
import json
import textwrap
import unittest
from pathlib import Path

import pytest
from gradescope_utils.autograder_utils.json_test_runner import JSONTestRunner

from generic_grader.style import (
    comment_coverage,
    formatting,
    hardcoding,
    header,
    names,
    structure,
)
from generic_grader.utils.options import Options

GOOD = '''\
"""
Course Number: ENGR 13100

Description:
    Compute the height of a ball thrown straight up at each second and
    report the second it lands.

Assignment Information:
    Assignment:     7.2.1 ICA_1
    Author:         Ada Lovelace, alovelace@purdue.edu
"""

import math

GRAVITY = 9.81  # gravitational acceleration (m/s^2)


def height(speed_mps, time_s):
    """Return the height (m) at time_s seconds for a launch speed in m/s."""
    # Kinematics: h = v*t - g*t^2/2
    return speed_mps * time_s - 0.5 * GRAVITY * time_s ** 2


def main():
    # Read the launch speed from the user.
    launch_speed = float(input("Enter launch speed (m/s): "))
    duration = 5  # time span to simulate (s)

    # Report the height each second until the ball lands.
    for second in range(1, duration + 1):
        current = height(launch_speed, second)
        if current <= 0:
            print(f"Landed by t = {second} s")
            break
        print(f"t = {second} s: {current:10.2f} m")

    # Peak height from the closed-form formula, rounded down.
    peak = launch_speed ** 2 / (2 * GRAVITY)
    print(f"Peak: {math.floor(peak)} m")


if __name__ == "__main__":
    main()
'''

CHECKS = {
    "header": header,
    "structure": structure,
    "comment_coverage": comment_coverage,
    "formatting": formatting,
    "names": names,
    "hardcoding": hardcoding,
}


def make_test(check, submission, reference=None, **options):
    """Write the files and return the check's bound test method."""
    Path("submission.py").write_text(textwrap.dedent(submission))
    Path("reference.py").write_text(textwrap.dedent(reference or submission))
    options = {
        "sub_module": "submission",
        "ref_module": "reference",
        "weight": 1,
        **options,
    }
    built = CHECKS[check].build(Options(**options))
    instance = built(methodName=f"test_{check}_0")
    return getattr(instance, f"test_{check}_0")


def assert_passes(test):
    test()
    assert test.__score__ == test.__weight__


def assert_fails(test, *fragments):
    with pytest.raises(AssertionError) as exc_info:
        test()
    message = " ".join(str(exc_info.value).split())
    for fragment in fragments:
        assert fragment in message
    return message


def with_main(body, top=""):
    """Return GOOD with main()'s body replaced by `body`."""
    head, rest = GOOD.split("def main():\n", 1)
    tail = rest[rest.index("\n\nif __name__") :]
    return (
        head
        + top
        + "def main():\n"
        + textwrap.indent(textwrap.dedent(body), "    ")
        + tail
    )


@pytest.mark.parametrize("check", CHECKS)
def test_build_names(check):
    built = CHECKS[check].build(Options())
    assert issubclass(built, unittest.TestCase)
    assert hasattr(built(), f"test_{check}_0")


@pytest.mark.parametrize("check", CHECKS)
def test_good_program_passes_every_check(fix_syspath, check):
    assert_passes(make_test(check, GOOD))


@pytest.mark.parametrize("check", CHECKS)
def test_syntax_error_always_fails(fix_syspath, check):
    test = make_test(check, "def main(:\n    pass\n", GOOD, max_violations=99)
    assert_fails(test, "could not be checked", "syntax error")


@pytest.mark.parametrize("check", CHECKS)
def test_missing_submission_fails(fix_syspath, check):
    test = make_test(check, GOOD)
    Path("submission.py").unlink()
    assert_fails(test, "was not found")


# Header


def test_header_missing(fix_syspath):
    source = GOOD[GOOD.index("import math") :]
    assert_fails(make_test("header", source, GOOD), "line 1:", "no program header")


@pytest.mark.parametrize(
    "old, new, fragment",
    [
        (
            "Compute the height of a ball thrown straight up at each second and\n"
            "    report the second it lands.",
            "Replace this line with a description of your program.",
            "line 4: The description is still the template's placeholder",
        ),
        (
            "Compute the height of a ball thrown straight up at each second and\n"
            "    report the second it lands.",
            "Ball height program.",
            "The description is 3 words",
        ),
        ("7.2.1 ICA_1", "#.#.#", "line 9: Fill in the Assignment field"),
        ("7.2.1 ICA_1", "A##, Problem #", "Fill in the Assignment field"),
        (
            "Ada Lovelace, alovelace@purdue.edu",
            "Name, login@purdue.edu",
            "line 10: Fill in the Author",
        ),
        (
            "    Author:         Ada Lovelace, alovelace@purdue.edu\n",
            "",
            "no Author field",
        ),
    ],
)
def test_header_fields(fix_syspath, old, new, fragment):
    assert_fails(make_test("header", GOOD.replace(old, new), GOOD), fragment)


def test_header_as_comment_block_passes(fix_syspath):
    docstring = GOOD[: GOOD.index("import math")]
    comments = "\n".join(
        "# " + line if line.strip() else "#" for line in docstring.splitlines()[1:-1]
    )
    assert_passes(make_test("header", comments + "\n\n" + GOOD[len(docstring) :], GOOD))


def test_header_function_without_docstring(fix_syspath):
    source = GOOD.replace(
        '    """Return the height (m) at time_s seconds for a launch speed in m/s."""\n',
        "",
    )
    assert_fails(
        make_test("header", source, GOOD), "line 18:", "`height()` has no docstring"
    )


def test_header_function_docstring_missing_param_and_return(fix_syspath):
    source = GOOD.replace(
        "Return the height (m) at time_s seconds for a launch speed in m/s.",
        "Height of the ball at time_s.",
    )
    assert_fails(
        make_test("header", source, GOOD),
        "does not describe `speed_mps`",
        "does not say what it returns",
    )


def test_header_param_described_by_main_word(fix_syspath):
    source = GOOD.replace("for a launch speed in m/s", "for the launch speed")
    assert_passes(make_test("header", source, GOOD))


# Structure


def test_structure_import_inside_function(fix_syspath):
    source = with_main("""\
        import random  # random numbers
        # Pick a speed.
        print(random.random())
        """)
    assert_fails(
        make_test("structure", source, GOOD), "line 25:", "not inside a function"
    )


def test_structure_import_after_code(fix_syspath):
    source = GOOD.replace("def main():", "import random\n\n\ndef main():")
    assert_fails(make_test("structure", source, GOOD), "before any code")


def test_structure_code_outside_function(fix_syspath):
    source = GOOD.replace(
        '\nif __name__ == "__main__":', 'print("debug")\n\nif __name__ == "__main__":'
    )
    assert_fails(make_test("structure", source, GOOD), "outside any function")


def test_structure_template_leftover(fix_syspath):
    source = with_main('"""Write your code here (and delete this line)."""\n')
    assert_fails(make_test("structure", source, GOOD), "instruction line is still here")


def test_structure_missing_guard(fix_syspath):
    source = GOOD[: GOOD.index("\n\nif __name__")] + "\n\n\nmain()\n"
    message = assert_fails(make_test("structure", source, GOOD), "outside any function")
    assert "if __name__" in message


def test_structure_main_not_required_when_reference_has_none(fix_syspath):
    module = 'def area(width_m):\n    """Return the area (m^2)."""\n    return width_m ** 2\n'
    assert_passes(make_test("structure", module, module))


# Comment coverage


def test_comments_stripped(fix_syspath):
    lines = [
        line.split("#")[0].rstrip() if "#" in line and 'f"' not in line else line
        for line in GOOD.splitlines()
    ]
    source = "\n".join(lines)
    assert_fails(
        make_test("comment_coverage", source, GOOD),
        "is initialized without a comment",
        "No comment explains",
    )


def test_comments_init_without_units(fix_syspath):
    source = GOOD.replace("# time span to simulate (s)", "# time span to simulate")
    assert_fails(
        make_test("comment_coverage", source, GOOD),
        "line 27:",
        "`duration` is initialized without",
    )


def test_comments_init_unit_on_line_above(fix_syspath):
    source = GOOD.replace(
        "    duration = 5  # time span to simulate (s)",
        "    # time span to simulate (s)\n    duration = 5",
    )
    assert_passes(make_test("comment_coverage", source, GOOD))


def test_comments_input_units_in_prompt_or_comment(fix_syspath):
    no_units = GOOD.replace("Enter launch speed (m/s): ", "Enter launch speed: ")
    assert_fails(
        make_test("comment_coverage", no_units, GOOD),
        "read from input without its units",
    )
    commented = no_units.replace('speed: "))', 'speed: "))  # launch speed (m/s)')
    assert_passes(make_test("comment_coverage", commented, GOOD))


def test_comments_commented_out_code_is_not_a_comment(fix_syspath):
    source = with_main('# print(debug)\nprint("a")\n')
    assert_fails(
        make_test("comment_coverage", source, GOOD), "line 26:", "No comment explains"
    )


def test_comments_window(fix_syspath):
    six = with_main("# Show the table.\n" + 'print("row")\n' * 6)
    assert_passes(make_test("comment_coverage", six, GOOD))
    seven = with_main("# Show the table.\n" + 'print("row")\n' * 7)
    assert_fails(
        make_test("comment_coverage", seven, GOOD), "line 32: No comment explains this"
    )


def test_comments_compound_statement_covered_as_one(fix_syspath):
    chain = "\n".join(
        f'{"if" if i == 0 else "elif"} launch_speed > {i}:\n    print("{i}")\n    print("{i}")'
        for i in range(5)
    )
    source = with_main(
        'launch_speed = float(input("Speed (m/s): "))\n# Classify the speed.\n'
        + chain
        + "\n"
    )
    assert_passes(make_test("comment_coverage", source, GOOD))


# Formatting


@pytest.mark.parametrize(
    "snippet, fragment",
    [
        ("total=1  # count (count)", "space on each side of `=`"),
        (
            "total = 1  # count (count)\nif total>0:\n    pass",
            "space on each side of `>`",
        ),
        ("values = [1,2]  # values (count)", "space after each comma"),
        ("total = 1; other = 2  # counts (count)", "one statement on each line"),
        ("if True: pass", "body on its own line"),
        ("if True:\n  pass", "multiple of 4 spaces"),
        ("if True:\n\tpass", "not tabs"),
        ("note = 'x'  # " + "y" * 120, "horten the line to 99"),
    ],
)
def test_formatting_rules(fix_syspath, snippet, fragment):
    source = with_main(snippet + "\n")
    assert_fails(make_test("formatting", source, GOOD, max_violations=0), fragment)


def test_formatting_keyword_equals_needs_no_space(fix_syspath):
    source = with_main('print("a", end="")\n')
    assert_passes(make_test("formatting", source, GOOD, max_violations=0))


def test_formatting_blank_line_before_def(fix_syspath):
    source = GOOD.replace("\n\ndef main():", "def main():")
    assert_fails(
        make_test("formatting", source, GOOD, max_violations=0),
        "blank line before `main`",
    )


def test_formatting_default_allows_three_lines(fix_syspath):
    three = with_main("a=1\nb=2\nc=3\n")
    assert_passes(make_test("formatting", three, GOOD))
    four = with_main("a=1\nb=2\nc=3\nd=4\n")
    assert_fails(make_test("formatting", four, GOOD), "Found 4 (3 allowed)")


# Names


def test_names_builtin(fix_syspath):
    source = with_main("sum = 0  # running total (count)\nprint(sum)\n")
    assert_fails(
        make_test("names", source, source),
        "line 25:",
        "`sum` overwrites Python's built-in",
    )


def test_names_imported_module(fix_syspath):
    source = with_main("math = 2  # factor (unitless)\nprint(math)\n")
    assert_fails(
        make_test("names", source, GOOD), "overwrites the imported module `math`"
    )


@pytest.mark.parametrize(
    "name, fragment", [("q", "single letter"), ("tmp", "does not describe")]
)
def test_names_undescriptive(fix_syspath, name, fragment):
    source = with_main(f"{name} = 0  # value (count)\nprint({name})\n")
    assert_fails(make_test("names", source, GOOD), f"`{name}`", fragment)


def test_names_allowed_by_reference_or_option(fix_syspath):
    source = with_main("v = 0  # speed (m/s)\nprint(v)\n")
    assert_passes(make_test("names", source, source))
    assert_passes(make_test("names", source, GOOD, allowed_names=("v",)))


def test_names_loop_variables_may_be_single_letters(fix_syspath):
    source = with_main("for i in range(3):\n    print([j for j in range(i)])\n")
    assert_passes(make_test("names", source, GOOD))


# Hardcoding


def test_hardcoding_number_in_calculation(fix_syspath):
    source = with_main("area = 3.14159 * 4 ** 2  # area (m^2)\nprint(area)\n")
    message = assert_fails(
        make_test("hardcoding", source, GOOD), "The number 3.14159", "line 25:"
    )
    assert "The number 4 " in message


def test_hardcoding_number_from_reference_or_option(fix_syspath):
    source = with_main("area = 3.14159 * 4 ** 2  # area (m^2)\nprint(area)\n")
    assert_passes(make_test("hardcoding", source, source))
    assert_passes(make_test("hardcoding", source, GOOD, allowed_literals=(3.14159, 4)))


def test_hardcoding_inlining_a_stored_reference_value(fix_syspath):
    """The reference stores 9.81 in GRAVITY; typing 9.81 inline still fails."""
    source = GOOD.replace("2 * GRAVITY)", "2 * 9.81)")
    assert_fails(make_test("hardcoding", source, GOOD), "The number 9.81")


def test_hardcoding_exempt_positions(fix_syspath):
    source = with_main(
        "values = [3, 7, 11]  # samples (count)\n"
        "rate = -42.5  # rate (m/s)\n"
        "# Show one sample and a rounded rate.\n"
        "print(values[7], round(rate, 3), end='\\n', sep=' ' * 4)\n"
    )
    assert_passes(make_test("hardcoding", source, GOOD))


def test_hardcoding_comparison(fix_syspath):
    source = with_main(
        'speed = 3  # speed (m/s)\n# Warn when fast.\nif speed > 25:\n    print("fast")\n'
    )
    assert_fails(make_test("hardcoding", source, GOOD), "The number 25")


def test_hardcoding_value_typed_into_output(fix_syspath):
    source = with_main('# Show the answer.\nprint("The mean is 4.73 m")\n')
    assert_fails(
        make_test("hardcoding", source, GOOD), "The value 4.73 is typed into text"
    )
    assert_passes(make_test("hardcoding", source, source))


# Scoring


def test_deduction_scores_negative_on_failure(fix_syspath):
    test = make_test(
        "names", with_main("q = 0  # x (m)\nprint(q)\n"), GOOD, weight=0, deduction=0.25
    )
    assert_fails(test, "single letter")
    assert test.__weight__ == 0
    assert test.__score__ == -0.25


def test_deduction_scores_zero_on_pass(fix_syspath):
    test = make_test("names", GOOD, weight=0, deduction=0.25)
    assert_passes(test)
    assert test.__score__ == 0


def test_deduction_in_gradescope_results(fix_syspath):
    """The JSON runner reports a failed deduction as score -d out of 0."""
    make_test("names", with_main("q = 0  # x (m)\nprint(q)\n"), GOOD)
    suite = unittest.TestSuite()
    for check, kwargs in (
        ("names", {"deduction": 0.25}),
        ("header", {"deduction": 0.25}),
    ):
        built = CHECKS[check].build(
            Options(sub_module="submission", ref_module="reference", weight=0, **kwargs)
        )
        suite.addTest(built(f"test_{check}_0"))
    stream = io.StringIO()
    JSONTestRunner(stream=stream).run(suite)
    results = json.loads(stream.getvalue())
    by_name = {t["name"].split(":")[0]: t for t in results["tests"]}
    scores = sorted((t["score"], t["max_score"]) for t in results["tests"])
    assert scores == [(-0.25, 0), (0, 0)], by_name
    assert results["score"] == -0.25
