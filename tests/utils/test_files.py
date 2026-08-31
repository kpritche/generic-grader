import pytest

from generic_grader.utils.files import (
    case_insensitive_pattern,
    describe_submitted_files,
    glob_ci,
    missing_file_message,
    submitted_file_names,
)


pattern_cases = [
    ("abc", "[aA][bB][cC]"),
    ("a1_b", "[aA]1_[bB]"),
    ("foo*.py", "[fF][oO][oO]*.[pP][yY]"),
    ("dir/Sub*.XLSX", "[dD][iI][rR]/[sS][uU][bB]*.[xX][lL][sS][xX]"),
    # Character classes pass through untouched.
    ("f[ao]o", "[fF][ao][oO]"),
    ("f[!a]o", "[fF][!a][oO]"),
    ("f[]]o", "[fF][]][oO]"),
    # Digits, punctuation, and question marks are unchanged.
    ("3.1.2_?", "3.1.2_?"),
    ("", ""),
]


@pytest.mark.parametrize("pattern, expected", pattern_cases)
def test_case_insensitive_pattern(pattern, expected):
    assert case_insensitive_pattern(pattern) == expected


def test_glob_ci_matches_regardless_of_case(fix_syspath):
    (fix_syspath / "3.1.2_powerData_login.xlsx").write_text("")

    assert glob_ci("3.1.2_powerdata*.xlsx") == ["3.1.2_powerData_login.xlsx"]
    assert glob_ci("3.1.2_POWERDATA*.XLSX") == ["3.1.2_powerData_login.xlsx"]


def test_glob_ci_returns_sorted_unique_matches(fix_syspath):
    (fix_syspath / "report_b.xlsx").write_text("")
    (fix_syspath / "report_A.xlsx").write_text("")

    assert glob_ci("report*.xlsx") == ["report_A.xlsx", "report_b.xlsx"]


def test_glob_ci_no_match(fix_syspath):
    assert glob_ci("nothing*.xlsx") == []


def test_submitted_file_names_skips_dot_files_and_symlinks(fix_syspath):
    (fix_syspath / "report.pdf").write_text("")
    (fix_syspath / "data.xlsx").write_text("")
    (fix_syspath / ".hidden").write_text("")
    (fix_syspath / "subdir").mkdir()
    (fix_syspath / "link.xlsx").symlink_to(fix_syspath / "data.xlsx")

    assert submitted_file_names("pattern*.xlsx") == ["data.xlsx", "report.pdf"]


def test_describe_submitted_files_lists_names(fix_syspath):
    (fix_syspath / "report.pdf").write_text("")

    description = describe_submitted_files("wanted*.xlsx")
    assert "`report.pdf`" in description


def test_describe_submitted_files_with_no_files(fix_syspath):
    assert "does not appear to contain any files" in describe_submitted_files(
        "wanted*.xlsx"
    )


def test_describe_submitted_files_counts_the_remainder(fix_syspath):
    for index in range(25):
        (fix_syspath / f"file_{index:02d}.txt").write_text("")

    description = describe_submitted_files("wanted*.xlsx")
    assert "and 5 more" in description


def test_missing_file_message_names_pattern_files_and_mistakes(fix_syspath):
    (fix_syspath / "lab_report.pdf").write_text("")

    message = missing_file_message("3.1.2_powerdata_*.xlsx")
    assert 'matching the pattern "3.1.2_powerdata_*.xlsx"' in message
    assert "`lab_report.pdf`" in message
    assert "for a different assignment" in message
    assert ".xlsx.xlsx" in message


def test_submitted_file_names_hides_grader_infrastructure(fix_syspath):
    """The listing reports the student's files, not the grader's own.

    On Gradescope the grader is unpacked into the same directory as the
    submission, so a bare listing reports run_autograder and setup.sh
    back to the student as files they uploaded.
    """

    for name in ("run_autograder", "run_tests.py", "post.py", "setup.sh"):
        (fix_syspath / name).write_text("")
    (fix_syspath / "test_config.py").write_text("")
    for name in ("tests", "results", "__pycache__"):
        (fix_syspath / name).mkdir()
    (fix_syspath / ".gitignore").write_text("")

    (fix_syspath / "3.1.2_powerData_login.xlsx").write_text("")
    (fix_syspath / "lab_report.pdf").write_text("")

    assert submitted_file_names("wanted*.xlsx") == [
        "3.1.2_powerData_login.xlsx",
        "lab_report.pdf",
    ]


def test_missing_file_hint_hides_grader_infrastructure(fix_syspath):
    """The hint a student reads names only the student's own files."""

    for name in ("run_autograder", "run_tests.py", "post.py", "setup.sh"):
        (fix_syspath / name).write_text("")
    (fix_syspath / "lab_report.pdf").write_text("")

    message = missing_file_message("3.1.2_powerdata_*.xlsx")
    assert "`lab_report.pdf`" in message
    assert "run_autograder" not in message
    assert "setup.sh" not in message
    assert "post.py" not in message
