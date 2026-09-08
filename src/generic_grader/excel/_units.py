"""Canonicalize the units and symbols in chart axis labels.

Students write the same unit many ways: ``Newtons``, ``newton``, or ``N``;
``millimeters`` or ``mm``; ``degrees`` or ``°``.  A reference workbook fixes
one spelling, so a character-level comparison fails a correct label over the
spelling of its unit.  ``canonicalize_label`` rewrites a label so every
spelling of a unit compares equal, and drops the single-letter variable
symbols (``(P)``, ``(δ)``) that a student may reasonably omit.

The rewrite is applied to both the reference and the submission, so it never
needs to be complete: an unknown unit is left as written and still compares
equal to itself.
"""

import re
import unicodedata

# Characters that carry unit meaning but are not alphanumeric.  Applied
# before the alphanumeric filter, which would otherwise erase them.
_PRE_SUBSTITUTIONS = (
    ("°", " deg "),  # degree sign
    ("º", " deg "),  # masculine ordinal, often typed for a degree sign
    ("%", " percent "),
    ("Ω", " ohm "),  # Greek capital omega
    ("Ω", " ohm "),  # ohm sign
    ("µ", "u"),  # micro sign
    ("μ", "u"),  # Greek small mu
    ("²", "2"),
    ("³", "3"),
    ("⁴", "4"),
    ("^", ""),
    ("/", " per "),
    ("·", " "),  # middle dot
    ("⋅", " "),  # dot operator
    ("*", " "),
)

# canonical abbreviation -> alternative spellings (singular).  Plurals with a
# trailing ``s`` are derived.  The canonical form itself is always accepted.
_UNIT_ALIASES = {
    "n": ("newton",),
    "kn": ("kilonewton",),
    "mm": ("millimeter", "millimetre"),
    "cm": ("centimeter", "centimetre"),
    "m": ("meter", "metre"),
    "km": ("kilometer", "kilometre"),
    "in": ("inch", "inches"),
    "ft": ("foot", "feet"),
    "mi": ("mile",),
    "kg": ("kilogram",),
    "g": ("gram",),
    "lb": ("lbs", "pound"),
    "s": ("sec", "secs", "second"),
    "min": ("mins", "minute"),
    "h": ("hr", "hrs", "hour"),
    "d": ("day",),
    "yr": ("yrs", "year"),
    "deg": ("degree",),
    "degc": ("celsius", "centigrade"),
    "degf": ("fahrenheit",),
    "k": ("kelvin",),
    "pa": ("pascal",),
    "kpa": ("kilopascal",),
    "mpa": ("megapascal",),
    "gpa": ("gigapascal",),
    "psi": (),
    "w": ("watt",),
    "kw": ("kilowatt",),
    "mw": ("megawatt",),
    "gw": ("gigawatt",),
    "wh": ("watthour",),
    "kwh": ("kilowatthour",),
    "mwh": ("megawatthour",),
    "j": ("joule",),
    "kj": ("kilojoule",),
    "mj": ("megajoule",),
    "v": ("volt",),
    "a": ("amp", "ampere"),
    "ohm": (),
    "hz": ("hertz",),
    "khz": ("kilohertz",),
    "l": ("liter", "litre"),
    "ml": ("milliliter", "millilitre"),
    "gal": ("gallon",),
    "percent": ("pct", "percentage"),
    "rpm": (),
    "rad": ("radian",),
    # A dimensionless quantity has no unit, and a reference workbook still
    # has to write something in the units cell.  Treat the usual ways of
    # saying "there is no unit here" as one canonical answer.
    "unitless": ("dimensionless", "none", "na"),
}

# Pairs of canonical tokens that merge into one unit.
_PAIR_MERGES = {
    ("deg", "c"): "degc",
    ("deg", "degc"): "degc",
    ("deg", "f"): "degf",
    ("deg", "degf"): "degf",
    ("w", "h"): "wh",
    ("kw", "h"): "kwh",
    ("mw", "h"): "mwh",
    # "per cent" survives the alphanumeric filter as two tokens, and the
    # leading token is the same "per" that a solidus becomes, so it can
    # only be recognized as a pair.
    ("per", "cent"): "percent",
    ("no", "unit"): "unitless",
    ("no", "units"): "unitless",
}

# Words that raise a unit to a power when they precede it.
_POWER_WORDS = {"square": "2", "sq": "2", "cubic": "3", "cu": "3"}

# A lone letter in the unit position that names a temperature scale.
_UNIT_POSITION_ALIASES = {"c": "degc", "f": "degf"}


