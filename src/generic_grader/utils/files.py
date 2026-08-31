"""Case-insensitive file matching and submission-file feedback.

Students rename a template file by hand, and the case they type is not
the case the pattern expects.  A template shipped as
``3.1.2_powerData_template.xlsx`` becomes ``3.1.2_powerData_login.xlsx``
when the student follows the instructions literally, which a
case-sensitive glob for ``3.1.2_powerdata*.xlsx`` does not match.  The
submission then scores zero on every check with no usable explanation.

Every consumer of a required-files pattern matches through
``glob_ci`` so the case a student types never decides the grade, and
reports a missing file through ``missing_file_message`` so the feedback
names what the submission actually contained.
"""

import glob
from pathlib import Path

# Listing every file in a large submission buries the useful part of the
# message, so the report stops here and counts the rest.
MAX_LISTED_FILES = 20


def case_insensitive_pattern(pattern: str) -> str:
    """Return *pattern* rewritten so its letters match in either case.

    Each letter becomes a two-character class (``a`` -> ``[aA]``).  Text
    already inside a character class is left alone, as are the glob
    metacharacters themselves, so the rewritten pattern keeps the
    meaning of the original.
    """

    result = []
    index = 0
    length = len(pattern)

    while index < length:
        char = pattern[index]

        if char == "[":
            # Copy the whole class through untouched.  A "!" directly
            # after the bracket negates the class, and a "]" in the
            # first position is a literal, so neither closes it.
            close = index + 1
            if close < length and pattern[close] == "!":
                close += 1
            if close < length and pattern[close] == "]":
                close += 1
            while close < length and pattern[close] != "]":
                close += 1
            result.append(pattern[index : close + 1])
            index = close + 1
            continue

        if char.isalpha() and char.lower() != char.upper():
            result.append(f"[{char.lower()}{char.upper()}]")
        else:
            result.append(char)
        index += 1

    return "".join(result)


def glob_ci(pattern: str) -> list[str]:
    """Return the paths matching *pattern*, ignoring the case of letters.

    Results are deduplicated and sorted so the order does not depend on
    the order the filesystem happens to report entries in.
    """

    matches = glob.glob(case_insensitive_pattern(pattern))
    return sorted(dict.fromkeys(matches))


def submitted_file_names(pattern: str = "") -> list[str]:
    """Return the names of the files sitting next to where *pattern* looks.

    Symlinks are skipped because the grader creates them itself, and so
    are dot files, which no student uploads on purpose.
    """

    directory = Path(pattern).parent if pattern else Path(".")
    try:
        entries = list(directory.iterdir())
    except OSError:
        return []

    names = [
        entry.name
        for entry in entries
        if entry.is_file() and not entry.is_symlink() and not entry.name.startswith(".")
    ]
    return sorted(names)


def describe_submitted_files(pattern: str = "") -> str:
    """Summarize the files a submission contains, for student feedback."""

    names = submitted_file_names(pattern)
    if not names:
        return "Your submission does not appear to contain any files."

    listed = names[:MAX_LISTED_FILES]
    quoted = ", ".join(f"`{name}`" for name in listed)
    remainder = len(names) - len(listed)
    if remainder:
        quoted += f", and {remainder} more"
    plural = "files" if len(names) > 1 else "file"
    return f"The {plural} in your submission: {quoted}."


# The four mistakes that actually produce a missing required file, in the
# order they show up in practice.
COMMON_MISTAKES = (
    "Check that you uploaded the file for this assignment and not one"
    " for a different assignment, that you did not upload your report"
    " in place of the workbook, that the name does not carry a doubled"
    " extension such as .xlsx.xlsx, and that the extension is present"
    " at all."
)


def missing_file_message(pattern: str) -> str:
    """Return the feedback for a required file that could not be found."""

    return (
        f'Cannot find any files matching the pattern "{pattern}".'
        f"  {describe_submitted_files(pattern)}"
        "  Make sure that you have included a file with a name matching"
        " this pattern in your submission."
        f"  {COMMON_MISTAKES}"
    )
