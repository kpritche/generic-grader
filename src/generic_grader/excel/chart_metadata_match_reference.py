"""Test that chart metadata in a workbook matches a reference workbook."""

import unittest

from parameterized import parameterized
from rapidfuzz.distance.Levenshtein import normalized_similarity

from generic_grader.excel._units import canonicalize_label, label_unit
from generic_grader.excel._workbook import (
    extract_chart_info_from_workbook,
    resolve_reference_file,
    resolve_submission_file,
)
from generic_grader.utils.decorators import merge_subtests, weighted
from generic_grader.utils.docs import get_wrapper
from generic_grader.utils.options import options_to_params


def _normalize_text(text: str | None) -> str:
    if text is None:
        return ""
    lowered = text.lower()
    filtered = "".join(ch if ch.isalnum() else " " for ch in lowered)
    return " ".join(filtered.split())


def _is_meaningful(text: str | None) -> bool:
    normalized = _normalize_text(text)
    return bool(normalized)


def _similarity(actual: str | None, expected: str | None) -> float:
    actual_normalized = _normalize_text(actual)
    expected_normalized = _normalize_text(expected)
    if not actual_normalized and not expected_normalized:
        return 1.0
    return normalized_similarity(actual_normalized, expected_normalized)


def _label_is_meaningful(text: str | None) -> bool:
    return bool(canonicalize_label(text))


def _units_differ(actual: str | None, expected: str | None) -> bool:
    """True when both labels carry a recognized unit and the units differ.

    The similarity ratio cannot see this on its own: once units are
    abbreviated, ``cm`` for ``mm`` costs one character against a long
    label and still clears the ratio.
    """

    actual_unit = label_unit(actual)
    expected_unit = label_unit(expected)
    return (
        actual_unit is not None
        and expected_unit is not None
        and actual_unit != expected_unit
    )


def _label_similarity(actual: str | None, expected: str | None) -> float:
    """Compare axis labels with their units spelled one way.

    ``Applied Load (N)`` and ``Applied Load (P) [Newtons]`` describe the
    same axis; see ``canonicalize_label``.
    """

    actual_canonical = canonicalize_label(actual)
    expected_canonical = canonicalize_label(expected)
    if not actual_canonical and not expected_canonical:
        return 1.0
    return normalized_similarity(actual_canonical, expected_canonical)


def _normalize_chart_type(chart_type: str) -> str:
    """Return a chart type with its 3-D variant folded onto the 2-D name.

    Excel writes a 3-D bar chart as ``bar3DChart`` and a flat one as
    ``barChart``.  The two render the same data the same way, so a student
    who picked the 3-D style from the chart gallery has made the chart the
    task asked for.  The same holds for the line, pie, area, and surface
    families.  Scatter charts have no 3-D form, so nothing changes there.
    """

    return chart_type.replace("3D", "")


def normalized_chart_types(chart: dict) -> list[str]:
    """Return a chart's types, sorted, with 3-D variants folded in."""

    return sorted(_normalize_chart_type(name) for name in chart.get("types", []))


def _total_points(chart: dict):
    """Sum the plotted data points across a chart's series.

    Returns None when any series' point count is unknown, so callers can
    fall back to comparing series counts.
    """

    series = chart.get("series", [])
    if not series:
        return None
    total = 0
    for entry in series:
        count = entry.get("point_count")
        if count is None:
            return None
        total += count
    return total


def _describe_titles(charts: list[dict]) -> str:
    """Summarize the titles found on a set of charts, for student feedback."""

    titles = [chart.get("title") for chart in charts if _is_meaningful(chart.get("title"))]
    if not titles:
        return "None of the charts on that sheet have a title."
    quoted = ", ".join(f"`{title.strip()}`" for title in titles)
    plural = "titles" if len(titles) > 1 else "title"
    return f"The chart {plural} found there: {quoted}."


