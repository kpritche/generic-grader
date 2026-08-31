"""Shared workbook helpers for excel checks."""

import posixpath
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from openpyxl.utils.cell import range_boundaries
from openpyxl.utils.exceptions import InvalidFileException
from rapidfuzz.distance.Levenshtein import normalized_similarity

from generic_grader.utils.docs import get_wrapper
from generic_grader.utils.files import glob_ci, missing_file_message
from generic_grader.utils.options import Options

from openpyxl import load_workbook
from openpyxl.worksheet.formula import ArrayFormula

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    "s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "xdr": "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing",
}


def _hint(message: str) -> str:
    """Format *message* the way every check formats student feedback."""

    return "\n\nHint:\n" + get_wrapper().fill(message)


def fail_student(message: str):
    """Raise a graded failure carrying plain-language feedback.

    A grader-internal exception reaches the student as a traceback with
    no explanation of what to fix.  AssertionError is what unittest
    counts as a failed check, so a helper that raises one lets a
    resolution problem be reported the way an assertion failure is.
    """

    raise AssertionError(_hint(message))


def resolve_single_file(file_patterns: tuple[str, ...], label: str) -> str:
    """Resolve exactly one file from a tuple of file patterns."""

    if not file_patterns:
        raise ValueError(f"No {label} file pattern provided.")

    pattern = file_patterns[0]
    matches = glob_ci(pattern)

    if len(matches) == 0:
        if label == "submission":
            fail_student(missing_file_message(pattern))
        raise FileNotFoundError(
            f'Could not find a {label} file matching pattern "{pattern}".'
        )

    if len(matches) > 1:
        raise ValueError(
            f'Found multiple {label} files matching pattern "{pattern}".'
        )

    return matches[0]


def resolve_sheet_and_range(options):
    """Read sheet and cell-range settings from Options."""

    if len(options.entries) != 2:
        raise ValueError(
            "Excel checks require `entries=(start_cell, end_cell)`,"
            " e.g. ('A1', 'C4')."
        )

    sheet = options.kwargs.get("sheet") or options.sheet or None
    start_cell, end_cell = options.entries
    return sheet, start_cell, end_cell


NOT_A_WORKBOOK_HINT = (
    "could not be opened as an Excel workbook.  Make sure you upload a"
    " .xlsx workbook.  In Excel, use File > Save As and choose Excel"
    " Workbook (.xlsx).  An older .xls file, a PDF or document renamed"
    " to .xlsx, and a CSV will not open, even when the name looks right."
)


def open_workbook(path: str, data_only: bool):
    """Open a workbook, or fail with plain language if it is not one.

    openpyxl reports an ``.xls`` upload as ``InvalidFileException`` and a
    renamed PDF as ``BadZipFile: File is not a zip file``.  Neither tells
    a student what to do, and both reach the student as a traceback.
    """

    try:
        return load_workbook(filename=path, data_only=data_only)
    except (zipfile.BadZipFile, InvalidFileException, KeyError):
        fail_student(f"The file `{Path(path).name}` {NOT_A_WORKBOOK_HINT}")


def resolve_sheet_name(sheet_names, sheet: str) -> str | None:
    """Return the sheet in *sheet_names* that *sheet* names, or None.

    An exact match wins.  Failing that, the comparison ignores the case
    of letters and any surrounding whitespace, so renaming "Beam Data"
    to "Beam data" does not stop every check that reads the sheet.
    """

    names = list(sheet_names)
    if sheet in names:
        return sheet

    wanted = sheet.strip().casefold()
    for name in names:
        if name.strip().casefold() == wanted:
            return name
    return None


def missing_sheet_message(sheet: str, sheet_names) -> str:
    """Return the feedback for a sheet the workbook does not contain."""

    names = list(sheet_names)
    if names:
        quoted = ", ".join(f"`{name}`" for name in names)
        plural = "sheets" if len(names) > 1 else "sheet"
        found = f"  The {plural} in your workbook: {quoted}."
    else:
        found = "  Your workbook does not appear to contain any sheets."

    return (
        f"This check reads the sheet named `{sheet}`, but your workbook"
        " does not have a sheet with that name."
        f"{found}"
        "  Make sure that sheet is still in the workbook and still has"
        " the name the instructions give it.  Renaming or deleting it"
        " stops every check that reads it."
    )


