import unittest

import pytest
from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference

from generic_grader.excel.chart_metadata_match_reference import build
from generic_grader.utils.options import Options


def write_chart_workbook(path, sheet_name="Sheet1", chart_specs=None):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = sheet_name

    worksheet.append(["Month", "Sales", "Cost"])
    worksheet.append(["Jan", 100, 80])
    worksheet.append(["Feb", 120, 90])
    worksheet.append(["Mar", 130, 92])
    worksheet.append(["Apr", 140, 95])

    chart_specs = chart_specs or []
    for i, spec in enumerate(chart_specs):
        values_col = spec.get("values_col", 2)
        chart = LineChart()
        chart_title = spec.get("title")
        if chart_title is not None:
            chart.title = chart_title
        chart.x_axis.title = spec.get("x_axis_label")
        chart.y_axis.title = spec.get("y_axis_label")

        values = Reference(worksheet, min_col=values_col, min_row=1, max_row=5)
        categories = Reference(worksheet, min_col=1, min_row=2, max_row=5)
        chart.add_data(values, titles_from_data=True)
        chart.set_categories(categories)
        worksheet.add_chart(chart, f"E{2 + i * 14}")

    workbook.save(path)


@pytest.fixture()
def built_class():
    return build(
        Options(
            required_files=("submission.xlsx",),
            sheet="Sheet1",
            kwargs={"reference_file": "reference.xlsx"},
        )
    )


@pytest.fixture()
def built_instance(built_class):
    return built_class()


def test_build_class(built_class):
    assert issubclass(built_class, unittest.TestCase)


def test_build_class_name(built_class):
    assert built_class.__name__ == "TestChartMetadataMatchReference"


def test_instance_has_test_method(built_instance):
    assert hasattr(built_instance, "test_chart_metadata_match_reference_0")


def test_doc_func(built_instance):
    assert (
        built_instance.test_chart_metadata_match_reference_0.__doc__
        == "Check that chart title and axis labels on sheet `Sheet1` are meaningfully similar to the reference workbook."
    )


def test_passing_fuzzy_case(fix_syspath):
    write_chart_workbook(
        fix_syspath / "reference.xlsx",
        chart_specs=[
            {
                "title": "Monthly Sales Analysis",
                "x_axis_label": "Month",
                "y_axis_label": "Revenue Dollars",
            }
        ],
    )
    write_chart_workbook(
        fix_syspath / "submission.xlsx",
        chart_specs=[
            {
                "title": "Monthly Sales Analyses",
                "x_axis_label": "Months",
                "y_axis_label": "Revenue in Dollars",
            }
        ],
    )

    built_class = build(
        Options(
            weight=1,
            required_files=("submission.xlsx",),
            sheet="Sheet1",
            chart_ratio=0.8,
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_chart_metadata_match_reference_0")
    test_method = built_instance.test_chart_metadata_match_reference_0
    test_method()

    assert test_method.__score__ == test_method.__weight__


def test_failing_similarity_case(fix_syspath):
    write_chart_workbook(
        fix_syspath / "reference.xlsx",
        chart_specs=[
            {
                "title": "Monthly Sales Analysis",
                "x_axis_label": "Month",
                "y_axis_label": "Revenue Dollars",
            }
        ],
    )
    write_chart_workbook(
        fix_syspath / "submission.xlsx",
        chart_specs=[
            {
                "title": "Random Chart",
                "x_axis_label": "Thing",
                "y_axis_label": "Stuff",
            }
        ],
    )

    built_class = build(
        Options(
            weight=1,
            required_files=("submission.xlsx",),
            sheet="Sheet1",
            chart_ratio=0.8,
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_chart_metadata_match_reference_0")
    test_method = built_instance.test_chart_metadata_match_reference_0

    with pytest.raises(AssertionError) as exc_info:
        test_method()

    # Normalize the wrapper's line breaks so assertions do not depend on
    # where wrapper.fill happens to split a line.
    message = " ".join(str(exc_info.value).split())
    # The message must not hand the student the reference chart's title.
    # On assignments where writing the title is part of the graded work,
    # echoing it is the answer.
    assert "Monthly Sales Analysis" not in message
    # It must still be actionable: name the sheet and report what the
    # submission actually contains.
    assert "Sheet1" in message
    assert "Random Chart" in message
    assert test_method.__score__ == 0


def test_failing_similarity_case_includes_hint(fix_syspath):
    """The assignment's own hint must survive into the no-match message."""

    write_chart_workbook(
        fix_syspath / "reference.xlsx",
        chart_specs=[{"title": "Monthly Sales Analysis"}],
    )
    write_chart_workbook(
        fix_syspath / "submission.xlsx",
        chart_specs=[{"title": "Random Chart"}],
    )

    built_class = build(
        Options(
            weight=1,
            required_files=("submission.xlsx",),
            sheet="Sheet1",
            chart_ratio=0.8,
            hint="Check the chart on the summary tab.",
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_chart_metadata_match_reference_0")
    test_method = built_instance.test_chart_metadata_match_reference_0

    with pytest.raises(AssertionError) as exc_info:
        test_method()

    message = " ".join(str(exc_info.value).split())
    assert "Check the chart on the summary tab." in message
    assert "Monthly Sales Analysis" not in message


def test_failing_missing_submission_title(fix_syspath):
    write_chart_workbook(
        fix_syspath / "reference.xlsx",
        chart_specs=[
            {
                "title": "Monthly Sales Analysis",
                "x_axis_label": "Month",
                "y_axis_label": "Revenue Dollars",
            }
        ],
    )
    write_chart_workbook(
        fix_syspath / "submission.xlsx",
        chart_specs=[
            {
                "title": "   ",
                "x_axis_label": "Month",
                "y_axis_label": "Revenue Dollars",
            }
        ],
    )

    built_class = build(
        Options(
            weight=1,
            required_files=("submission.xlsx",),
            sheet="Sheet1",
            chart_require_title=True,
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_chart_metadata_match_reference_0")
    test_method = built_instance.test_chart_metadata_match_reference_0

    with pytest.raises(AssertionError) as exc_info:
        test_method()

    assert "meaningful title" in str(exc_info.value)
    assert test_method.__score__ == 0


def test_matches_charts_by_title_not_order(fix_syspath):
    write_chart_workbook(
        fix_syspath / "reference.xlsx",
        chart_specs=[
            {
                "title": "Revenue Trend",
                "x_axis_label": "Month",
                "y_axis_label": "Revenue",
                "values_col": 2,
            },
            {
                "title": "Cost Trend",
                "x_axis_label": "Month",
                "y_axis_label": "Cost",
                "values_col": 3,
            },
        ],
    )
    write_chart_workbook(
        fix_syspath / "submission.xlsx",
        chart_specs=[
            {
                "title": "Cost Trend",
                "x_axis_label": "Month",
                "y_axis_label": "Cost",
                "values_col": 3,
            },
            {
                "title": "Revenue Trend",
                "x_axis_label": "Month",
                "y_axis_label": "Revenue",
                "values_col": 2,
            },
        ],
    )

    built_class = build(
        Options(
            weight=1,
            required_files=("submission.xlsx",),
            sheet="Sheet1",
            chart_ratio=0.8,
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_chart_metadata_match_reference_0")
    test_method = built_instance.test_chart_metadata_match_reference_0
    test_method()

    assert test_method.__score__ == test_method.__weight__
