"""
The adapters that reach Naukri, LinkedIn and Indeed inventory.

None of those three can be queried directly — no public API, and scraping is
prohibited — so the postings arrive through aggregators that license the
Google for Jobs index. The behaviour worth pinning down is that a posting
keeps the identity of the portal it was published on, that Indian salary
conventions survive the trip, and that non-Indian results are dropped.

These test the parsing only: no network, payloads shaped like the real ones.
"""

import pytest

from app.services.sources.careerjet import CareerjetAdapter
from app.services.sources.jooble import JoobleAdapter
from app.services.sources.jsearch import JSearchAdapter
from app.services.sources.publishers import publisher_slug


# ───────────────────────── publisher attribution ─────────────────────────

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("LinkedIn", "linkedin"),
        ("linkedin.com", "linkedin"),
        ("Jobs via LinkedIn", "linkedin"),
        ("Naukri", "naukri"),
        ("www.naukri.com", "naukri"),
        ("Indeed", "indeed"),
        ("in.indeed.com", "indeed"),
        # Monster India rebranded; both names appear in live data.
        ("Monster India", "foundit"),
        ("foundit.in", "foundit"),
        ("Internshala", "internshala"),
        (None, "jsearch"),
        ("", "jsearch"),
    ],
)
def test_publisher_slugs(raw, expected):
    assert publisher_slug(raw, "jsearch") == expected


# ──────────────────────────────── JSearch ────────────────────────────────

def _jsearch_job(**overrides):
    """One job, shaped like a real /search-v2 item."""
    job = {
        "job_id": "abc123",
        "job_title": "Senior Backend Engineer",
        "employer_name": "PhonePe",
        "job_publisher": "Naukri",
        "job_apply_link": "https://www.naukri.com/job-listings-abc123",
        "job_city": "Bengaluru",
        "job_state": "Karnataka",
        "job_country": "IN",
        "job_location": "Bengaluru, Karnataka",
        "job_is_remote": False,
        "job_posted_at_datetime_utc": "2026-08-10T09:30:00.000Z",
        "job_description": "<p>Build payment systems in Java and Kotlin.</p>",
        # Display text arrives with an en-dash; the list is the usable form.
        "job_employment_type": "Full–time",
        "job_employment_types": ["FULLTIME"],
        "job_min_salary": 2500000,
        "job_max_salary": 4000000,
        "job_salary_period": "YEAR",
        "job_salary_string": None,
    }
    job.update(overrides)
    return job


def _jsearch_payload(**overrides):
    """The /search-v2 envelope: data is an object holding `jobs`."""
    return {"data": {"jobs": [_jsearch_job(**overrides)], "cursor": None}}


def test_a_naukri_posting_keeps_its_portal_identity():
    """
    The point of the adapter: the user asked for Naukri, LinkedIn and Indeed,
    and the result has to say which one it came from — not "jsearch".
    """
    jobs = JSearchAdapter()._parse(_jsearch_payload())
    assert len(jobs) == 1
    assert jobs[0].source == "naukri"
    assert jobs[0].title == "Senior Backend Engineer"
    assert jobs[0].company == "PhonePe"
    assert jobs[0].location == "Bengaluru, Karnataka"


def test_linkedin_and_indeed_are_distinguished():
    payload = {"data": {"jobs": [
        _jsearch_job(job_id="1", job_publisher="LinkedIn"),
        _jsearch_job(job_id="2", job_publisher="Indeed"),
    ]}}
    assert {job.source for job in JSearchAdapter()._parse(payload)} == {"linkedin", "indeed"}


def test_the_legacy_flat_envelope_still_parses():
    """
    `/search` returned a flat list under `data`; `/search-v2` nests it under
    `data.jobs`. Accepting both is why an endpoint move degrades to a visible
    error rather than a silent zero-result search — which is how the wrong
    path survived until a real key was tried.
    """
    legacy = {"data": [_jsearch_job()]}
    assert [job.source for job in JSearchAdapter()._parse(legacy)] == ["naukri"]


def test_html_is_stripped_from_the_description():
    jobs = JSearchAdapter()._parse(_jsearch_payload())
    assert "<p>" not in jobs[0].description
    assert "Java" in jobs[0].description


def test_monthly_pay_is_annualized():
    """
    Indian postings quote monthly pay far more often than Western ones.
    Storing ₹80,000/month as ₹80,000/year understates the role by 12x.
    """
    jobs = JSearchAdapter()._parse(
        _jsearch_payload(job_min_salary=80000, job_max_salary=100000,
                         job_salary_period="MONTH")
    )
    assert jobs[0].salary_min == 960_000
    assert jobs[0].salary_max == 1_200_000


def test_non_indian_results_are_dropped():
    """The aggregator's country filter is a hint, not a guarantee."""
    jobs = JSearchAdapter()._parse(
        _jsearch_payload(job_city="Austin", job_state="TX", job_country="US")
    )
    assert jobs == []


def test_a_worldwide_remote_role_is_kept():
    jobs = JSearchAdapter()._parse(
        _jsearch_payload(job_city=None, job_state=None,
                         job_location="Anywhere", job_is_remote=True)
    )
    assert len(jobs) == 1 and jobs[0].remote is True


def test_a_posting_with_no_id_is_skipped():
    jobs = JSearchAdapter()._parse(_jsearch_payload(job_id=None))
    assert jobs == []