def load_sheet(path: str, sheet: str | None, data_only: bool):
    """Load a workbook and return the requested sheet."""

    workbook = open_workbook(path, data_only=data_only)
    if not sheet:
        if not workbook.worksheets:
            raise ValueError(f"Workbook at '{path}' has no worksheets.")
        return workbook.worksheets[0]

    resolved = resolve_sheet_name(workbook.sheetnames, sheet)
    if resolved is None:
        fail_student(missing_sheet_message(sheet, workbook.sheetnames))
    return workbook[resolved]


def range_shape(start_cell: str, end_cell: str) -> tuple[int, int]:
    """Return (height, width) for an Excel range."""

    min_col, min_row, max_col, max_row = range_boundaries(f"{start_cell}:{end_cell}")
    return max_row - min_row + 1, max_col - min_col + 1


def iter_rect_windows(sheet, height: int, width: int):
    """Yield top-left row/column for each in-sheet rectangular window."""

    if height <= 0 or width <= 0:
        return

    max_row = sheet.max_row
    max_col = sheet.max_column
    if height > max_row or width > max_col:
        return

    for row in range(1, max_row - height + 2):
        for col in range(1, max_col - width + 2):
            yield row, col


def read_rect_values(sheet, start_row: int, start_col: int, height: int, width: int):
    """Read a rectangular block of values from a worksheet."""

    return [
        [sheet.cell(start_row + row, start_col + col).value for col in range(width)]
        for row in range(height)
    ]


def get_formula_text(value) -> str | None:
    """Return a cell value's formula text, or None if there is none to compare.

    Handles both ordinary string formulas (``"=A1+B1"``) and openpyxl's
    ``ArrayFormula`` objects (returned for array/CSE-entered formulas), so
    every excel check can ask "is this a formula, and what does it say"
    through one code path instead of re-deriving the answer per call site.

    Note: ``ArrayFormula.text`` can itself be ``None`` (openpyxl's
    ``ArrayFormula.__init__`` defaults ``text=None``), so a ``None`` return
    here does *not* always mean "not a formula" -- use `is_formula_value`
    for the existence check; use this only for text to compare/display.
    """

    if isinstance(value, ArrayFormula):
        return value.text

    if isinstance(value, str) and value.startswith("="):
        return value

    return None


def is_formula_value(value) -> bool:
    """Return True if *value* is a formula, ordinary or array-entered.

    Any ``ArrayFormula`` instance counts as a formula regardless of whether
    it carries text -- `get_formula_text` can legitimately return ``None``
    for an array formula (openpyxl allows ``text=None``), and that must not
    be misread as "not a formula".
    """

    if isinstance(value, ArrayFormula):
        return True

    return get_formula_text(value) is not None


def _rels_path_for_source(source_path: str) -> str:
    source_dir = posixpath.dirname(source_path)
    source_file = posixpath.basename(source_path)
    return posixpath.join(source_dir, "_rels", f"{source_file}.rels")


