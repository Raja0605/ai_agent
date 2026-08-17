"""
Salary parsing, with the Indian conventions that generic parsers miss.

Indian postings quote pay in ways no other market uses:

* **Lakh / crore** — 1 lakh = 100,000 and 1 crore = 10,000,000. "18 LPA" means
  ₹1,800,000 per annum, and "₹12,00,000" uses the Indian digit grouping
  (2-2-3) rather than thousands separators.
* **LPA / CTC** — pay is almost always stated as an annual cost-to-company
  figure, not a monthly or hourly rate.

Without this, an Indian posting either surfaced no salary at all or — worse —
reported "12" as the figure after a naive number grab.
"""

import re
from typing import NamedTuple, Optional

# Annual working assumptions, for converting non-annual quotes.
MONTHS_PER_YEAR = 12
# 40h/week × 52 weeks, the convention Adzuna and most boards use.
HOURS_PER_YEAR = 2080

LAKH = 100_000
CRORE = 10_000_000


class SalaryRange(NamedTuple):
    min_amount: Optional[int]
    max_amount: Optional[int]
    currency: Optional[str]
    period: str  # always "year" once parsed; kept explicit for clarity


# A number, tolerating Indian grouping (12,00,000) and decimals (12.5).
_NUMBER = r"(\d[\d,]*(?:\.\d+)?)"

# Lakh/crore suffixes, longest alternative first.
#
# Order is load-bearing: Python's alternation is first-match, not longest-
# match, so listing "cr" before "crore" made "33 Crore" match as "cr" and
# leave "ore" behind. That broke the guard that recognises "33 Crore
# transactions" as a business metric, and PhonePe's blurb was read as pay.
_UNITS = r"crores|crore|cr|lakhs|lakh|lacs|lac|lpa|l"
_CURRENCY = r"(?:₹|rs\.?|inr)"

# "12-18 LPA", "12 to 18 lakhs per annum", "₹12L - ₹18L",
# and "₹12,00,000 - ₹18,00,000" — the unit suffix is optional because portals
# quote the digits in full at least as often as they use lakh notation. A
# range with no unit is only accepted if the figures are already salary-sized,
# which is what keeps "3-5 years of experience" out.
_RANGE_UNIT = re.compile(
    rf"{_CURRENCY}?\s*{_NUMBER}\s*(?:{_UNITS})?\s*"
    rf"(?:-|–|to|and)\s*"
    rf"{_CURRENCY}?\s*{_NUMBER}\s*({_UNITS})?",
    re.IGNORECASE,
)

# A single "18 LPA" / "₹18 lakhs" / "1.2 crore"
_SINGLE_UNIT = re.compile(
    rf"{_CURRENCY}\s*{_NUMBER}\s*({_UNITS})?"
    rf"|{_NUMBER}\s*(crores|crore|cr|lakhs|lakh|lacs|lac|lpa)",
    re.IGNORECASE,
)

_PER_MONTH = re.compile(r"per\s*month|monthly|/\s*month|p\.?m\.?\b", re.IGNORECASE)
_PER_HOUR = re.compile(r"per\s*hour|hourly|/\s*hour|per\s*hr", re.IGNORECASE)


def _to_number(raw: str) -> Optional[float]:
    try:
        return float(raw.replace(",", ""))
    except (TypeError, ValueError):
        return None


def _apply_unit(value: float, unit: Optional[str]) -> int:
    """Scale a figure by its lakh/crore suffix."""
    if not unit:
        return int(round(value))

    unit = unit.lower()
    if unit.startswith("cr"):
        return int(round(value * CRORE))
    # l / lakh / lac / lpa
    return int(round(value * LAKH))


def _annualize(amount: Optional[int], text: str) -> Optional[int]:
    """Convert a monthly or hourly figure to annual."""
    if amount is None:
        return None
    if _PER_MONTH.search(text):
        return amount * MONTHS_PER_YEAR
    if _PER_HOUR.search(text):
        return amount * HOURS_PER_YEAR
    return amount


