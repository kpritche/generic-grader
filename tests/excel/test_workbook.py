"""Unit tests for the shared excel/_workbook.py helpers."""

import zipfile

import pytest
from openpyxl import Workbook
from openpyxl.worksheet.formula import ArrayFormula

from generic_grader.excel._workbook import (
    extract_chart_info_from_workbook,
    get_formula_text,
    is_formula_value,
    load_sheet,
    resolve_module_workbook,
    resolve_submission_file,
)
from generic_grader.utils.options import Options


def test_ordinary_string_formula_is_a_formula():
    assert is_formula_value("=A1+B1") is True
    assert get_formula_text("=A1+B1") == "=A1+B1"


def test_array_formula_with_text_is_a_formula():
    value = ArrayFormula("A1", "=MODE.MULT(B1:B10)")
    assert is_formula_value(value) is True
    assert get_formula_text(value) == "=MODE.MULT(B1:B10)"


def test_array_formula_with_no_text_is_still_a_formula():
    """openpyxl's ArrayFormula.__init__ defaults text=None (e.g. for
    non-anchor cells of a multi-cell array range). is_formula_value must
    still report True -- an array formula with no text of its own is not
    the same thing as "not a formula", and misreading it that way is the
    exact bug class this module fixes."""
    value = ArrayFormula("A1")
    assert value.text is None
    assert is_formula_value(value) is True
    assert get_formula_text(value) is None


def test_plain_value_is_not_a_formula():
    assert is_formula_value(42) is False
    assert get_formula_text(42) is None


def test_none_is_not_a_formula():
    assert is_formula_value(None) is False
    assert get_formula_text(None) is None


def test_plain_string_starting_with_something_else_is_not_a_formula():
    assert is_formula_value("hello") is False
    assert get_formula_text("hello") is None


# ---------------------------------------------------------------------------
# File resolution: case-insensitive matching and plain-language failures
# ---------------------------------------------------------------------------


def _write_workbook(path, sheet_name="Sheet1"):
    workbook = Workbook()
    workbook.active.title = sheet_name
    workbook.active["A1"] = 1
    workbook.save(path)


def test_resolve_submission_file_ignores_case(fix_syspath):
    """A template renamed with its original capitals still resolves."""

    _write_workbook(fix_syspath / "3.1.2_powerData_login.xlsx")

    options = Options(required_files=("3.1.2_powerdata*.xlsx",))
    assert resolve_submission_file(options) == "3.1.2_powerData_login.xlsx"


def test_resolve_module_workbook_ignores_case(fix_syspath):
    """A workbook saved with an upper-case extension still resolves."""

    _write_workbook(fix_syspath / "Submission.XLSX")

    assert resolve_module_workbook("submission", "submission") == "Submission.XLSX"


def test_resolve_submission_file_missing_names_received_files(fix_syspath):
    """A missing workbook fails with a hint, not a bare FileNotFoundError."""

    (fix_syspath / "lab_report.pdf").write_text("")

    options = Options(required_files=("3.1.2_powerdata*.xlsx",))
    with pytest.raises(AssertionError) as exc_info:
        resolve_submission_file(options)

    message = " ".join(str(exc_info.value).split())
    assert "`lab_report.pdf`" in message
    assert "for a different assignment" in message


def test_load_sheet_rejects_an_xls_upload(fix_syspath):
    """An .xls upload gets plain language, not "File is not a zip file"."""

    path = fix_syspath / "submission.xls"
    path.write_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1not really an xls")

    with pytest.raises(AssertionError) as exc_info:
        load_sheet(str(path), "Sheet1", data_only=True)

    message = " ".join(str(exc_info.value).split())
    assert "could not be opened as an Excel workbook" in message
    assert ".xlsx workbook" in message
    assert "zip file" not in message


def test_load_sheet_rejects_a_renamed_pdf(fix_syspath):
    """A PDF renamed to .xlsx gets the same plain-language failure."""

    path = fix_syspath / "submission.xlsx"
    path.write_bytes(b"%PDF-1.7\nnot a workbook at all\n")

    with pytest.raises(AssertionError) as exc_info:
        load_sheet(str(path), "Sheet1", data_only=True)

    assert "could not be opened as an Excel workbook" in " ".join(
        str(exc_info.value).split()
    )


def test_extract_chart_info_rejects_a_non_workbook(fix_syspath):
    """The chart extractor reports a non-workbook the same way."""

    path = fix_syspath / "submission.xlsx"
    path.write_bytes(b"%PDF-1.7\nnot a workbook at all\n")

    with pytest.raises(AssertionError) as exc_info:
        extract_chart_info_from_workbook(str(path), sheet="Sheet1")

    assert "could not be opened as an Excel workbook" in " ".join(
        str(exc_info.value).split()
    )


def test_extract_chart_info_rejects_a_zip_that_is_not_a_workbook(fix_syspath):
    """A zip archive that carries no workbook part is not a workbook."""

    path = fix_syspath / "submission.xlsx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("hello.txt", "not a workbook")

    with pytest.raises(AssertionError) as exc_info:
        extract_chart_info_from_workbook(str(path), sheet="Sheet1")

    assert "could not be opened as an Excel workbook" in " ".join(
        str(exc_info.value).split()
    )