def test_publisher_allowlist_is_applied(monkeypatch):
    from app.core import config
    monkeypatch.setattr(config.settings, "JSEARCH_PUBLISHERS", "naukri,linkedin")

    payload = {"data": {"jobs": [
        _jsearch_job(job_id="1", job_publisher="Naukri"),
        _jsearch_job(job_id="2", job_publisher="Glassdoor"),
    ]}}
    assert [job.source for job in JSearchAdapter()._parse(payload)] == ["naukri"]


def test_salary_currency_is_read_from_the_text_when_given():
    """The endpoint carries no currency field; the string is the only source."""
    jobs = JSearchAdapter()._parse(
        _jsearch_payload(job_salary_string="₹18,00,000 - ₹24,00,000 a year",
                         job_min_salary=None, job_max_salary=None)
    )
    assert (jobs[0].salary_min, jobs[0].salary_max) == (1_800_000, 2_400_000)
    assert jobs[0].currency == "INR"


def test_bare_figures_on_an_indian_posting_are_rupees():
    """Numeric fields arrive with no currency at all. USD would be a worse guess."""
    jobs = JSearchAdapter()._parse(_jsearch_payload())
    assert jobs[0].currency == "INR"
    assert jobs[0].salary_min == 2_500_000


def test_a_posting_with_no_salary_reports_none():
    jobs = JSearchAdapter()._parse(
        _jsearch_payload(job_min_salary=None, job_max_salary=None, job_salary_string=None)
    )
    assert jobs[0].salary_min is None and jobs[0].currency is None


def test_employment_type_prefers_the_machine_readable_list():
    jobs = JSearchAdapter()._parse(_jsearch_payload())
    assert jobs[0].employment_type == "fulltime"


def test_an_empty_payload_is_not_an_error():
    assert JSearchAdapter()._parse({}) == []
    assert JSearchAdapter()._parse({"data": None}) == []
    assert JSearchAdapter()._parse({"data": {"jobs": None}}) == []
    assert JSearchAdapter()._parse(None) == []


# ─────────────────────────────── Careerjet ───────────────────────────────

def _careerjet_payload(**overrides):
    job = {
        "title": "Data Engineer",
        "company": "Swiggy",
        "date": "2026-08-11",
        "description": "Own the data platform. Spark, Airflow, Python.",
        "locations": "Bangalore, Karnataka",
        "salary_currency_code": "INR",
        "salary_min": 1800000,
        "salary_max": 2600000,
        "salary_type": "Y",
        "url": "https://www.careerjet.co.in/jobad/in-xyz",
    }
    job.update(overrides)
    return {"jobs": [job]}


def test_careerjet_parses_an_indian_posting():
    jobs = CareerjetAdapter()._parse(_careerjet_payload())
    assert len(jobs) == 1
    job = jobs[0]
    assert job.source == "careerjet"
    assert job.title == "Data Engineer"
    assert job.location == "Bangalore, Karnataka"
    assert job.posted_at.date().isoformat() == "2026-08-11"


def test_careerjet_derives_a_stable_id_from_the_url():
    """The API returns no id, so the URL has to serve as one."""
    first = CareerjetAdapter()._parse(_careerjet_payload())[0]
    second = CareerjetAdapter()._parse(_careerjet_payload())[0]
    other = CareerjetAdapter()._parse(_careerjet_payload(url="https://x.test/2"))[0]

    assert first.source_job_id == second.source_job_id
    assert first.source_job_id != other.source_job_id


def test_careerjet_annualizes_a_monthly_figure():
    jobs = CareerjetAdapter()._parse(
        _careerjet_payload(salary_min=90000, salary_max=None, salary_type="M")
    )
    assert jobs[0].salary_min == 1_080_000


def test_careerjet_drops_non_indian_postings():
    assert CareerjetAdapter()._parse(_careerjet_payload(locations="Berlin, Germany")) == []


# ───────────────────────────────── Jooble ────────────────────────────────

def _jooble_payload(**overrides):
    job = {
        "id": "998877",
        "title": "DevOps Engineer",
        "location": "Pune, Maharashtra",
        "snippet": "Kubernetes and <b>AWS</b> experience required.",
        "salary": "₹12,00,000 - ₹18,00,000 per year",
        "source": "naukri.com",
        "type": "Full-time",
        "link": "https://in.jooble.org/jdp/998877",
        "updated": "2026-08-12T06:00:00",
    }
    job.update(overrides)
    return {"jobs": [job]}


def test_jooble_keeps_the_originating_portal():
    jobs = JoobleAdapter()._parse(_jooble_payload())
    assert len(jobs) == 1
    assert jobs[0].source == "naukri"
    assert jobs[0].title == "DevOps Engineer"


def test_jooble_falls_back_to_its_own_name_when_no_portal_is_given():
    jobs = JoobleAdapter()._parse(_jooble_payload(source=None))
    assert jobs[0].source == "jooble"


def test_jooble_reads_lakh_notation_in_the_salary_string():
    """Salary arrives as free text; the Indian parser already handles it."""
    jobs = JoobleAdapter()._parse(_jooble_payload())
    assert jobs[0].salary_min == 1_200_000
    assert jobs[0].salary_max == 1_800_000
    assert jobs[0].currency == "INR"


def test_jooble_strips_the_highlight_markup():
    jobs = JoobleAdapter()._parse(_jooble_payload())
    assert "<b>" not in jobs[0].description
    assert "AWS" in jobs[0].description


def test_jooble_drops_non_indian_postings():
    assert JoobleAdapter()._parse(_jooble_payload(location="Warsaw, Poland")) == []
