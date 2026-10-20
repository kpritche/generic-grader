import datetime
import inspect
from collections.abc import Callable

from attrs import Factory, define
from parameterized import param


def options_to_params(options):
    try:
        return [param(o) for o in options]
    except TypeError:  # non-iterable
        return [param(options)]


@define(kw_only=True, frozen=True)
class Options:
    # Base
    weight: int | float = 0
    init: Callable | None = None
    ref_module: str = "tests.reference"
    sub_module: str = ""
    required_files: tuple = ()
    ignored_files: tuple = ()
    hint: str = ""
    patches: list[dict[str, list[str, Callable]]] = Factory(list)
    """
    There are some functions that cannot be patched due to other functions being dependent on their behavior.
    As of right now, those functions are `str` and `int`.
    """

    # Input
    entries: tuple = ()

    # Output
    interaction: int = 0
    start: int = 1
    n_lines: int | None = None
    line_n: int = 1
    value_n: int | None = None
    ratio: float = 1.0  # exact match
    log_limit: int = 0
    fixed_time: bool | datetime.datetime | str = False
    debug: bool = False
    time_limit: int = 1
    memory_limit_GB: float = 1.4

    # Callable
    obj_name: str = "main"
    args: tuple = ()
    kwargs: dict = Factory(dict)
    expected_set: set = Factory(set)
    expected_perms: set = Factory(set)
    validator: Callable | None = None

    # File
    filenames: tuple = ()

    # Code
    expected_minimum_depth: int = 1

    # Programming standards (style.header, style.structure, ...)
    # A standards check with weight 0 and a deduction costs `deduction` points
    # when it fails and nothing when it passes, so it never changes a task's
    # point total.
    deduction: int | float = 0.0
    max_violations: int | None = None  # None uses the check's own default
    max_line_length: int = 99
    # Names and numbers the reference solution uses are always allowed; these
    # add to them.
    allowed_names: tuple = ()
    allowed_literals: tuple = ()

    # Plots / Image (see #156 for planned Enum replacement)
    prop: str = ""
    prop_kwargs: dict = Factory(dict)

    # Stats
    expected_distribution: dict = {0: 0}
    relative_tolerance: float = 1e-7
    absolute_tolerance: float = 0.0

    # Image
    mode: str = "exactly"
    ref_image: str = "sol_inv.png"
    sub_image: str = "tests/output.png"
    region_inner: str = ""
    region_outer: str = ""
    threshold: int = 0
    delta: int = 0
    expected_words: str = ""

    # Random_func_calls
    random_func_calls: list[str] = Factory(list)
    random_chance_tolerance: int = 9
    # This is the probabilty that we miss a possible outcome, by default it is set to 1 in a billion

    # Excel
    sheet: str = ""
    range_matches_reference: bool = True
    series_require_formulas: bool = False
    # Compare string cells by the units they name rather than by their text.
    # Spelling stops mattering, so "%", "percent", "per cent" and
    # "percentage" are one answer; so does any description wrapped around
    # the unit, so "percent of households" names the same unit as
    # "percent".  A blank cell reads as "this quantity has no unit" and
    # matches a dimensionless reference, and nothing else.  A different
    # unit still fails.  Numeric cells are unaffected.
    #
    # Turn this on only for a range whose cells hold units.  Never turn it
    # on for a range holding a graded word such as Yes or No: against a
    # reference that names no unit the comparison falls back to canonical
    # text, but a blank answer would still be scored on unit rules rather
    # than on the word the task asked for.
    series_canonicalize_units: bool = False
    # When a same-location series check fails, search the sheet for the
    # intact series (same orientation, at least 3 values) and award credit
    # if it is found and satisfies the same formula requirement.  Set False
    # to require the exact template location.
    series_allow_relocation: bool = True
    chart_ratio: float = 0.9
    chart_fields: tuple = ("title", "x_axis_label", "y_axis_label")
    # When True, every chart on the sheet must carry a meaningful
    # title.  Like `chart_title_match_reference`, this flag is inert
    # unless `chart_grade_title` is also True -- the policy is exactly
    # two opt-in flags, so no third lever may re-enable title grading on
    # a task that has opted out.
    chart_require_title: bool = False
    # Chart checks grade three things by default: that the chart exists on
    # the named sheet, that its chart type is correct, and that it plots
    # the expected number of data values.  Wording -- the chart title and
    # the axis labels -- is NOT graded by default, because most tasks do
    # not prescribe it.  The two flags below opt a task back in.
    #
    # When True, the chart title is graded.  Presence alone by default: the
    # title must be present and meaningful.  Combine with
    # `chart_title_match_reference` to also require similarity to the
    # reference title.  When False, the title is ignored entirely: a blank
    # title passes, and charts are identified by chart type rather than by
    # title.
    chart_grade_title: bool = False
    # When True, the axis labels are graded.  Each must be present and
    # meaningful, must carry the same unit as the corresponding reference
    # label when both name a unit, and must reach `chart_ratio` similarity
    # once units are canonicalized.  When False, axis labels are ignored
    # entirely: blank, wrong, and wrong-unit labels all pass.
    chart_grade_axis_labels: bool = False
    # When True, the chart title must be similar to the reference title,
    # and the title is also used to identify which submitted chart to
    # grade (legacy behavior; use only when the task prescribes the exact
    # title).  This flag is inert unless `chart_grade_title` is also True:
    # identifying a chart by its title is itself a form of title grading,
    # so it must not reach a task that has opted out of grading titles.
    chart_title_match_reference: bool = False
    # Semantic data-table matching (used by data_table_match_reference)
    header_ratio: float = 0.9
    strict_headers: bool = False
    strict_column_order: bool = False

    def __attrs_post_init__(self):
        """Check that the attributes are of the correct type."""
        annotations = type(self).__annotations__
        for attr in annotations:
            if attr == "init":
                expected_type = (Callable, type(None))
                attr_type = f"<class 'function'> or {type(None)}. "
            elif attr == "patches":
                expected_type = list
                attr_type = f"{list}. "
            elif attr == "random_func_calls":
                expected_type = list
                attr_type = f"{list}. "
            else:
                expected_type = annotations[attr]
                attr_type = f"{annotations[attr]}. "
            if not isinstance(getattr(self, attr), expected_type):
                raise ValueError(
                    f"`{attr}` must be of type "
                    + attr_type
                    + f"Got {type(getattr(self, attr))} instead."
                )
        for name in ["filenames", "required_files", "ignored_files"]:
            attr = getattr(self, name)
            if attr == ():
                continue
            s = set(attr)
            if len(s) != len(attr):
                raise ValueError(f"Duplicate entries in {name}.")
        if self.init is not None:
            sig = inspect.signature(self.init)
            positional_kinds = (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.VAR_POSITIONAL,
            )
            max_positional = 0
            for p in sig.parameters.values():
                if p.kind == inspect.Parameter.VAR_POSITIONAL:
                    max_positional = float("inf")
                    break
                if p.kind in positional_kinds:
                    max_positional += 1
            if max_positional < 2:
                raise ValueError(
                    f"`init` must accept 2 positional arguments"
                    f" (test, options), but accepts {max_positional}."
                )
        if self.mode not in ["exactly", "less than", "more than", "approximately"]:
            raise ValueError(
                "`mode` must be one of 'exactly', 'less than', 'more than', or 'approximately'."
            )
