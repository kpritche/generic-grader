import pytest

from generic_grader.excel._units import canonicalize_label, label_unit

# Axis labels taken from the ENGR 131 reference workbooks, each paired with
# spellings a student is likely to write for the same axis.
EQUIVALENT_LABELS = [
    (
        "Applied Load (P) [Newtons]",
        ["Applied Load (P) [N]", "Applied Load (N)", "Applied Load [newton]", "applied load (P) (n)"],
    ),
    (
        "Deflection (δ) [mm]",
        ["Deflection (mm)", "Deflection (millimeters)", "Deflection [millimetres]"],
    ),
    (
        "Maximum Allowable Deflection [mm]",
        ["Maximum Allowable Deflection (millimeters)"],
    ),
    (
        "Launch Angle (θ) [°]",
        ["Launch Angle (degrees)", "Launch Angle (°)", "Launch Angle (deg)"],
    ),
    (
        "Distance (d) [ft]",
        ["Distance (feet)", "Distance (ft)", "Distance (foot)"],
    ),
    (
        "Adjusted Energy Usage (kWh)",
        ["Adjusted Energy Usage (kilowatt-hours)", "Adjusted Energy Usage [kilowatt hours]", "Adjusted Energy Usage (kW h)"],
    ),
    (
        "Total Power Demand [MW]",
        ["Total Power Demand (megawatts)", "Total Power Demand (mw)"],
    ),
    (
        "Water Consumed [m3/d]",
        ["Water Consumed (m³/d)", "Water Consumed (cubic meters per day)", "Water Consumed (m^3/day)"],
    ),
    (
        "Temperature (T) [°C]",
        ["Temperature (degrees Celsius)", "Temperature (C)", "Temperature (°C)", "Temperature (celsius)"],
    ),
    (
        "Velocity (v) [m/s]",
        ["Velocity (meters per second)", "Velocity (m/s)"],
    ),
    (
        "Moment of Inertia (I) [mm^4]",
        ["Moment of Inertia (mm⁴)", "Moment of Inertia (mm4)"],
    ),
    (
        "Area (m2)",
        ["Area (square meters)", "Area (m²)", "Area (sq m)"],
    ),
    (
        "Households (%)",
        [
            "Households (percent)",
            "Households (Percent)",
            "Households (percentage)",
            "Households (Percentages)",
            "Households (per cent)",
            "Households (PER CENT)",
            "Households (pct)",
        ],
    ),
    (
        "Adoption Rate (%/year)",
        [
            "Adoption Rate (percent per year)",
            "Adoption Rate (percentage/yr)",
            "Adoption Rate (per cent per year)",
        ],
    ),
    (
        "Coefficient of Determination (unitless)",
        [
            "Coefficient of Determination (Unitless)",
            "Coefficient of Determination (dimensionless)",
            "Coefficient of Determination (none)",
            "Coefficient of Determination (N/A)",
            "Coefficient of Determination (n/a)",
            "Coefficient of Determination (no units)",
            "Coefficient of Determination (no unit)",
        ],
    ),
]


@pytest.mark.parametrize(
    "reference, variant",
    [(ref, variant) for ref, variants in EQUIVALENT_LABELS for variant in variants],
)
def test_unit_spellings_compare_equal(reference, variant):
    assert canonicalize_label(variant) == canonicalize_label(reference)


@pytest.mark.parametrize(
    "label, expected",
    [
        ("Applied Load (P) [Newtons]", "applied load n"),
        ("Deflection (δ) [mm]", "deflection mm"),
        ("Launch Angle (θ) [°]", "launch angle deg"),
        ("Material Type", "material type"),
        ("Day", "d"),
        ("Water Consumed [m3/d]", "water consumed m3 per d"),
        ("Percentage", "percent"),
        ("Per Cent", "percent"),
        ("N/A", "unitless"),
        ("No Units", "unitless"),
    ],
)
def test_canonical_form(label, expected):
    assert canonicalize_label(label) == expected


@pytest.mark.parametrize(
    "left, right",
    [
        ("Deflection (mm)", "Deflection (cm)"),
        ("Applied Load (N)", "Applied Load (kN)"),
        ("Energy (kWh)", "Energy (MWh)"),
        ("Temperature (°C)", "Temperature (°F)"),
        ("Growth (%)", "Growth (%/yr)"),
        ("Ratio (unitless)", "Ratio (%)"),
        # "N/A" must not survive as newtons per ampere.
        ("Current (N/A)", "Current (A)"),
    ],
)
def test_different_units_stay_different(left, right):
    assert canonicalize_label(left) != canonicalize_label(right)


def test_symbol_only_group_keeps_its_letter_in_unit_position():
    # A lone bracket group cannot be told apart from a unit, so it is kept
    # and left to fail the similarity check rather than the presence check.
    assert canonicalize_label("(P)") == "p"


def test_unknown_unit_is_kept_as_written():
    assert canonicalize_label("Count (widgets)") == "count widgets"


@pytest.mark.parametrize("label", [None, "", "   ", "(δ)"])
def test_empty_labels(label):
    assert canonicalize_label(label) == ""


@pytest.mark.parametrize(
    "label, expected",
    [
        ("Applied Load (P) [Newtons]", "n"),
        ("Applied Load (N)", "n"),
        ("Deflection (δ) [mm]", "mm"),
        ("Launch Angle (θ) [°]", "deg"),
        ("Water Consumed [m3/d]", "m3 per d"),
        ("Water Consumed (cubic meters per day)", "m3 per d"),
        ("Temperature (°C)", "degc"),
        ("Moment of Inertia (I) [mm^4]", "mm4"),
        ("Material Type", None),
        ("Applied Load (P)", None),
        ("Count (widgets)", None),
        ("Applied Load", None),
    ],
)
def test_label_unit(label, expected):
    assert label_unit(label) == expected
