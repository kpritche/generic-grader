import unittest

import pytest
from openpyxl import Workbook
from openpyxl.worksheet.formula import ArrayFormula

from generic_grader.excel._workbook import formulas_lack_cached_values
from generic_grader.excel.data_series_match_reference import build
from generic_grader.utils.options import Options


def write_workbook(path, sheet_name="Sheet1", cells=None):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = sheet_name
    for cell, value in (cells or {}).items():
        worksheet[cell] = value
    workbook.save(path)


@pytest.fixture()
def built_class():
    return build(
        Options(
            required_files=("submission.xlsx",),
            entries=("A2", "A5"),
            kwargs={"reference_file": "reference.xlsx"},
        )
    )


@pytest.fixture()
def built_instance(built_class):
    return built_class()


def test_build_class(built_class):
    assert issubclass(built_class, unittest.TestCase)


def test_build_class_name(built_class):
    assert built_class.__name__ == "TestDataSeriesMatchReference"


def test_instance_has_test_method(built_instance):
    assert hasattr(built_instance, "test_data_series_match_reference_0")


def test_doc_func_same_range_default(built_instance):
    # Relocation is on by default, so the title must not promise a
    # same-cell requirement.
    assert (
        built_instance.test_data_series_match_reference_0.__doc__
        == "Check that the data series in range A2:A5 on sheet `<first worksheet>` exactly matches the reference values."
    )


