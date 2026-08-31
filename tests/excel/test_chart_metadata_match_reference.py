import unittest

import pytest
from openpyxl import Workbook
from openpyxl.chart import (
    BarChart,
    BarChart3D,
    LineChart,
    Reference,
    ScatterChart,
    Series,
)

from generic_grader.excel._workbook import extract_chart_info_from_workbook
from generic_grader.excel.chart_metadata_match_reference import (
    build,
    graded_metadata_fields,
    grades_title_by_similarity,
    normalized_chart_types,
)
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
        kinds = {"bar": BarChart, "bar3d": BarChart3D, "scatter": ScatterChart}
        chart_class = kinds.get(spec.get("kind"), LineChart)
        chart = chart_class()
        chart_title = spec.get("title")
        if chart_title is not None:
            chart.title = chart_title
        chart.x_axis.title = spec.get("x_axis_label")
        chart.y_axis.title = spec.get("y_axis_label")
        if spec.get("kind") == "scatter":
            # Excel writes the x value-axis at the bottom; openpyxl
            # defaults both scatter axes to the left position.
            chart.x_axis.axPos = "b"
        if spec.get("horizontal"):
            # A horizontal bar chart: Excel renders the categories up the
            # left side and the values along the bottom, so the category
            # axis is the one on the left.  openpyxl does not set these
            # positions for us, so the fixture writes them the way Excel
            # would.
            chart.type = "bar"
            chart.x_axis.axPos = "l"
            chart.y_axis.axPos = "b"

        max_row = spec.get("max_row", 5)
        if spec.get("split_series"):
            # One single-point series per data row, the way a student
            # who picked each value separately builds the chart.
            for row in range(2, max_row + 1):
                values = Reference(
                    worksheet, min_col=values_col, min_row=row, max_row=row
                )
                chart.append(Series(values))
        elif spec.get("kind") == "scatter":
            x_values = Reference(worksheet, min_col=1, min_row=2, max_row=max_row)
            y_values = Reference(
                worksheet, min_col=values_col, min_row=2, max_row=max_row
            )
            chart.append(Series(y_values, x_values))
        else:
            values = Reference(
                worksheet, min_col=values_col, min_row=1, max_row=max_row
            )
            categories = Reference(worksheet, min_col=1, min_row=2, max_row=max_row)
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
        == "Check that the chart on sheet `Sheet1` is the expected chart type and plots the expected data."
    )


