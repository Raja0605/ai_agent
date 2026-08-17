"""
Indian-market handling: location aliases and salary notation.

The salary cases marked "live data" are lifted from real postings fetched
during development, because that is where these bugs came from — not from
imagined input.
"""

import pytest

from app.services.job_identity import job_fingerprint
from app.services.locations import (
    canonical_city,
    is_indian_location,
    matches_location_query,
    normalize_location,
)
from app.services.salary_parser import format_salary, parse_indian_salary


# ─────────────────────────────── locations ───────────────────────────────

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Bangalore", "bengaluru"),
        ("Bengaluru", "bengaluru"),
        ("Bengaluru-VTP, India", "bengaluru"),      # live data: Groww
        ("Bangalore, Karnataka", "bengaluru"),      # live data: Meesho
        ("BLR", "bengaluru"),
        ("Gurgaon", "gurugram"),
        ("Gurugram, Haryana", "gurugram"),
        ("Bombay", "mumbai"),
        ("New Delhi", "delhi"),
        ("Trivandrum", "thiruvananthapuram"),
        ("Vizag", "visakhapatnam"),
        ("London, UK", None),
    ],
)
def test_canonical_city(raw, expected):
    assert canonical_city(raw) == expected


def test_alias_spellings_share_a_fingerprint():
    """
    The point of the alias table: the same role posted to two boards with
    different spellings of one city must merge into a single entry.
    """
    a = job_fingerprint("Meesho", "Backend Engineer", "Bangalore, Karnataka", False)
    b = job_fingerprint("Meesho", "Backend Engineer", "Bengaluru-VTP, India", False)
    assert a == b


def test_different_indian_cities_still_separate():
    a = job_fingerprint("Acme", "Backend Engineer", "Bengaluru, India", False)
    b = job_fingerprint("Acme", "Backend Engineer", "Pune, India", False)
    assert a != b


@pytest.mark.parametrize(
    "location,remote,expected",
    [
        ("Bengaluru, India", False, True),
        ("Gurgaon", False, True),
        ("Karnataka", False, True),
        ("India", False, True),
        ("Remote - India", True, True),
        ("Worldwide", True, True),      # a worldwide remote role is open to India
        ("Anywhere", True, True),
        ("London, UK", False, False),
        ("San Francisco, CA", False, False),
    ],
)
def test_is_indian_location(location, remote, expected):
    assert is_indian_location(location, remote) is expected


def test_searching_bangalore_finds_bengaluru_postings():
    """Without this, a Bangalore search hides most of the local market."""
    assert matches_location_query("Bengaluru-VTP, India", "Bangalore") is True
    assert matches_location_query("Bangalore, Karnataka", "Bengaluru") is True


def test_searching_a_city_excludes_other_cities():
    assert matches_location_query("Pune, Maharashtra", "Bangalore") is False


def test_country_query_matches_any_indian_city():
    assert matches_location_query("Hyderabad, Telangana", "India") is True
    assert matches_location_query("Berlin, Germany", "India") is False


def test_empty_query_matches_everything():
    assert matches_location_query("Anywhere", None) is True
    assert matches_location_query("Anywhere", "") is True


def test_normalize_location_passes_through_unknown_places():
    assert normalize_location("Berlin, Germany") == "berlin"


# ──────────────────────────────── salary ─────────────────────────────────

def test_lpa_range():
    result = parse_indian_salary("Salary: 12-18 LPA")
    assert (result.min_amount, result.max_amount, result.currency) == (1_200_000, 1_800_000, "INR")


def test_lakhs_written_out():
    result = parse_indian_salary("Compensation: 15 to 25 lakhs per annum")
    assert (result.min_amount, result.max_amount) == (1_500_000, 2_500_000)


def test_indian_digit_grouping():
    """₹12,00,000 is 12 lakh, not 12 thousand — 2-2-3 grouping, not 3-3-3."""
    result = parse_indian_salary("CTC: ₹12,00,000 per annum")
    assert result.min_amount == 1_200_000


def test_crore_salary():
    result = parse_indian_salary("Remuneration: ₹1.5 crore")
    assert result.min_amount == 15_000_000


def test_monthly_figure_is_annualized():
    result = parse_indian_salary("Stipend: ₹80,000 per month")
    assert result.min_amount == 960_000


def test_experience_range_is_not_read_as_salary():
    """'5-8 years' sits near pay wording in most Indian ads."""
    assert parse_indian_salary("Looking for 5-8 years of experience. Salary as per market.") is None


def test_company_user_counts_are_not_read_as_salary():
    """
    Live data, PhonePe: every posting reported ₹60 Cr because the cue "pay"
    matched inside "payments app", anchoring the window on the company blurb.
    """
    blurb = (
        "About PhonePe Limited: Headquartered in India, its flagship product, the "
        "PhonePe digital payments app, was launched in Aug 2016. As of April 2025, "
        "PhonePe has over 60 Crore (600 Million) registered users and a digital "
        "payments acceptance network spread across over 4 Crore (40+ million) merchants."
    )
    assert parse_indian_salary(blurb) is None


def test_transaction_volumes_are_not_read_as_salary():
    text = "PhonePe processes over 33 Crore transactions daily with a TPV of over INR 150 lakh crore."
    assert parse_indian_salary(text) is None


@pytest.mark.parametrize(
    "text,expected_min,expected_max",
    [
        # Digits written out in full, which the aggregators return far more
        # often than lakh notation. None of these parsed before: the rupee
        # sign was not treated as a cue, so the window never opened.
        ("₹12,00,000 - ₹18,00,000 per year", 1_200_000, 1_800_000),
        ("INR 12,00,000 - 18,00,000", 1_200_000, 1_800_000),
        ("Rs. 12,00,000 to Rs. 18,00,000 per annum", 1_200_000, 1_800_000),
        ("₹12L - ₹18L", 1_200_000, 1_800_000),
        ("₹80,000 per month", 960_000, None),
    ],
)
def test_rupee_ranges_without_lakh_notation(text, expected_min, expected_max):
    parsed = parse_indian_salary(text)
    assert parsed is not None, f"failed to parse {text!r}"
    assert parsed.min_amount == expected_min
    assert parsed.max_amount == expected_max
    assert parsed.currency == "INR"


def test_the_experience_range_is_stepped_over_to_reach_the_pay_range():
    """
    Indian ads put both in the same sentence, and the experience range comes
    first. Taking the first number pair found reports "3-5" as the salary.
    """
    parsed = parse_indian_salary(
        "CTC: 3-5 years experience, salary 12,00,000 to 18,00,000 per annum"
    )
    assert parsed is not None
    assert (parsed.min_amount, parsed.max_amount) == (1_200_000, 1_800_000)


def test_an_experience_range_alone_is_not_a_salary():
    assert parse_indian_salary("Salary: 5-8 years of experience required") is None


def test_implausibly_large_figures_are_rejected():
    assert parse_indian_salary("Salary: 500 crore per annum") is None


def test_no_salary_information_returns_none():
    assert parse_indian_salary("We are hiring a backend engineer in Bengaluru.") is None
    assert parse_indian_salary("") is None
    assert parse_indian_salary(None) is None


def test_format_uses_lakh_notation_for_inr():
    assert format_salary(1_200_000, 1_800_000, "INR") == "₹12L – ₹18L PA"
    assert format_salary(15_000_000, None, "INR") == "₹1.5 Cr PA"


def test_format_leaves_other_currencies_alone():
    assert format_salary(100_000, 150_000, "USD") == "100,000 – 150,000 USD"


def test_format_reports_missing_salary_honestly():
    assert format_salary(None, None, "INR") == "Not disclosed"