def _resolve_target(source_path: str, target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    source_dir = posixpath.dirname(source_path)
    return posixpath.normpath(posixpath.join(source_dir, target))


def _read_relationships(archive: zipfile.ZipFile, source_path: str) -> dict[str, str]:
    rels_path = _rels_path_for_source(source_path)
    if rels_path not in archive.namelist():
        return {}

    rels_xml = archive.read(rels_path)
    root = ET.fromstring(rels_xml)

    relationship_map = {}
    for relationship in root.findall("rel:Relationship", NS):
        rel_id = relationship.get("Id")
        target = relationship.get("Target")
        if rel_id and target:
            relationship_map[rel_id] = _resolve_target(source_path, target)

    return relationship_map


def _extract_title_text(parent_node):
    if parent_node is None:
        return None

    title_node = parent_node.find(".//c:title", NS)
    if title_node is None:
        return None

    text_nodes = title_node.findall(".//a:t", NS)
    text = "".join(node.text for node in text_nodes if node.text)
    return text or None


def _extract_chart_info(chart_xml: bytes, chart_file: str) -> dict:
    root = ET.fromstring(chart_xml)
    chart_info = {
        "chart_file": chart_file,
        "title": _extract_title_text(root),
        "x_axis_label": None,
        "y_axis_label": None,
        "types": [],
        "series": [],
    }

    # Map axes to x/y by their ROLE when the chart has a category axis:
    # the category axis is the x axis and the value axis is the y axis,
    # whatever the rendered position.  A horizontal bar chart (barDir=bar)
    # puts its category axis on the left and its value axis at the bottom,
    # so mapping by position alone compares both labels against the wrong
    # reference axis.  A date axis plays the same role as a category axis.
    #
    # Scatter charts carry two valAx and no catAx, so role cannot separate
    # them; there, and only there, fall back to the rendered position
    # (axPos: b/t = horizontal, l/r = vertical).  serAx (present on 3-D
    # charts) is the depth axis and is never x or y.
    axes = []
    for axis in root.findall(".//c:plotArea/*", NS):
        tag_name = axis.tag.split("}")[-1]
        if tag_name in ("catAx", "valAx", "dateAx"):
            axes.append((tag_name, axis))

    category_axes = [axis for tag_name, axis in axes if tag_name in ("catAx", "dateAx")]
    value_axes = [axis for tag_name, axis in axes if tag_name == "valAx"]

    if category_axes:
        chart_info["x_axis_label"] = _extract_title_text(category_axes[0])
        if value_axes:
            chart_info["y_axis_label"] = _extract_title_text(value_axes[0])
    else:
        for _tag_name, axis in axes:
            pos_node = axis.find("c:axPos", NS)
            pos = pos_node.get("val") if pos_node is not None else None
            if pos in ("b", "t") and chart_info["x_axis_label"] is None:
                chart_info["x_axis_label"] = _extract_title_text(axis)
            elif pos in ("l", "r") and chart_info["y_axis_label"] is None:
                chart_info["y_axis_label"] = _extract_title_text(axis)

        # A chart with no axPos at all still needs both slots filled.
        unlabeled = [
            axis
            for _tag_name, axis in axes
            if axis.find("c:axPos", NS) is None
        ]
        for axis in unlabeled:
            if chart_info["x_axis_label"] is None:
                chart_info["x_axis_label"] = _extract_title_text(axis)
            elif chart_info["y_axis_label"] is None:
                chart_info["y_axis_label"] = _extract_title_text(axis)

    plot_area = root.find(".//c:plotArea", NS)
    if plot_area is not None:
        for child in plot_area:
            tag_name = child.tag.split("}")[-1]
            if tag_name.endswith("Chart"):
                chart_info["types"].append(tag_name)

    for i, series in enumerate(root.findall(".//c:ser", NS), start=1):
        series_info = {
            "series_number": i,
            "x_range": None,
            "y_range": None,
            "point_count": None,
        }
        cat_formula = series.find(".//c:cat//c:f", NS)
        if cat_formula is not None:
            series_info["x_range"] = cat_formula.text

        # Scatter series carry their values under c:yVal; every other
        # chart type uses c:val.
        val_node = series.find("c:val", NS)
        if val_node is None:
            val_node = series.find("c:yVal", NS)
        if val_node is not None:
            val_formula = val_node.find(".//c:f", NS)
            if val_formula is not None:
                series_info["y_range"] = val_formula.text
            series_info["point_count"] = _extract_point_count(
                val_node, series_info["y_range"]
            )

        chart_info["series"].append(series_info)

    return chart_info


_RANGE_RE = re.compile(
    r"\$?([A-Z]{1,3})\$?(\d+)(?::\$?([A-Z]{1,3})\$?(\d+))?$"
)


def _extract_point_count(val_node, range_formula):
    """Count the data points a series plots.

    Prefer the cached point count Excel writes next to the range; fall
    back to counting cached points, then to the span of the range
    formula. Returns None when none of those are available.
    """

    pt_count = val_node.find(".//c:ptCount", NS)
    if pt_count is not None and pt_count.get("val", "").isdigit():
        return int(pt_count.get("val"))

    points = val_node.findall(".//c:pt", NS)
    if points:
        return len(points)

    if range_formula:
        match = _RANGE_RE.search(range_formula.split(",")[-1].strip())
        if match:
            col1, row1, col2, row2 = match.groups()
            if col2 is None:
                return 1
            if col1 == col2:
                return abs(int(row2) - int(row1)) + 1
            if row1 == row2:
                return abs(
                    _column_index(col2) - _column_index(col1)
                ) + 1

    return None


def _column_index(letters: str) -> int:
    index = 0
    for ch in letters:
        index = index * 26 + (ord(ch) - ord("A") + 1)
    return index


def extract_chart_info_from_workbook(xlsx_filepath: str, sheet: str | None = None) -> list[dict]:
    """Extract chart metadata from workbook XML for one sheet or all sheets."""

    workbook_chart_info = []
    try:
        archive = zipfile.ZipFile(xlsx_filepath, "r")
    except (zipfile.BadZipFile, OSError):
        fail_student(f"The file `{Path(xlsx_filepath).name}` {NOT_A_WORKBOOK_HINT}")

    with archive:
        workbook_path = "xl/workbook.xml"
        if workbook_path not in archive.namelist():
            fail_student(
                f"The file `{Path(xlsx_filepath).name}` {NOT_A_WORKBOOK_HINT}"
            )
        workbook_xml = archive.read(workbook_path)
        workbook_root = ET.fromstring(workbook_xml)
        workbook_relationships = _read_relationships(archive, workbook_path)

        sheet_nodes = workbook_root.findall("s:sheets/s:sheet", NS)
        all_sheet_names = [
            node.get("name") for node in sheet_nodes if node.get("name") is not None
        ]

        # Resolve the requested sheet to the name the workbook actually
        # uses.  Skipping past a miscased name would report "no charts
        # were found", which sends the student looking for a chart that
        # is there under a sheet name that is not.
        wanted_sheet = None
        if sheet:
            wanted_sheet = resolve_sheet_name(all_sheet_names, sheet)
            if wanted_sheet is None:
                fail_student(missing_sheet_message(sheet, all_sheet_names))

        for sheet_node in sheet_nodes:
            sheet_name = sheet_node.get("name")
            if wanted_sheet is not None and sheet_name != wanted_sheet:
                continue

            rel_id = sheet_node.get(f"{{{NS['r']}}}id")
            if rel_id is None or rel_id not in workbook_relationships:
                continue

            sheet_path = workbook_relationships[rel_id]
            sheet_xml = archive.read(sheet_path)
            sheet_root = ET.fromstring(sheet_xml)
            sheet_relationships = _read_relationships(archive, sheet_path)

            drawing_rel_ids = [
                node.get(f"{{{NS['r']}}}id")
                for node in sheet_root.findall(".//s:drawing", NS)
                if node.get(f"{{{NS['r']}}}id")
            ]

            for drawing_rel_id in drawing_rel_ids:
                drawing_path = sheet_relationships.get(drawing_rel_id)
                if drawing_path is None:
                    continue

                drawing_xml = archive.read(drawing_path)
                drawing_root = ET.fromstring(drawing_xml)
                drawing_relationships = _read_relationships(archive, drawing_path)

                chart_rel_ids = [
                    node.get(f"{{{NS['r']}}}id")
                    for node in drawing_root.findall(".//c:chart", NS)
                    if node.get(f"{{{NS['r']}}}id")
                ]

                for chart_rel_id in chart_rel_ids:
                    chart_path = drawing_relationships.get(chart_rel_id)
                    if chart_path is None:
                        continue

                    chart_xml = archive.read(chart_path)
                    chart_info = _extract_chart_info(chart_xml, chart_path)
                    chart_info["sheet"] = sheet_name
                    workbook_chart_info.append(chart_info)

    return workbook_chart_info


def _resolve_from_patterns(patterns: tuple[str, ...], label: str) -> str:
    """Resolve exactly one file from multiple candidate patterns."""

    if not patterns:
        raise ValueError(f"No {label} file pattern provided.")

    matches = []
    for pattern in patterns:
        matches.extend(glob_ci(pattern))

    matches = list(dict.fromkeys(matches))

    if len(matches) == 0:
        if label == "submission":
            fail_student(missing_file_message(patterns[0]))
        pattern_str = '", "'.join(patterns)
        raise FileNotFoundError(
            f'Could not find a {label} file matching any pattern in ("{pattern_str}").'
        )

    if len(matches) > 1:
        pattern_str = '", "'.join(patterns)
        raise ValueError(
            f'Found multiple {label} files matching patterns in ("{pattern_str}").'
        )

    return matches[0]


def resolve_submission_file(options: Options) -> str:
    """Resolve submission workbook from sub_module or required_files."""

    if options.sub_module:
        return resolve_module_workbook(options.sub_module, "submission")

    if options.required_files:
        return resolve_single_file(options.required_files, "submission")

    raise ValueError("No submission file pattern provided.")


def resolve_reference_file(options: Options) -> str:
    """Resolve reference workbook from ref_module or kwargs['reference_file']."""

    default_ref_module = Options().ref_module
    if options.ref_module and options.ref_module != default_ref_module:
        return resolve_module_workbook(options.ref_module, "reference")

    explicit_reference = options.kwargs.get("reference_file")
    if explicit_reference:
        return resolve_single_file((explicit_reference,), "reference")

    raise ValueError(
        "No reference file provided. Set `ref_module`"
        " or `kwargs['reference_file']`.")


def resolve_module_workbook(module: str, label: str) -> str:
    """Resolve an exact workbook path from module-like syntax."""

    if not module:
        raise ValueError(f"No {label} module provided.")

    if any(char in module for char in "*?[]"):
        return _resolve_from_patterns((module,), label)

    candidate_paths = [
        module,
        f"{module}.xlsx",
        f"{module.replace('.', '/')}.xlsx",
        f"{module.replace('.', str(Path('/')))}.xlsx",
    ]

    # Match candidates without regard to the case of letters, so a
    # workbook saved as Report.XLSX resolves the same as report.xlsx.
    existing_paths = {}
    for candidate in candidate_paths:
        for match in glob_ci(candidate):
            candidate_path = Path(match)
            if not candidate_path.is_file():
                continue
            normalized = str(candidate_path.resolve())
            existing_paths[normalized] = str(candidate_path)

    existing_paths = list(existing_paths.values())

    if len(existing_paths) == 0:
        if label == "submission":
            fail_student(missing_file_message(candidate_paths[1]))
        candidate_str = '", "'.join(candidate_paths)
        raise FileNotFoundError(
            f'Could not find a {label} file from module "{module}".'
            f' Tried ("{candidate_str}").'
        )

    if len(existing_paths) > 1:
        candidate_str = '", "'.join(existing_paths)
        raise ValueError(
            f'Found multiple {label} files for module "{module}"'
            f' in ("{candidate_str}").'
        )

    return existing_paths[0]


# ---------------------------------------------------------------------------
# Semantic header-matching helpers (used by data_table_match_reference)
# ---------------------------------------------------------------------------


def _normalize_header(value) -> str:
    """Normalize a cell value for fuzzy header comparison (lowercased)."""
    if value is None:
        return ""
    return " ".join(str(value).strip().lower().split())


def _normalize_header_strict(value) -> str:
    """Normalize a cell value for strict header comparison (case-preserved)."""
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def _match_header_mapping(
    ref_headers: list,
    sub_headers: list,
    header_ratio: float,
    strict_headers: bool,
    strict_column_order: bool,
) -> dict | None:
    """Try to match ref_headers to sub_headers using greedy similarity assignment.

    Returns a dict mapping ref_col_idx -> sub_col_idx, or None if any non-None
    reference header cannot be matched above *header_ratio*.  When
    *strict_column_order* is True the mapping must be monotonically increasing
    (sub indices must increase as ref indices increase).
    """
    available = list(range(len(sub_headers)))
    mapping: dict[int, int] = {}

    for ref_idx, ref_h in enumerate(ref_headers):
        ref_norm = _normalize_header(ref_h)
        if not ref_norm:
            # Skip None / empty reference headers — treat them as don't-care.
            continue

        best_sub_idx = None
        best_score = -1.0

        for sub_idx in available:
            if strict_headers:
                # Case-sensitive, whitespace-normalised exact match only.
                ref_s = _normalize_header_strict(ref_h)
                sub_s = _normalize_header_strict(sub_headers[sub_idx])
                score = 1.0 if ref_s == sub_s else 0.0
            else:
                sub_norm = _normalize_header(sub_headers[sub_idx])
                score = normalized_similarity(ref_norm, sub_norm) if sub_norm else 0.0
            if score > best_score:
                best_score = score
                best_sub_idx = sub_idx

        if best_sub_idx is None or best_score < header_ratio:
            return None

        mapping[ref_idx] = best_sub_idx
        available.remove(best_sub_idx)

    if not mapping:
        return None

    if strict_column_order:
        prev = -1
        for ref_idx in sorted(mapping):
            if mapping[ref_idx] <= prev:
                return None
            prev = mapping[ref_idx]

    return mapping


def find_table_by_headers(
    sheet,
    ref_headers: list,
    header_ratio: float,
    strict_headers: bool,
    strict_column_order: bool,
) -> tuple[int, int, dict] | None:
    """Scan *sheet* for a contiguous row of cells that fuzzy-matches *ref_headers*.

    Returns ``(header_row_1based, col_start_1based, col_mapping)`` where
    *col_mapping* is a dict ``{ref_col_idx: sub_col_idx}`` (both 0-based
    relative to the scanned block).  Returns ``None`` if no match is found.
    """
    n = len(ref_headers)
    if n == 0:
        return None

    max_row = sheet.max_row
    max_col = sheet.max_column
    if max_col < n:
        return None

    for row in range(1, max_row + 1):
        for col_start in range(1, max_col - n + 2):
            candidate = [sheet.cell(row, col_start + i).value for i in range(n)]
            mapping = _match_header_mapping(
                ref_headers, candidate, header_ratio, strict_headers, strict_column_order
            )
            if mapping is not None:
                return row, col_start, mapping

    return None
