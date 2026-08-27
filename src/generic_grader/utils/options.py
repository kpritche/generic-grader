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
    # When a same-location series check fails, search the sheet for the
    # intact series (same orientation, at least 3 values) and award credit
    # if it is found and satisfies the same formula requirement.  Set False
    # to require the exact template location.
    series_allow_relocation: bool = True
    chart_ratio: float = 0.9
    chart_fields: tuple = ("title", "x_axis_label", "y_axis_label")
    chart_require_title: bool = False
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