def test_doc_func_graded_title_and_labels():
    built_class = build(
        Options(
            required_files=("submission.xlsx",),
            sheet="Sheet1",
            chart_grade_title=True,
            chart_grade_axis_labels=True,
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class()
    assert (
        built_instance.test_chart_metadata_match_reference_0.__doc__
        == "Check that the chart on sheet `Sheet1` is the expected chart type and plots the expected data, and has a descriptive title and has axis labels similar to the reference workbook."
    )


def test_doc_func_strict_title():
    built_class = build(
        Options(
            required_files=("submission.xlsx",),
            sheet="Sheet1",
            chart_grade_title=True,
            chart_title_match_reference=True,
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class()
    assert (
        built_instance.test_chart_metadata_match_reference_0.__doc__
        == "Check that the chart on sheet `Sheet1` is the expected chart type and plots the expected data, and has a title similar to the reference workbook."
    )


def test_grading_flags_default_off():
    """Title and axis-label grading are both off unless a task opts in."""

    o = Options()
    assert o.chart_grade_title is False
    assert o.chart_grade_axis_labels is False
    assert o.chart_title_match_reference is False


def test_strict_title_flag_is_inert_without_title_grading():
    """chart_title_match_reference alone must not restore title grading.

    Identifying a chart by its title is itself title grading, so the
    legacy flag stays inert until `chart_grade_title` turns grading on.
    """

    o = Options(chart_title_match_reference=True)
    assert grades_title_by_similarity(o) is False
    assert graded_metadata_fields(o) == ()


def test_graded_metadata_fields_follow_the_flags():
    base = {"sheet": "Sheet1"}
    assert graded_metadata_fields(Options(**base)) == ()
    assert graded_metadata_fields(Options(**base, chart_grade_title=True)) == ("title",)
    assert graded_metadata_fields(Options(**base, chart_grade_axis_labels=True)) == (
        "x_axis_label",
        "y_axis_label",
    )
    assert graded_metadata_fields(
        Options(**base, chart_grade_title=True, chart_grade_axis_labels=True)
    ) == ("title", "x_axis_label", "y_axis_label")


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


def test_self_authored_title_passes(fix_syspath):
    """A title unlike the reference passes when the axis labels match.

    Students author their own titles, so the title identifies nothing and
    is graded on presence only.
    """

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
                "title": "Sales vs Month",
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
            chart_ratio=0.8,
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_chart_metadata_match_reference_0")
    test_method = built_instance.test_chart_metadata_match_reference_0
    test_method()

    assert test_method.__score__ == test_method.__weight__


def test_failing_axis_label_case(fix_syspath):
    """Dissimilar axis labels fail under opt-in axis grading.

    The message must not leak the reference title or the reference label
    wording, even when the labels are what is being graded.
    """

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
            chart_grade_axis_labels=True,
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_chart_metadata_match_reference_0")
    test_method = built_instance.test_chart_metadata_match_reference_0

    with pytest.raises(AssertionError) as exc_info:
        test_method()

    message = " ".join(str(exc_info.value).split())
    # The message must not hand the student the reference chart's title.
    assert "Monthly Sales Analysis" not in message
    assert "axis_label" in message
    assert "not sufficiently similar" in message
    assert test_method.__score__ == 0


def test_strict_title_mode_restores_identification_gate(fix_syspath):
    """The two title flags together keep the legacy title gate and hint."""

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
            chart_grade_title=True,
            chart_title_match_reference=True,
            hint="Check the chart on the summary tab.",
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_chart_metadata_match_reference_0")
    test_method = built_instance.test_chart_metadata_match_reference_0

    with pytest.raises(AssertionError) as exc_info:
        test_method()

    message = " ".join(str(exc_info.value).split())
    assert "could not be identified" in message
    assert "Check the chart on the summary tab." in message
    assert "Monthly Sales Analysis" not in message
    assert "Random Chart" in message
    assert test_method.__score__ == 0


def test_blank_title_passes_by_default(fix_syspath):
    """A blank title passes when the task does not grade titles."""

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
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_chart_metadata_match_reference_0")
    test_method = built_instance.test_chart_metadata_match_reference_0
    test_method()

    assert test_method.__score__ == test_method.__weight__


def test_blank_title_fails_when_title_graded(fix_syspath):
    """The opt-in title flag restores the presence check on the title."""

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
            chart_grade_title=True,
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_chart_metadata_match_reference_0")
    test_method = built_instance.test_chart_metadata_match_reference_0

    with pytest.raises(AssertionError) as exc_info:
        test_method()

    message = " ".join(str(exc_info.value).split())
    assert "missing or not meaningful" in message
    assert "Monthly Sales Analysis" not in message
    assert test_method.__score__ == 0


def test_blank_axis_labels_pass_by_default(fix_syspath):
    """Blank axis labels pass when the task does not grade labels."""

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
                "title": "Monthly Sales Analysis",
                "x_axis_label": None,
                "y_axis_label": None,
            }
        ],
    )

    built_class = build(
        Options(
            weight=1,
            required_files=("submission.xlsx",),
            sheet="Sheet1",
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_chart_metadata_match_reference_0")
    test_method = built_instance.test_chart_metadata_match_reference_0
    test_method()

    assert test_method.__score__ == test_method.__weight__


def test_wrong_axis_labels_pass_by_default(fix_syspath):
    """Axis labels unlike the reference pass when labels are not graded."""

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
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_chart_metadata_match_reference_0")
    test_method = built_instance.test_chart_metadata_match_reference_0
    test_method()

    assert test_method.__score__ == test_method.__weight__


def test_pairs_by_chart_type_before_title(fix_syspath):
    """Type-distinct charts pair by type even when the titles cross."""

    write_chart_workbook(
        fix_syspath / "reference.xlsx",
        chart_specs=[
            {
                "title": "Alpha Trend",
                "x_axis_label": "Month",
                "y_axis_label": "Revenue",
                "values_col": 2,
            },
            {
                "title": "Beta Comparison",
                "x_axis_label": "Month",
                "y_axis_label": "Cost",
                "values_col": 3,
                "kind": "bar",
            },
        ],
    )
    # The line chart carries the bar chart's title and vice versa.  Type
    # pairing must still grade line-against-line and bar-against-bar.
    write_chart_workbook(
        fix_syspath / "submission.xlsx",
        chart_specs=[
            {
                "title": "Beta Comparison",
                "x_axis_label": "Month",
                "y_axis_label": "Revenue",
                "values_col": 2,
            },
            {
                "title": "Alpha Trend",
                "x_axis_label": "Month",
                "y_axis_label": "Cost",
                "values_col": 3,
                "kind": "bar",
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


def test_wrong_chart_type_fails(fix_syspath):
    """A wrong chart type fails with the type message, not a title message."""

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
                "title": "Sales by Month",
                "x_axis_label": "Month",
                "y_axis_label": "Revenue Dollars",
                "kind": "bar",
            }
        ],
    )

    built_class = build(
        Options(
            weight=1,
            required_files=("submission.xlsx",),
            sheet="Sheet1",
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_chart_metadata_match_reference_0")
    test_method = built_instance.test_chart_metadata_match_reference_0

    with pytest.raises(AssertionError) as exc_info:
        test_method()

    assert "chart type" in str(exc_info.value)
    assert test_method.__score__ == 0


def test_split_series_equivalent_passes(fix_syspath):
    """One series of N points equals N single-point series."""

    write_chart_workbook(
        fix_syspath / "reference.xlsx",
        chart_specs=[
            {
                "title": "Cost by Month",
                "x_axis_label": "Month",
                "y_axis_label": "Cost",
                "kind": "bar",
            }
        ],
    )
    write_chart_workbook(
        fix_syspath / "submission.xlsx",
        chart_specs=[
            {
                "title": "Monthly Cost Comparison",
                "x_axis_label": "Month",
                "y_axis_label": "Cost",
                "kind": "bar",
                "split_series": True,
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


def test_missing_data_points_fail(fix_syspath):
    """A chart plotting fewer total values than the reference still fails."""

    write_chart_workbook(
        fix_syspath / "reference.xlsx",
        chart_specs=[
            {
                "title": "Cost by Month",
                "x_axis_label": "Month",
                "y_axis_label": "Cost",
                "kind": "bar",
            }
        ],
    )
    write_chart_workbook(
        fix_syspath / "submission.xlsx",
        chart_specs=[
            {
                "title": "Cost by Month",
                "x_axis_label": "Month",
                "y_axis_label": "Cost",
                "kind": "bar",
                "max_row": 4,
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

    message = " ".join(str(exc_info.value).split())
    assert "plots 3 data values" in message
    assert test_method.__score__ == 0


def test_scatter_axis_labels_extracted_by_position(fix_syspath):
    """Scatter charts (two valAx) report x and y labels by axis position."""

    path = fix_syspath / "scatter.xlsx"
    write_chart_workbook(
        path,
        chart_specs=[
            {
                "title": "Sales vs Month Index",
                "x_axis_label": "Month Index",
                "y_axis_label": "Revenue Dollars",
                "kind": "scatter",
            }
        ],
    )

    charts = extract_chart_info_from_workbook(str(path), sheet="Sheet1")
    assert len(charts) == 1
    assert charts[0]["x_axis_label"] == "Month Index"
    assert charts[0]["y_axis_label"] == "Revenue Dollars"
    assert charts[0]["types"] == ["scatterChart"]


def test_fewer_charts_than_reference_fails(fix_syspath):
    """More reference charts than submission charts fails with a clear message."""

    write_chart_workbook(
        fix_syspath / "reference.xlsx",
        chart_specs=[
            {"title": "Alpha Trend", "values_col": 2},
            {"title": "Beta Trend", "values_col": 3},
        ],
    )
    write_chart_workbook(
        fix_syspath / "submission.xlsx",
        chart_specs=[{"title": "Alpha Trend", "values_col": 2}],
    )

    built_class = build(
        Options(
            weight=1,
            required_files=("submission.xlsx",),
            sheet="Sheet1",
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_chart_metadata_match_reference_0")
    test_method = built_instance.test_chart_metadata_match_reference_0

    with pytest.raises(AssertionError) as exc_info:
        test_method()

    message = " ".join(str(exc_info.value).split())
    assert "more charts" in message
    assert test_method.__score__ == 0


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


def test_unit_abbreviation_in_axis_label_passes(fix_syspath):
    """An axis label that abbreviates the unit passes under axis grading.

    The reference writes the unit out and names the variable; a student who
    writes ``Applied Load (N)`` has labeled the same axis.
    """

    write_chart_workbook(
        fix_syspath / "reference.xlsx",
        chart_specs=[
            {
                "title": "Beam Deflection",
                "x_axis_label": "Applied Load (P) [Newtons]",
                "y_axis_label": "Deflection (δ) [mm]",
                "kind": "scatter",
            }
        ],
    )
    write_chart_workbook(
        fix_syspath / "submission.xlsx",
        chart_specs=[
            {
                "title": "Load vs Deflection",
                "x_axis_label": "Applied Load (N)",
                "y_axis_label": "Deflection (millimeters)",
                "kind": "scatter",
            }
        ],
    )

    built_class = build(
        Options(
            weight=1,
            required_files=("submission.xlsx",),
            sheet="Sheet1",
            chart_grade_axis_labels=True,
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_chart_metadata_match_reference_0")
    test_method = built_instance.test_chart_metadata_match_reference_0
    test_method()

    assert test_method.__score__ == test_method.__weight__


def test_wrong_unit_in_axis_label_fails_when_labels_graded(fix_syspath):
    """The opt-in axis flag restores the unit gate as well as the ratio.

    The similarity ratio alone cannot catch this: ``cm`` for ``mm`` costs
    one character against a long label and clears 0.9.
    """

    write_chart_workbook(
        fix_syspath / "reference.xlsx",
        chart_specs=[
            {
                "title": "Beam Deflection",
                "x_axis_label": "Applied Load (P) [Newtons]",
                "y_axis_label": "Deflection (δ) [mm]",
                "kind": "scatter",
            }
        ],
    )
    write_chart_workbook(
        fix_syspath / "submission.xlsx",
        chart_specs=[
            {
                "title": "Load vs Deflection",
                "x_axis_label": "Applied Load (P) [N]",
                "y_axis_label": "Deflection (δ) [cm]",
                "kind": "scatter",
            }
        ],
    )

    built_class = build(
        Options(
            weight=1,
            required_files=("submission.xlsx",),
            sheet="Sheet1",
            chart_grade_axis_labels=True,
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_chart_metadata_match_reference_0")
    test_method = built_instance.test_chart_metadata_match_reference_0

    with pytest.raises(AssertionError) as exc_info:
        test_method()

    message = " ".join(str(exc_info.value).split())
    assert "y_axis_label" in message
    assert "different unit" in message
    # The reference label wording must not leak either.
    assert "mm" not in message
    assert test_method.__score__ == 0


def test_wrong_unit_in_axis_label_passes_by_default(fix_syspath):
    """A wrong-unit label passes when the task does not grade labels."""

    write_chart_workbook(
        fix_syspath / "reference.xlsx",
        chart_specs=[
            {
                "title": "Beam Deflection",
                "x_axis_label": "Applied Load (P) [Newtons]",
                "y_axis_label": "Deflection (δ) [mm]",
                "kind": "scatter",
            }
        ],
    )
    write_chart_workbook(
        fix_syspath / "submission.xlsx",
        chart_specs=[
            {
                "title": "Load vs Deflection",
                "x_axis_label": "Applied Load (P) [N]",
                "y_axis_label": "Deflection (δ) [cm]",
                "kind": "scatter",
            }
        ],
    )

    built_class = build(
        Options(
            weight=1,
            required_files=("submission.xlsx",),
            sheet="Sheet1",
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_chart_metadata_match_reference_0")
    test_method = built_instance.test_chart_metadata_match_reference_0
    test_method()

    assert test_method.__score__ == test_method.__weight__


def test_bar_3d_chart_matches_2d_bar_reference(fix_syspath):
    """A 3-D bar chart grades as the 2-D bar chart the reference expects."""

    write_chart_workbook(
        fix_syspath / "reference.xlsx",
        chart_specs=[
            {
                "title": "Cost by Month",
                "x_axis_label": "Month",
                "y_axis_label": "Cost",
                "kind": "bar",
            }
        ],
    )
    write_chart_workbook(
        fix_syspath / "submission.xlsx",
        chart_specs=[
            {
                "title": "Cost by Month",
                "x_axis_label": "Month",
                "y_axis_label": "Cost",
                "kind": "bar3d",
            }
        ],
    )

    built_class = build(
        Options(
            weight=1,
            required_files=("submission.xlsx",),
            sheet="Sheet1",
            chart_grade_axis_labels=True,
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_chart_metadata_match_reference_0")
    test_method = built_instance.test_chart_metadata_match_reference_0
    test_method()

    assert test_method.__score__ == test_method.__weight__


def test_bar_3d_chart_type_is_extracted_as_3d(fix_syspath):
    """The extractor reports the raw type; only the comparison folds it."""

    path = fix_syspath / "bar3d.xlsx"
    write_chart_workbook(
        path,
        chart_specs=[{"title": "Cost by Month", "kind": "bar3d"}],
    )

    charts = extract_chart_info_from_workbook(str(path), sheet="Sheet1")
    assert charts[0]["types"] == ["bar3DChart"]
    assert normalized_chart_types(charts[0]) == ["barChart"]


def test_horizontal_bar_axis_labels_map_by_role(fix_syspath):
    """A horizontal bar chart maps its category axis to x, not by position.

    Excel puts the category axis on the LEFT for a horizontal bar chart,
    so mapping axes by rendered position compares both labels against the
    wrong reference axis.
    """

    path = fix_syspath / "horizontal.xlsx"
    write_chart_workbook(
        path,
        chart_specs=[
            {
                "title": "Cost by Month",
                "x_axis_label": "Month",
                "y_axis_label": "Cost (dollars)",
                "kind": "bar",
                "horizontal": True,
            }
        ],
    )

    charts = extract_chart_info_from_workbook(str(path), sheet="Sheet1")
    assert charts[0]["x_axis_label"] == "Month"
    assert charts[0]["y_axis_label"] == "Cost (dollars)"


def test_horizontal_bar_passes_axis_grading(fix_syspath):
    """Correct labels on a horizontal bar chart pass opt-in axis grading."""

    write_chart_workbook(
        fix_syspath / "reference.xlsx",
        chart_specs=[
            {
                "title": "Cost by Month",
                "x_axis_label": "Month",
                "y_axis_label": "Cost (dollars)",
                "kind": "bar",
                "horizontal": True,
            }
        ],
    )
    write_chart_workbook(
        fix_syspath / "submission.xlsx",
        chart_specs=[
            {
                "title": "Monthly Cost",
                "x_axis_label": "Month",
                "y_axis_label": "Cost (dollars)",
                "kind": "bar",
                "horizontal": True,
            }
        ],
    )

    built_class = build(
        Options(
            weight=1,
            required_files=("submission.xlsx",),
            sheet="Sheet1",
            chart_grade_axis_labels=True,
            kwargs={"reference_file": "reference.xlsx"},
        )
    )
    built_instance = built_class(methodName="test_chart_metadata_match_reference_0")
    test_method = built_instance.test_chart_metadata_match_reference_0
    test_method()

    assert test_method.__score__ == test_method.__weight__