def test_doc_func_same_range_strict():
    built_class = build(
        Options(
            required_files=("submission.xlsx",),
            entries=("A2", "A5"),
            series_allow_relocation=False,
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class()

    assert (
        built_instance.test_data_series_match_reference_0.__doc__
        == "Check that the data series in range A2:A5 on sheet `<first worksheet>` exactly matches the reference values at the same cell locations."
    )


def test_doc_func_search_mode():
    built_class = build(
        Options(
            required_files=("submission.xlsx",),
            entries=("A2", "A5"),
            range_matches_reference=False,
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class()

    assert (
        built_instance.test_data_series_match_reference_0.__doc__
        == "Check that the data series in range A2:A5 on sheet `<first worksheet>` exactly matches somewhere in the submission workbook."
    )


def test_passing_same_range_case(fix_syspath):
    write_workbook(
        fix_syspath / "reference.xlsx",
        cells={"A2": 10, "A3": 20, "A4": 30, "A5": 40},
    )
    write_workbook(
        fix_syspath / "submission.xlsx",
        cells={"A2": 10, "A3": 20, "A4": 30, "A5": 40},
    )

    built_class = build(
        Options(
            weight=1,
            required_files=("submission.xlsx",),
            entries=("A2", "A5"),
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_data_series_match_reference_0")
    test_method = built_instance.test_data_series_match_reference_0
    test_method()

    assert test_method.__score__ == test_method.__weight__


def test_failing_same_range_case(fix_syspath):
    write_workbook(
        fix_syspath / "reference.xlsx",
        cells={"A2": 10, "A3": 20, "A4": 30, "A5": 40},
    )
    write_workbook(
        fix_syspath / "submission.xlsx",
        cells={"A2": 10, "A3": 20, "A4": 999, "A5": 40},
    )

    built_class = build(
        Options(
            weight=1,
            required_files=("submission.xlsx",),
            entries=("A2", "A5"),
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_data_series_match_reference_0")
    test_method = built_instance.test_data_series_match_reference_0

    with pytest.raises(AssertionError) as exc_info:
        test_method()

    assert "did not meet the expected" in str(exc_info.value)
    assert test_method.__score__ == 0


def test_passing_search_mode_relocated_case(fix_syspath):
    write_workbook(
        fix_syspath / "reference.xlsx",
        cells={"A2": 10, "A3": 20, "A4": 30, "A5": 40},
    )
    write_workbook(
        fix_syspath / "submission.xlsx",
        cells={"D2": 10, "D3": 20, "D4": 30, "D5": 40},
    )

    built_class = build(
        Options(
            weight=1,
            required_files=("submission.xlsx",),
            entries=("A2", "A5"),
            range_matches_reference=False,
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_data_series_match_reference_0")
    test_method = built_instance.test_data_series_match_reference_0
    test_method()

    assert test_method.__score__ == test_method.__weight__


def test_passing_search_mode_ratio_case(fix_syspath):
    write_workbook(
        fix_syspath / "reference.xlsx",
        cells={"A2": 10, "A3": 20, "A4": 30, "A5": 40},
    )
    write_workbook(
        fix_syspath / "submission.xlsx",
        cells={"D2": 10, "D3": 20, "D4": 999, "D5": 40},
    )

    built_class = build(
        Options(
            weight=1,
            ratio=0.75,
            required_files=("submission.xlsx",),
            entries=("A2", "A5"),
            range_matches_reference=False,
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_data_series_match_reference_0")
    test_method = built_instance.test_data_series_match_reference_0
    test_method()

    assert test_method.__score__ == test_method.__weight__


def test_failing_search_mode_exact_case(fix_syspath):
    write_workbook(
        fix_syspath / "reference.xlsx",
        cells={"A2": 10, "A3": 20, "A4": 30, "A5": 40},
    )
    write_workbook(
        fix_syspath / "submission.xlsx",
        cells={"D2": 10, "D3": 20, "D4": 999, "D5": 40},
    )

    built_class = build(
        Options(
            weight=1,
            required_files=("submission.xlsx",),
            entries=("A2", "A5"),
            range_matches_reference=False,
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_data_series_match_reference_0")
    test_method = built_instance.test_data_series_match_reference_0

    with pytest.raises(AssertionError) as exc_info:
        test_method()

    assert "No exact data series match" in str(exc_info.value)
    assert test_method.__score__ == 0


def test_first_worksheet_default_sheet_fallback(fix_syspath):
    write_workbook(
        fix_syspath / "reference.xlsx",
        sheet_name="Grades",
        cells={"A2": 10, "A3": 20, "A4": 30, "A5": 40},
    )
    write_workbook(
        fix_syspath / "submission.xlsx",
        sheet_name="Grades",
        cells={"A2": 10, "A3": 20, "A4": 30, "A5": 40},
    )

    built_class = build(
        Options(
            weight=1,
            required_files=("submission.xlsx",),
            entries=("A2", "A5"),
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_data_series_match_reference_0")
    test_method = built_instance.test_data_series_match_reference_0
    test_method()

    assert test_method.__score__ == test_method.__weight__


# ---------------------------------------------------------------------------
# `series_require_formulas` formula-detection gate: ordinary formula, array
# formula, plain value, and empty cell -- for BOTH the range_matches_reference
# branch (cell-by-cell) and the search-anywhere branch. Array-formula cells
# hold an openpyxl `ArrayFormula` object rather than a `str`, so a naive
# `isinstance(value, str)` check reports a legitimate array formula as "not
# a formula" -- this is the bug these tests pin down.
#
# Note: openpyxl-authored fixtures never carry a *cached* value for a
# formula cell (there's no calc engine involved), so a formula cell's
# `data_only` read is always None. The value-match `ratio` check and the
# formula-existence check are independent gates in the source, so the
# formula-passing tests below set `ratio=0.0` to isolate the formula gate
# from the (here, unrepresentable) value-match gate; the failing tests use
# values that already satisfy the default ratio so the formula gate is what
# trips the failure.
# ---------------------------------------------------------------------------


def test_require_formulas_same_range_ordinary_formula_passes(fix_syspath):
    write_workbook(fix_syspath / "reference.xlsx", cells={"A2": 10})
    write_workbook(fix_syspath / "submission.xlsx", cells={"A2": "=1+1"})

    built_class = build(
        Options(
            weight=1,
            ratio=0.0,
            required_files=("submission.xlsx",),
            entries=("A2", "A2"),
            series_require_formulas=True,
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_data_series_match_reference_0")
    test_method = built_instance.test_data_series_match_reference_0
    test_method()

    assert test_method.__score__ == test_method.__weight__


def test_require_formulas_same_range_array_formula_passes(fix_syspath):
    write_workbook(fix_syspath / "reference.xlsx", cells={"A2": 10})

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Sheet1"
    worksheet["A2"] = ArrayFormula("A2", "=MODE.MULT(B1:B10)")
    workbook.save(fix_syspath / "submission.xlsx")

    built_class = build(
        Options(
            weight=1,
            ratio=0.0,
            required_files=("submission.xlsx",),
            entries=("A2", "A2"),
            series_require_formulas=True,
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_data_series_match_reference_0")
    test_method = built_instance.test_data_series_match_reference_0
    test_method()

    assert test_method.__score__ == test_method.__weight__


def test_require_formulas_same_range_plain_value_fails(fix_syspath):
    write_workbook(fix_syspath / "reference.xlsx", cells={"A2": 10})
    write_workbook(fix_syspath / "submission.xlsx", cells={"A2": 10})

    built_class = build(
        Options(
            weight=1,
            required_files=("submission.xlsx",),
            entries=("A2", "A2"),
            series_require_formulas=True,
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_data_series_match_reference_0")
    test_method = built_instance.test_data_series_match_reference_0

    with pytest.raises(AssertionError) as exc_info:
        test_method()

    assert "must contain a formula" in str(exc_info.value)
    assert test_method.__score__ == 0


def test_require_formulas_same_range_empty_cell_fails(fix_syspath):
    write_workbook(fix_syspath / "reference.xlsx", cells={})
    write_workbook(fix_syspath / "submission.xlsx", cells={})

    built_class = build(
        Options(
            weight=1,
            required_files=("submission.xlsx",),
            entries=("A2", "A2"),
            series_require_formulas=True,
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_data_series_match_reference_0")
    test_method = built_instance.test_data_series_match_reference_0

    with pytest.raises(AssertionError) as exc_info:
        test_method()

    assert "must contain a formula" in str(exc_info.value)
    assert test_method.__score__ == 0


def test_require_formulas_search_mode_ordinary_formula_passes(fix_syspath):
    write_workbook(fix_syspath / "reference.xlsx", cells={"A2": 10})
    write_workbook(fix_syspath / "submission.xlsx", cells={"A1": "=1+1"})

    built_class = build(
        Options(
            weight=1,
            ratio=0.0,
            required_files=("submission.xlsx",),
            entries=("A2", "A2"),
            range_matches_reference=False,
            series_require_formulas=True,
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_data_series_match_reference_0")
    test_method = built_instance.test_data_series_match_reference_0
    test_method()

    assert test_method.__score__ == test_method.__weight__


def test_require_formulas_search_mode_array_formula_passes(fix_syspath):
    write_workbook(fix_syspath / "reference.xlsx", cells={"A2": 10})

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Sheet1"
    worksheet["A1"] = ArrayFormula("A1", "=MODE.MULT(B1:B10)")
    workbook.save(fix_syspath / "submission.xlsx")

    built_class = build(
        Options(
            weight=1,
            ratio=0.0,
            required_files=("submission.xlsx",),
            entries=("A2", "A2"),
            range_matches_reference=False,
            series_require_formulas=True,
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_data_series_match_reference_0")
    test_method = built_instance.test_data_series_match_reference_0
    test_method()

    assert test_method.__score__ == test_method.__weight__


def test_require_formulas_search_mode_plain_value_fails(fix_syspath):
    write_workbook(fix_syspath / "reference.xlsx", cells={"A2": 10})
    write_workbook(fix_syspath / "submission.xlsx", cells={"A1": 42})

    built_class = build(
        Options(
            weight=1,
            ratio=0.0,
            required_files=("submission.xlsx",),
            entries=("A2", "A2"),
            range_matches_reference=False,
            series_require_formulas=True,
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_data_series_match_reference_0")
    test_method = built_instance.test_data_series_match_reference_0

    with pytest.raises(AssertionError) as exc_info:
        test_method()

    assert "is not a formula cell" in str(exc_info.value)
    assert test_method.__score__ == 0


def test_require_formulas_search_mode_empty_cell_fails(fix_syspath):
    write_workbook(fix_syspath / "reference.xlsx", cells={"A2": 10})
    # A1 stays empty; B1 anchors sheet dimensions so the search space isn't
    # empty, while A1 (the first, and therefore best-scoring-tie-breaking,
    # length-1 candidate window) remains unfilled.
    write_workbook(fix_syspath / "submission.xlsx", cells={"B1": "unrelated"})

    built_class = build(
        Options(
            weight=1,
            ratio=0.0,
            required_files=("submission.xlsx",),
            entries=("A2", "A2"),
            range_matches_reference=False,
            series_require_formulas=True,
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_data_series_match_reference_0")
    test_method = built_instance.test_data_series_match_reference_0

    with pytest.raises(AssertionError) as exc_info:
        test_method()

    assert "is not a formula cell" in str(exc_info.value)
    assert test_method.__score__ == 0


# ---------------------------------------------------------------------------
# Relocation fallback (same-location branch): when the expected window fails,
# an intact series found elsewhere on the sheet (same orientation, length >= 3)
# earns credit under the same formula requirement.  Common cause: an inserted
# or deleted row shifting an otherwise-correct block off its template cells.
#
# openpyxl cannot write a cached result next to a formula, so fixtures that
# need a formula cell with a value (the shape a desktop Excel save produces)
# inject the `<v>` element into the sheet XML after saving.
# ---------------------------------------------------------------------------


def write_workbook_with_cached_formulas(path, cells=None, cached=None):
    """Write a workbook where *cached* maps cell -> (formula, cached_value)."""

    import re
    import zipfile

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Sheet1"
    for cell, value in (cells or {}).items():
        worksheet[cell] = value
    for cell, (formula, _value) in (cached or {}).items():
        worksheet[cell] = formula
    workbook.save(path)

    with zipfile.ZipFile(path) as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}

    sheet_xml = entries["xl/worksheets/sheet1.xml"].decode()
    for cell, (_formula, value) in (cached or {}).items():
        pattern = rf'(<c r="{cell}"[^>]*>)(<f>[^<]*</f>)'
        sheet_xml, count = re.subn(pattern, rf"\g<1>\g<2><v>{value}</v>", sheet_xml)
        assert count == 1, f"could not inject cached value for {cell}"
    entries["xl/worksheets/sheet1.xml"] = sheet_xml.encode()

    with zipfile.ZipFile(path, "w") as archive:
        for name, data in entries.items():
            archive.writestr(name, data)


def test_relocated_series_passes(fix_syspath):
    # Row-shifted submission: the whole block sits one row low.
    write_workbook(
        fix_syspath / "reference.xlsx",
        cells={"A2": 10, "A3": 20, "A4": 30, "A5": 40},
    )
    write_workbook(
        fix_syspath / "submission.xlsx",
        cells={"A3": 10, "A4": 20, "A5": 30, "A6": 40},
    )

    built_class = build(
        Options(
            weight=1,
            required_files=("submission.xlsx",),
            entries=("A2", "A5"),
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_data_series_match_reference_0")
    test_method = built_instance.test_data_series_match_reference_0
    test_method()

    assert test_method.__score__ == test_method.__weight__


def test_relocated_series_with_formulas_passes(fix_syspath):
    write_workbook(
        fix_syspath / "reference.xlsx",
        cells={"A2": 10, "A3": 20, "A4": 30, "A5": 40},
    )
    write_workbook_with_cached_formulas(
        fix_syspath / "submission.xlsx",
        cached={
            "A3": ("=5+5", 10),
            "A4": ("=10+10", 20),
            "A5": ("=15+15", 30),
            "A6": ("=20+20", 40),
        },
    )

    built_class = build(
        Options(
            weight=1,
            required_files=("submission.xlsx",),
            entries=("A2", "A5"),
            series_require_formulas=True,
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_data_series_match_reference_0")
    test_method = built_instance.test_data_series_match_reference_0
    test_method()

    assert test_method.__score__ == test_method.__weight__


def test_relocation_prefers_formula_window(fix_syspath):
    # The series values appear twice: a typed copy in column A (scanned
    # first) and a formula-backed copy in column C.  The formula copy must
    # win even though the typed copy is found earlier.
    write_workbook(
        fix_syspath / "reference.xlsx",
        cells={"A2": 10, "A3": 20, "A4": 30, "A5": 40},
    )
    write_workbook_with_cached_formulas(
        fix_syspath / "submission.xlsx",
        cells={"A3": 10, "A4": 20, "A5": 30, "A6": 40},
        cached={
            "C2": ("=5+5", 10),
            "C3": ("=10+10", 20),
            "C4": ("=15+15", 30),
            "C5": ("=20+20", 40),
        },
    )

    built_class = build(
        Options(
            weight=1,
            required_files=("submission.xlsx",),
            entries=("A2", "A5"),
            series_require_formulas=True,
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_data_series_match_reference_0")
    test_method = built_instance.test_data_series_match_reference_0
    test_method()

    assert test_method.__score__ == test_method.__weight__


def test_relocation_found_typed_copy_fails_with_location(fix_syspath):
    # The only relocated copy is typed numbers; with formulas required the
    # check still fails, and the message names where the values were found.
    write_workbook(
        fix_syspath / "reference.xlsx",
        cells={"A2": 10, "A3": 20, "A4": 30, "A5": 40},
    )
    write_workbook(
        fix_syspath / "submission.xlsx",
        cells={"A3": 10, "A4": 20, "A5": 30, "A6": 40},
    )

    built_class = build(
        Options(
            weight=1,
            required_files=("submission.xlsx",),
            entries=("A2", "A5"),
            series_require_formulas=True,
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_data_series_match_reference_0")
    test_method = built_instance.test_data_series_match_reference_0

    with pytest.raises(AssertionError) as exc_info:
        test_method()

    message = str(exc_info.value)
    assert "did not meet the expected" in message
    assert "A matching series was found at `A3:A6`" in message
    assert "must contain a formula" in message
    assert test_method.__score__ == 0


def test_relocation_partial_match_names_closest_window(fix_syspath):
    # No window fully matches; the failure message points at the closest one.
    write_workbook(
        fix_syspath / "reference.xlsx",
        cells={"A2": 10, "A3": 20, "A4": 30, "A5": 40},
    )
    write_workbook(
        fix_syspath / "submission.xlsx",
        cells={"A3": 10, "A4": 20, "A5": 999, "A6": 40},
    )

    built_class = build(
        Options(
            weight=1,
            required_files=("submission.xlsx",),
            entries=("A2", "A5"),
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_data_series_match_reference_0")
    test_method = built_instance.test_data_series_match_reference_0

    with pytest.raises(AssertionError) as exc_info:
        test_method()

    message = " ".join(str(exc_info.value).split())
    assert "did not meet the expected" in message
    assert "The closest match found was at `A3:A6` (ratio 0.75)" in message
    assert "inserted or deleted rows" in message
    assert test_method.__score__ == 0


def test_relocation_disabled_restores_strict_behavior(fix_syspath):
    write_workbook(
        fix_syspath / "reference.xlsx",
        cells={"A2": 10, "A3": 20, "A4": 30, "A5": 40},
    )
    write_workbook(
        fix_syspath / "submission.xlsx",
        cells={"A3": 10, "A4": 20, "A5": 30, "A6": 40},
    )

    built_class = build(
        Options(
            weight=1,
            required_files=("submission.xlsx",),
            entries=("A2", "A5"),
            series_allow_relocation=False,
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_data_series_match_reference_0")
    test_method = built_instance.test_data_series_match_reference_0

    with pytest.raises(AssertionError) as exc_info:
        test_method()

    message = str(exc_info.value)
    assert "did not meet the expected" in message
    assert "closest match" not in message
    assert "matching series" not in message
    assert test_method.__score__ == 0


def test_relocation_skipped_below_minimum_length(fix_syspath):
    # A two-value series matches elsewhere too easily to mean anything, so
    # relocation never applies to it.
    write_workbook(
        fix_syspath / "reference.xlsx",
        cells={"A2": 10, "A3": 20},
    )
    write_workbook(
        fix_syspath / "submission.xlsx",
        cells={"A3": 10, "A4": 20},
    )

    built_class = build(
        Options(
            weight=1,
            required_files=("submission.xlsx",),
            entries=("A2", "A3"),
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_data_series_match_reference_0")
    test_method = built_instance.test_data_series_match_reference_0

    with pytest.raises(AssertionError) as exc_info:
        test_method()

    message = str(exc_info.value)
    assert "did not meet the expected" in message
    assert "closest match" not in message
    assert test_method.__score__ == 0


def test_case_renamed_sheet_still_passes(fix_syspath):
    """Renaming "Beam Data" to "Beam data" does not fail the check."""

    write_workbook(
        fix_syspath / "reference.xlsx",
        sheet_name="Beam Data",
        cells={"A2": 10, "A3": 20, "A4": 30, "A5": 40},
    )
    write_workbook(
        fix_syspath / "submission.xlsx",
        sheet_name="Beam data",
        cells={"A2": 10, "A3": 20, "A4": 30, "A5": 40},
    )

    built_class = build(
        Options(
            weight=1,
            required_files=("submission.xlsx",),
            sheet="Beam Data",
            entries=("A2", "A5"),
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_data_series_match_reference_0")
    test_method = built_instance.test_data_series_match_reference_0
    test_method()

    assert test_method.__score__ == test_method.__weight__


def test_missing_sheet_gives_a_hint_not_a_traceback(fix_syspath):
    """A deleted sheet is reported as a graded failure with a hint."""

    write_workbook(
        fix_syspath / "reference.xlsx",
        sheet_name="Beam Data",
        cells={"A2": 10, "A3": 20, "A4": 30, "A5": 40},
    )
    write_workbook(
        fix_syspath / "submission.xlsx",
        sheet_name="Summary",
        cells={"A2": 10, "A3": 20, "A4": 30, "A5": 40},
    )

    built_class = build(
        Options(
            weight=1,
            required_files=("submission.xlsx",),
            sheet="Beam Data",
            entries=("A2", "A5"),
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_data_series_match_reference_0")
    test_method = built_instance.test_data_series_match_reference_0

    with pytest.raises(AssertionError) as exc_info:
        test_method()

    message = " ".join(str(exc_info.value).split())
    assert "`Beam Data`" in message
    assert "`Summary`" in message
    assert "does not exist" not in message
    assert test_method.__score__ == 0


# ---------------------------------------------------------------------------
# Uncached formula results: a workbook saved by an editor that does not write
# the values its formulas produce reads as empty in every data check.
# ---------------------------------------------------------------------------


def write_workbook_without_cached_values(path, cells=None, sheet_name="Sheet1"):
    """Write a workbook whose formulas carry no cached results.

    openpyxl has no calculation engine, so a workbook it writes never
    holds a formula result.  That is exactly the state a workbook saved
    by Google Sheets, Numbers, or an online editor arrives in.
    """

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = sheet_name
    for cell, formula in (cells or {}).items():
        worksheet[cell] = formula
    workbook.save(path)


def test_uncached_formula_results_are_named_as_the_cause(fix_syspath):
    """Formulas with no cached results get their own message."""

    write_workbook(
        fix_syspath / "reference.xlsx",
        cells={"A2": 10, "A3": 20, "A4": 30, "A5": 40},
    )
    write_workbook_without_cached_values(
        fix_syspath / "submission.xlsx",
        cells={"A2": "=5+5", "A3": "=10+10", "A4": "=15+15", "A5": "=20+20"},
    )

    built_class = build(
        Options(
            weight=1,
            required_files=("submission.xlsx",),
            entries=("A2", "A5"),
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_data_series_match_reference_0")
    test_method = built_instance.test_data_series_match_reference_0

    with pytest.raises(AssertionError) as exc_info:
        test_method()

    message = " ".join(str(exc_info.value).split())
    assert "does not carry the results those formulas produce" in message
    assert "desktop version of Excel" in message
    # The generic ratio message would send the student after the wrong thing.
    assert "did not meet the expected match ratio" not in message
    assert test_method.__score__ == 0


def test_uncached_formula_results_named_in_search_mode(fix_syspath):
    """Search mode reports the same cause when nothing can be found."""

    write_workbook(
        fix_syspath / "reference.xlsx",
        cells={"A2": 10, "A3": 20, "A4": 30, "A5": 40},
    )
    write_workbook_without_cached_values(
        fix_syspath / "submission.xlsx",
        cells={"C1": "=5+5", "C2": "=10+10", "C3": "=15+15", "C4": "=20+20"},
    )

    built_class = build(
        Options(
            weight=1,
            required_files=("submission.xlsx",),
            entries=("A2", "A5"),
            range_matches_reference=False,
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_data_series_match_reference_0")
    test_method = built_instance.test_data_series_match_reference_0

    with pytest.raises(AssertionError) as exc_info:
        test_method()

    message = " ".join(str(exc_info.value).split())
    assert "does not carry the results those formulas produce" in message
    assert test_method.__score__ == 0


def test_uncached_message_carries_the_assignment_hint(fix_syspath):
    """The per-assignment hint rides along, as it does on every message."""

    write_workbook(
        fix_syspath / "reference.xlsx",
        cells={"A2": 10, "A3": 20, "A4": 30, "A5": 40},
    )
    write_workbook_without_cached_values(
        fix_syspath / "submission.xlsx",
        cells={"A2": "=5+5", "A3": "=10+10", "A4": "=15+15", "A5": "=20+20"},
    )

    built_class = build(
        Options(
            weight=1,
            required_files=("submission.xlsx",),
            entries=("A2", "A5"),
            hint="See step 4 of the task.",
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_data_series_match_reference_0")
    test_method = built_instance.test_data_series_match_reference_0

    with pytest.raises(AssertionError) as exc_info:
        test_method()

    assert "See step 4 of the task." in " ".join(str(exc_info.value).split())


def test_wrong_values_are_not_blamed_on_caching(fix_syspath):
    """A workbook with cached results keeps the ordinary failure message."""

    write_workbook(
        fix_syspath / "reference.xlsx",
        cells={"A2": 10, "A3": 20, "A4": 30, "A5": 40},
    )
    write_workbook_with_cached_formulas(
        fix_syspath / "submission.xlsx",
        cached={
            "A2": ("=5+5", 10),
            "A3": ("=10+10", 20),
            "A4": ("=15+15", 999),
            "A5": ("=20+20", 40),
        },
    )

    built_class = build(
        Options(
            weight=1,
            required_files=("submission.xlsx",),
            entries=("A2", "A5"),
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_data_series_match_reference_0")
    test_method = built_instance.test_data_series_match_reference_0

    with pytest.raises(AssertionError) as exc_info:
        test_method()

    message = " ".join(str(exc_info.value).split())
    assert "did not meet the expected match ratio" in message
    assert "does not carry the results" not in message


def test_typed_values_are_not_blamed_on_caching(fix_syspath):
    """A workbook with no formulas at all keeps the ordinary message."""

    write_workbook(
        fix_syspath / "reference.xlsx",
        cells={"A2": 10, "A3": 20, "A4": 30, "A5": 40},
    )
    write_workbook(
        fix_syspath / "submission.xlsx",
        cells={"A2": 1, "A3": 2, "A4": 3, "A5": 4},
    )

    built_class = build(
        Options(
            weight=1,
            required_files=("submission.xlsx",),
            entries=("A2", "A5"),
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_data_series_match_reference_0")
    test_method = built_instance.test_data_series_match_reference_0

    with pytest.raises(AssertionError) as exc_info:
        test_method()

    message = " ".join(str(exc_info.value).split())
    assert "did not meet the expected match ratio" in message
    assert "does not carry the results" not in message


def test_formulas_lack_cached_values_helper(fix_syspath):
    """The detector needs a formula present and every result missing."""

    uncached = fix_syspath / "uncached.xlsx"
    write_workbook_without_cached_values(uncached, cells={"A2": "=5+5"})
    assert formulas_lack_cached_values(str(uncached), "Sheet1") is True

    cached = fix_syspath / "cached.xlsx"
    write_workbook_with_cached_formulas(cached, cached={"A2": ("=5+5", 10)})
    assert formulas_lack_cached_values(str(cached), "Sheet1") is False

    typed = fix_syspath / "typed.xlsx"
    write_workbook(typed, cells={"A2": 10})
    assert formulas_lack_cached_values(str(typed), "Sheet1") is False