def parse_indian_salary(text: Optional[str]) -> Optional[SalaryRange]:
    """
    Extract an annual INR range from free text.

    Returns None when nothing salary-shaped is found, rather than guessing —
    a fabricated salary is worse than an honest "Not disclosed".
    """
    if not text:
        return None

    # Look only at the neighbourhood of salary words, so an unrelated "5-8
    # years of experience" is never read as "5-8 lakhs".
    window = _salary_window(text)
    if not window:
        return None

    # Every candidate is considered, not just the first. A window routinely
    # opens on "3-5 years of experience, CTC ₹12,00,000 - ₹18,00,000": the
    # leading range is implausible as pay and has to be stepped over rather
    # than treated as the answer.
    for match in _RANGE_UNIT.finditer(window):
        low = _to_number(match.group(1))
        high = _to_number(match.group(2))
        unit = match.group(3)
        if low is None or high is None:
            continue

        min_amount = _apply_unit(low, unit)
        max_amount = _apply_unit(high, unit)
        if min_amount > max_amount:
            min_amount, max_amount = max_amount, min_amount

        min_annual = _annualize(min_amount, window)
        max_annual = _annualize(max_amount, window)
        if _is_plausible(min_annual) and _is_plausible(max_annual):
            return SalaryRange(min_annual, max_annual, "INR", "year")

    for match in _SINGLE_UNIT.finditer(window):
        raw = match.group(1) or match.group(3)
        unit = match.group(2) or match.group(4)
        value = _to_number(raw)
        if value is None:
            continue

        amount = _annualize(_apply_unit(value, unit), window)
        # A bare rupee figure under a lakh is almost always a monthly
        # stipend or a typo rather than an annual salary; don't report it.
        if _is_plausible(amount) and amount >= LAKH:
            return SalaryRange(amount, None, "INR", "year")

    return None


# Words that mark a passage as being about pay.
#
# Word-bounded, and "pay" is deliberately absent as a bare stem: it matched
# inside "payments", which anchored the search window on PhonePe's company
# blurb and read "over 60 Crore registered users" as a ₹60 crore salary on
# every one of their postings.
# The rupee sign and an explicit currency code are cues in their own right:
# aggregators return a bare "₹12,00,000 - ₹18,00,000 per year" with none of
# the surrounding prose these words were written for, and without a cue the
# window never opens and the figure is dropped.
_SALARY_CUE = re.compile(
    r"₹|(?<![a-z])(salary|salaries|compensation|ctc|remuneration|stipend|lpa|"
    r"inr|rs\.?|pay\s+range|pay\s+scale|base\s+pay|take\s*home|in\s*hand|"
    r"per\s+annum|per\s+year|per\s+month|annually|monthly|p\.?a\.?)(?![a-z])",
    re.IGNORECASE,
)

# Nouns that turn a big number into a business metric rather than a wage.
# Indian company blurbs quote user and merchant counts in crore constantly.
_COUNT_NOUN = re.compile(
    r"^\W{0,4}(\(|registered|active|monthly|daily|\d)?\s*"
    r"(users?|customers?|merchants?|transactions?|downloads?|subscribers?|"
    r"members?|people|indians?|million|billion|mn\b|bn\b|tpv|gmv|valuation|"
    r"revenue|funding|raised|market|volume)",
    re.IGNORECASE,
)

# Plausibility bounds for an annual Indian salary. Anything outside is a
# business figure that happened to sit near a pay word.
MIN_PLAUSIBLE_ANNUAL = 50_000        # below this it is a monthly stipend
MAX_PLAUSIBLE_ANNUAL = 10 * CRORE    # ₹10 Cr/yr tops out real executive pay


def _is_plausible(amount: Optional[int]) -> bool:
    return amount is not None and MIN_PLAUSIBLE_ANNUAL <= amount <= MAX_PLAUSIBLE_ANNUAL


def _salary_window(text: str) -> Optional[str]:
    """
    The slice of text around a genuine pay reference.

    Scoping matters twice over: Indian job ads put "3-5 years of experience"
    and the pay range in the same document, and company boilerplate quotes
    user counts in crore. Each cue is checked in turn and one whose
    neighbourhood looks like a business metric is skipped.
    """
    for match in _SALARY_CUE.finditer(text):
        start = max(0, match.start() - 80)
        window = text[start : match.end() + 160]
        if not _looks_like_a_count(window):
            return window
    return None


def _looks_like_a_count(window: str) -> bool:
    """Whether the figures in this window are counts rather than money."""
    for number in re.finditer(
        rf"{_NUMBER}\s*(?:{_UNITS})?", window, re.IGNORECASE
    ):
        trailing = window[number.end() : number.end() + 30]
        if _COUNT_NOUN.match(trailing):
            return True
    return False


def format_salary(min_amount: Optional[int], max_amount: Optional[int], currency: Optional[str]) -> str:
    """Human-readable salary, using lakh notation for INR."""
    if min_amount is None and max_amount is None:
        return "Not disclosed"

    if currency == "INR":
        def lakhs(value: int) -> str:
            if value >= CRORE:
                return f"₹{value / CRORE:.2f}".rstrip("0").rstrip(".") + " Cr"
            return f"₹{value / LAKH:.1f}".rstrip("0").rstrip(".") + "L"

        if min_amount and max_amount:
            return f"{lakhs(min_amount)} – {lakhs(max_amount)} PA"
        return f"{lakhs(min_amount or max_amount or 0)} PA"

    unit = currency or ""
    if min_amount and max_amount:
        return f"{min_amount:,} – {max_amount:,} {unit}".strip()
    return f"{(min_amount or max_amount or 0):,} {unit}".strip()