def _match_reference_to_submission(
    ref_charts: list[dict],
    sub_charts: list[dict],
    ratio: float,
    sheet: str | None = None,
    hint: str = "",
    wrapper=None,
):
    """Pair each reference chart with the submission chart whose title is closest.

    The failure message deliberately does NOT quote the reference chart's
    title.  On assignments where writing the title is part of the graded
    work, echoing the expected title hands the student the answer.  Report
    what the submission contains instead, and let the assignment's own hint
    say where to look.
    """

    available = sub_charts.copy()
    pairs = []

    for ref_chart in ref_charts:
        ref_title = ref_chart.get("title")
        if not _is_meaningful(ref_title):
            raise AssertionError(
                "Reference chart is missing a meaningful title on the selected sheet."
            )

        best_match = None
        best_ratio = -1.0
        for sub_chart in available:
            score = _similarity(sub_chart.get("title"), ref_title)
            if score > best_ratio:
                best_ratio = score
                best_match = sub_chart

        if best_match is None or best_ratio < ratio:
            where = f" on sheet `{sheet}`" if sheet else ""
            message = (
                f"No chart{where} has a title close enough to the one this"
                " check expects, so the chart could not be identified."
                f"  {_describe_titles(sub_charts)}"
                "  Confirm the chart the instructions ask for is on that"
                " sheet, and that its title describes what the chart plots."
                + (hint and f"  {hint}" or "")
            )
            if wrapper is not None:
                message = "\n\nHint:\n" + wrapper.fill(message)
            raise AssertionError(message)

        available.remove(best_match)
        pairs.append((ref_chart, best_match))

    return pairs


def _pair_reference_to_submission(
    ref_charts: list[dict],
    sub_charts: list[dict],
    sheet: str | None = None,
    hint: str = "",
    wrapper=None,
):
    """Pair each reference chart with a submission chart by chart type.

    Unlike ``_match_reference_to_submission``, the pairing never fails on
    title dissimilarity: students author their own titles, so the title
    cannot identify the chart.  Candidates whose chart type matches the
    reference are preferred; among several candidates, the closest title
    wins as a deterministic tie-break.  Pairing fails only when the
    submission has fewer charts than the reference expects.
    """

    available = sub_charts.copy()
    pairs = []

    for ref_chart in ref_charts:
        ref_types = normalized_chart_types(ref_chart)
        typed = [
            chart
            for chart in available
            if normalized_chart_types(chart) == ref_types
        ]
        candidates = typed or available

        if not candidates:
            where = f" on sheet `{sheet}`" if sheet else ""
            message = (
                f"The reference workbook expects more charts{where} than your"
                " submission contains, so one of the expected charts could"
                " not be found."
                f"  {_describe_titles(sub_charts)}"
                + (hint and f"  {hint}" or "")
            )
            if wrapper is not None:
                message = "\n\nHint:\n" + wrapper.fill(message)
            raise AssertionError(message)

        ref_title = ref_chart.get("title")
        best_match = max(
            candidates,
            key=lambda chart: (
                _similarity(chart.get("title"), ref_title),
                str(chart.get("chart_file")),
            ),
        )
        available.remove(best_match)
        pairs.append((ref_chart, best_match))

    return pairs


def graded_metadata_fields(o) -> tuple[str, ...]:
    """Return the metadata fields this check grades, in `chart_fields` order.

    Titles and axis labels are graded only when the task opts in with
    `chart_grade_title` or `chart_grade_axis_labels`.  With neither flag
    set the tuple is empty and the check grades chart type and plotted
    data points alone.
    """

    fields = []
    for field in o.chart_fields:
        if field == "title":
            if o.chart_grade_title:
                fields.append(field)
        elif o.chart_grade_axis_labels:
            fields.append(field)
    return tuple(fields)


def requires_a_title(o) -> bool:
    """Return True when every chart on the sheet must carry a title.

    `chart_require_title` is a third way to grade a title, so it is
    gated the same way `chart_title_match_reference` is: the policy is
    exactly two opt-in flags, and a task that has not set
    `chart_grade_title` grades nothing about titles.
    """

    return bool(o.chart_grade_title and o.chart_require_title)