def _build_token_map() -> dict[str, str]:
    token_map = {}
    for canonical, aliases in _UNIT_ALIASES.items():
        token_map[canonical] = canonical
        for alias in aliases:
            token_map[alias] = canonical
            if not alias.endswith("s"):
                token_map[alias + "s"] = canonical
    return token_map


_TOKEN_MAP = _build_token_map()

_BRACKET_GROUP = re.compile(r"\(([^()]*)\)|\[([^\[\]]*)\]|\{([^{}]*)\}")

# "N/A" has to be read before the solidus below turns it into "n per a",
# which the token map would then read as newtons per ampere.
_NOT_APPLICABLE = re.compile(r"\bn\s*/\s*a\b", re.IGNORECASE)


def _tokens(text: str) -> list[str]:
    text = _NOT_APPLICABLE.sub(" unitless ", text)
    for old, new in _PRE_SUBSTITUTIONS:
        text = text.replace(old, new)
    lowered = text.lower()
    filtered = "".join(ch if ch.isalnum() else " " for ch in lowered)
    return filtered.split()


def _is_greek(token: str) -> bool:
    return len(token) == 1 and "GREEK" in unicodedata.name(token, "")


def _canonicalize_tokens(tokens: list[str]) -> list[str]:
    mapped = [_TOKEN_MAP.get(token, token) for token in tokens if not _is_greek(token)]

    merged = []
    i = 0
    while i < len(mapped):
        pair = tuple(mapped[i : i + 2])
        if len(pair) == 2 and pair in _PAIR_MERGES:
            merged.append(_PAIR_MERGES[pair])
            i += 2
        elif len(pair) == 2 and pair[0] in _POWER_WORDS and pair[1] in _UNIT_ALIASES:
            merged.append(pair[1] + _POWER_WORDS[pair[0]])
            i += 2
        else:
            merged.append(mapped[i])
            i += 1
    return merged


def _is_symbol_like(tokens: list[str]) -> bool:
    """A bracket group holding one short token reads as a variable symbol."""

    return len(tokens) <= 1 and all(len(token) <= 2 for token in tokens)


_POWERED_UNIT = re.compile(r"([a-z]+)\d")


def _is_unit_token(token: str) -> bool:
    if token in _UNIT_ALIASES or token == "per":
        return True
    match = _POWERED_UNIT.fullmatch(token)
    return bool(match and match.group(1) in _UNIT_ALIASES)


def _parse_label(text: str | None) -> tuple[list[str], list[str] | None]:
    """Split a label into canonical quantity tokens and canonical unit tokens.

    Bracketed groups are read by position: the last group is taken as the
    unit and kept whatever it holds, while an earlier group holding a single
    short token is taken as a variable symbol and dropped.  The unit tokens
    are returned separately only when every token in that last group is a
    recognized unit; otherwise the group is part of the quantity text and
    the unit is None.
    """

    if text is None:
        return [], None

    groups = list(_BRACKET_GROUP.finditer(text))
    quantity = []
    unit = None
    cursor = 0
    for index, match in enumerate(groups):
        quantity.extend(_canonicalize_tokens(_tokens(text[cursor : match.start()])))
        group_tokens = _canonicalize_tokens(_tokens(next(g for g in match.groups() if g is not None)))
        is_last = index == len(groups) - 1
        if is_last and len(group_tokens) == 1:
            group_tokens = [_UNIT_POSITION_ALIASES.get(group_tokens[0], group_tokens[0])]
        if is_last and group_tokens and all(_is_unit_token(token) for token in group_tokens):
            unit = group_tokens
        elif is_last or not _is_symbol_like(group_tokens):
            quantity.extend(group_tokens)
        cursor = match.end()
    quantity.extend(_canonicalize_tokens(_tokens(text[cursor:])))

    return quantity, unit


def canonicalize_label(text: str | None) -> str:
    """Return a label rewritten for comparison.

    The text is lowercased, punctuation is dropped, unit spellings are
    replaced by one canonical abbreviation, Greek letters are removed, and
    a variable symbol in an earlier bracket group is dropped (see
    ``_parse_label``).  So ``Applied Load (P) [Newtons]``,
    ``Applied Load (P) [N]``, and ``Applied Load (N)`` all become
    ``applied load n``.
    """

    quantity, unit = _parse_label(text)
    return " ".join(quantity + (unit or []))


def label_unit(text: str | None) -> str | None:
    """Return the canonical unit a label carries, or None if it has none.

    A label has a unit when its last bracket group holds only recognized
    units: ``Deflection (δ) [mm]`` -> ``mm``; ``Water Consumed [m3/d]`` ->
    ``m3 per d``; ``Material Type`` -> None; ``Applied Load (P)`` -> None.
    """

    _, unit = _parse_label(text)
    return " ".join(unit) if unit else None