def grades_title_by_similarity(o) -> bool:
    """Return True when the title must resemble the reference title.

    `chart_title_match_reference` is inert on its own.  Identifying a
    chart by its title fails a student whose title reads differently, so
    it must not reach a task that has opted out of grading titles.
    """

    return bool(o.chart_grade_title and o.chart_title_match_reference)


def doc_func(func, num, param):
    """Return parameterized docstring for chart metadata checks."""

    o = param.args[0]
    clauses = []
    if o.chart_grade_title:
        if o.chart_title_match_reference:
            clauses.append("has a title similar to the reference workbook")
        else:
            clauses.append("has a descriptive title")
    if o.chart_grade_axis_labels:
        clauses.append("has axis labels similar to the reference workbook")

    summary = (
        f"Check that the chart on sheet `{o.sheet}` is the expected chart"
        " type and plots the expected data"
    )
    if clauses:
        summary += ", and " + " and ".join(clauses)
    return summary + "."


def build(the_options):
    """Create a class for chart metadata-to-reference checks."""

    the_params = options_to_params(the_options)

    class TestChartMetadataMatchReference(unittest.TestCase):
        """A class for chart metadata matching tests."""

        wrapper = get_wrapper()

        @parameterized.expand(the_params, doc_func=doc_func)
        @merge_subtests()
        @weighted
        def test_chart_metadata_match_reference(self, options):
            """Check chart type and plotted data against reference workbook.

            Title and axis-label wording are graded only when the task
            sets `chart_grade_title` or `chart_grade_axis_labels`.
            """

            o = options
            sub_file = resolve_submission_file(o)
            reference_file = resolve_reference_file(o)

            ref_charts = extract_chart_info_from_workbook(reference_file, sheet=o.sheet)
            sub_charts = extract_chart_info_from_workbook(sub_file, sheet=o.sheet)

            self.assertTrue(
                ref_charts,
                msg=(
                    "\n\nHint:\n"
                    + self.wrapper.fill(
                        f"No charts were found in the reference workbook on sheet `{o.sheet}`."
                    )
                ),
            )

            self.assertTrue(
                sub_charts,
                msg=(
                    "\n\nHint:\n"
                    + self.wrapper.fill(
                        f"No charts were found in your workbook on sheet `{o.sheet}`."
                        + (o.hint and f"  {o.hint}" or "")
                    )
                ),
            )

            if requires_a_title(o):
                for chart in sub_charts:
                    with self.subTest(chart=chart.get("chart_file")):
                        self.assertTrue(
                            _is_meaningful(chart.get("title")),
                            msg=(
                                "\n\nHint:\n"
                                + self.wrapper.fill(
                                    f"Chart `{chart.get('chart_file')}` on sheet `{o.sheet}`"
                                    " is missing a meaningful title."
                                    + (o.hint and f"  {o.hint}" or "")
                                )
                            ),
                        )

            if grades_title_by_similarity(o):
                matched_charts = _match_reference_to_submission(
                    ref_charts,
                    sub_charts,
                    o.chart_ratio,
                    sheet=o.sheet,
                    hint=o.hint,
                    wrapper=self.wrapper,
                )
            else:
                matched_charts = _pair_reference_to_submission(
                    ref_charts,
                    sub_charts,
                    sheet=o.sheet,
                    hint=o.hint,
                    wrapper=self.wrapper,
                )

            for ref_chart, sub_chart in matched_charts:
                # --- structural checks (always enforced) ---
                with self.subTest(chart=sub_chart.get("chart_file"), field="chart_type"):
                    # 3-D variants count as their 2-D type, so a student who
                    # picked a 3-D bar chart is not failed for the styling.
                    # The message quotes the types as written in the files.
                    ref_types = sorted(ref_chart.get("types", []))
                    sub_types = sorted(sub_chart.get("types", []))
                    self.assertEqual(
                        normalized_chart_types(ref_chart),
                        normalized_chart_types(sub_chart),
                        msg=(
                            "\n\nHint:\n"
                            + self.wrapper.fill(
                                f"Chart `{sub_chart.get('chart_file')}` on sheet"
                                f" `{o.sheet}` has chart type(s) {sub_types},"
                                f" but the reference expects {ref_types}."
                                + (o.hint and f"  {o.hint}" or "")
                            )
                        ),
                    )

                with self.subTest(chart=sub_chart.get("chart_file"), field="series_count"):
                    # Splitting one series into several (one per category)
                    # renders the same chart, so compare the total number
                    # of plotted data points rather than the series count.
                    # Fall back to the series count only when a point
                    # count could not be extracted on either side.
                    ref_total = _total_points(ref_chart)
                    sub_total = _total_points(sub_chart)
                    if ref_total is not None and sub_total is not None:
                        self.assertEqual(
                            ref_total,
                            sub_total,
                            msg=(
                                "\n\nHint:\n"
                                + self.wrapper.fill(
                                    f"Chart `{sub_chart.get('chart_file')}` on sheet"
                                    f" `{o.sheet}` plots {sub_total} data"
                                    f" value{'s' if sub_total != 1 else ''},"
                                    f" but the reference expects {ref_total}."
                                    + (o.hint and f"  {o.hint}" or "")
                                )
                            ),
                        )
                    else:
                        ref_count = len(ref_chart.get("series", []))
                        sub_count = len(sub_chart.get("series", []))
                        self.assertEqual(
                            ref_count,
                            sub_count,
                            msg=(
                                "\n\nHint:\n"
                                + self.wrapper.fill(
                                    f"Chart `{sub_chart.get('chart_file')}` on sheet"
                                    f" `{o.sheet}` has {sub_count} data series,"
                                    f" but the reference expects {ref_count}."
                                    + (o.hint and f"  {o.hint}" or "")
                                )
                            ),
                        )

                # --- metadata checks (opt-in; see graded_metadata_fields) ---
                for field in graded_metadata_fields(o):
                    with self.subTest(chart=sub_chart.get("chart_file"), field=field):
                        expected = ref_chart.get(field)
                        actual = sub_chart.get(field)
                        if expected is None:
                            continue

                        # Titles are compared as written.  Axis labels are
                        # compared with their units canonicalized, so the
                        # spelling of a unit never decides the grade.
                        is_title = field == "title"
                        meaningful = _is_meaningful if is_title else _label_is_meaningful
                        similarity = _similarity if is_title else _label_similarity

                        self.assertTrue(
                            meaningful(actual),
                            msg=(
                                "\n\nHint:\n"
                                + self.wrapper.fill(
                                    f"The `{field}` for chart `{sub_chart.get('chart_file')}`"
                                    f" on sheet `{o.sheet}` is missing or not meaningful."
                                    + (o.hint and f"  {o.hint}" or "")
                                )
                            ),
                        )

                        # Students author their own titles, so a title is
                        # graded on presence, not on similarity to the
                        # reference, unless the check opts in to strict
                        # title matching.
                        if is_title and not grades_title_by_similarity(o):
                            continue

                        if not is_title:
                            self.assertFalse(
                                _units_differ(actual, expected),
                                msg=(
                                    "\n\nHint:\n"
                                    + self.wrapper.fill(
                                        f"The `{field}` for chart `{sub_chart.get('chart_file')}`"
                                        " carries a different unit than the reference chart."
                                        + (o.hint and f"  {o.hint}" or "")
                                    )
                                ),
                            )

                        ratio = similarity(actual, expected)
                        self.assertGreaterEqual(
                            ratio,
                            o.chart_ratio,
                            msg=(
                                "\n\nHint:\n"
                                + self.wrapper.fill(
                                    f"The `{field}` for chart `{sub_chart.get('chart_file')}`"
                                    " is not sufficiently similar to the reference chart."
                                    f" Required similarity: {o.chart_ratio:.2f}."
                                    + (o.hint and f"  {o.hint}" or "")
                                )
                            ),
                        )

            self.set_score(self, o.weight)

    return TestChartMetadataMatchReference
