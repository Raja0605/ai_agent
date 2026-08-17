"""
That a search returns what was searched for.

The bug these cover: the role filter asked whether every query word appeared
anywhere in the title, company, skills or description, which almost every
posting satisfies — so "data engineer" returned frontend roles whose
description happened to contain both words. Location filtering had the
opposite problem, being a raw substring test that missed every Indian city
alias. And `/jobs/search` returned whatever got saved, filtered by nothing at
all.
"""

import pytest

from app.schemas.job import NormalizedJob
from app.services import job_filter
from app.services.job_filter import SearchCriteria
from app.services.locations import location_aliases
from app.services.role_matcher import matches_role, role_relevance


def _job(title, *, skills=(), location="Bengaluru, India", company="Acme",
         remote=False, description="", source="greenhouse", posted_at=None):
    return NormalizedJob(
        source=source,
        source_job_id=f"{title}-{location}",
        title=title,
        company=company,
        location=location,
        remote=remote,
        description=description,
        skills=list(skills),
        posted_at=posted_at,
    )


# ─────────────────────────────── role matching ───────────────────────────────

def test_description_mentions_are_not_evidence_of_the_role():
    """
    The original false positive, verbatim: a frontend role whose description
    happens to use both query words used to pass the filter.
    """
    description = (
        "Join our engineering team to build data-rich dashboards. "
        "You will work with our data platform engineers on the UI."
    )
    assert matches_role("data engineer", "Senior Frontend Engineer",
                        ["React", "TypeScript"]) is False
    # ...and that stays false however many times the description says it.
    assert job_filter.relevance(
        _job("Senior Frontend Engineer", skills=["React"], description=description),
        SearchCriteria.build(keywords=["data engineer"]),
    ) is None


@pytest.mark.parametrize(
    "query,title,skills,expected",
    [
        ("data engineer", "Data Engineer", ["Spark"], True),
        # Different role noun class: an analyst job is not an engineer job.
        ("data engineer", "Data Analyst", ["SQL"], False),
        # Domain word satisfied by the skill list rather than the title.
        ("react developer", "Frontend Engineer", ["React", "CSS"], True),
        ("kubernetes", "Platform Engineer", ["Kubernetes"], True),
        ("kubernetes", "Platform Engineer", ["Terraform"], False),
        # Developer and Engineer are the same job in this market.
        ("java developer", "Java Software Engineer", [], True),
        ("java developer", "Python Developer", ["Django"], False),
    ],
)
def test_role_matching(query, title, skills, expected):
    assert matches_role(query, title, skills) is expected


@pytest.mark.parametrize(
    "query,title,expected",
    [
        # The SDE ladder is the default title at Indian product companies.
        ("software engineer", "SDE II", True),
        ("software developer", "SDE-1", True),
        ("java developer", "SDE-2 (Java Backend)", True),
        # "Fresher" is the standard local term and has no US equivalent.
        ("fresher java developer", "Java Developer - Fresher", True),
        ("full stack developer", "MERN Stack Developer", True),
        (".net developer", "Dot Net Developer", True),
    ],
)
def test_indian_title_conventions(query, title, expected):
    assert matches_role(query, title, []) is expected


@pytest.mark.parametrize(
    "query,title",
    [
        ("senior backend engineer", "Backend Engineering Intern"),
        ("fresher software engineer", "Principal Staff Engineer"),
        ("intern data analyst", "Senior Data Analyst"),
    ],
)
def test_seniority_conflicts_are_rejected(query, title):
    assert matches_role(query, title, []) is False


def test_seniority_gap_is_tolerated_when_close():
    """Senior vs mid is the same shortlist; senior vs intern is not."""
    assert matches_role("senior backend engineer", "Backend Engineer", ["Go"]) is True
    assert matches_role("lead devops engineer", "Senior DevOps Engineer", []) is True


@pytest.mark.parametrize(
    "query,title",
    [
        # Plural role nouns. Without these the title registers as naming no
        # role at all, which switches off the class check entirely — a live
        # search for "data engineer" returned "Data Labeling Specialists".
        ("data engineer", "Data Labeling Specialists"),
        ("software engineer", "Technical Writers"),
        ("data analyst", "Data Scientists"),
    ],
)
def test_plural_role_nouns_are_still_role_nouns(query, title):
    assert matches_role(query, title, []) is False


def test_a_skill_tag_alone_cannot_carry_an_unrelated_title():
    """
    "Assistant Account Payable" surfaced in a live "data analyst" search: the
    title names no role to agree on, so a single skill tag was the only
    evidence. That is too thin to call it a match.
    """
    assert matches_role("data analyst", "Assistant Account Payable",
                        ["Data Entry", "Excel"]) is False


def test_a_title_with_no_role_noun_still_matches_on_its_own_words():
    """The case the rule above must not break: plenty of real titles name no
    role noun, and the domain word in the title is enough."""
    assert matches_role("backend engineer", "Backend - Payments Platform", []) is True


def test_a_title_hit_outranks_a_skill_hit():
    """Ranking signal: the title is much stronger evidence than a skill tag."""
    in_title = role_relevance("react developer", "React Developer", [])
    in_skills = role_relevance("react developer", "Frontend Engineer", ["React"])
    assert in_title > in_skills


def test_company_name_is_searchable():
    """The search box is labelled "Role, skill or company"."""
    assert matches_role("phonepe", "Backend Engineer", [], company="PhonePe") is True
    assert matches_role("phonepe", "Backend Engineer", [], company="Razorpay") is False


def test_an_empty_query_excludes_nothing():
    assert matches_role("", "Anything At All", []) is True
    assert matches_role(None, "Anything At All", []) is True


# ────────────────────────────── the search gate ──────────────────────────────

def test_city_aliases_are_honoured_across_the_gate():
    """A Bangalore search must find the postings written "Bengaluru"."""
    criteria = SearchCriteria.build(keywords=["backend engineer"], locations=["Bangalore"])
    jobs = [
        _job("Backend Engineer", location="Bengaluru-VTP, India"),
        _job("Backend Engineer", location="Bangalore, Karnataka"),
        _job("Backend Engineer", location="Gurgaon, Haryana"),
        _job("Backend Engineer", location="London, UK"),
    ]
    kept = {job.location for job in job_filter.apply(jobs, criteria)}
    assert kept == {"Bengaluru-VTP, India", "Bangalore, Karnataka"}


def test_several_cities_are_a_union_not_an_intersection():
    criteria = SearchCriteria.build(
        keywords=["backend engineer"], locations=["Pune", "Hyderabad"]
    )
    jobs = [
        _job("Backend Engineer", location="Pune, Maharashtra"),
        _job("Backend Engineer", location="Hyderabad, Telangana"),
        _job("Backend Engineer", location="Chennai, Tamil Nadu"),
    ]
    kept = {job.location for job in job_filter.apply(jobs, criteria)}
    assert kept == {"Pune, Maharashtra", "Hyderabad, Telangana"}


def test_several_roles_are_a_union_too():
    criteria = SearchCriteria.build(keywords=["data engineer", "devops engineer"])
    jobs = [
        _job("Data Engineer"),
        _job("DevOps Engineer"),
        _job("Graphic Designer"),
    ]
    kept = {job.title for job in job_filter.apply(jobs, criteria)}
    assert kept == {"Data Engineer", "DevOps Engineer"}


def test_non_indian_postings_are_dropped_by_default():
    criteria = SearchCriteria.build(keywords=["backend engineer"])
    jobs = [
        _job("Backend Engineer", location="Bengaluru, India"),
        _job("Backend Engineer", location="Austin, TX"),
    ]
    kept = job_filter.apply(jobs, criteria)
    assert [job.location for job in kept] == ["Bengaluru, India"]


def test_india_scope_can_be_turned_off():
    criteria = SearchCriteria.build(keywords=["backend engineer"], india_only=False)
    jobs = [_job("Backend Engineer", location="Austin, TX")]
    assert len(job_filter.apply(jobs, criteria)) == 1


def test_remote_only_drops_onsite_roles():
    criteria = SearchCriteria.build(keywords=["backend engineer"], remote=True)
    jobs = [
        _job("Backend Engineer", location="Remote - India", remote=True),
        _job("Backend Engineer", location="Bengaluru, India", remote=False),
    ]
    kept = job_filter.apply(jobs, criteria)
    assert [job.remote for job in kept] == [True]


def test_results_are_ranked_with_the_best_match_first():
    criteria = SearchCriteria.build(keywords=["react developer"])
    jobs = [
        _job("Frontend Engineer", skills=["React"]),      # skill hit only
        _job("React Developer", skills=["React"]),        # title hit
    ]
    assert [job.title for job in job_filter.apply(jobs, criteria)][0] == "React Developer"


def test_criteria_are_deduplicated_and_capped():
    criteria = SearchCriteria.build(
        keywords=["Backend Engineer", "backend engineer", "A", "B", "C", "D"],
        locations=["Pune", "  Pune  "],
    )
    assert criteria.keywords == ("Backend Engineer", "A", "B")
    assert criteria.locations == ("Pune",)


# ────────────────────────── manager fan-out and gate ─────────────────────────

class _FakeSource:
    """Records what it was asked, and returns a fixed list."""

    def __init__(self, name, jobs, uses_location_param=True):
        self.source_name = name
        self.uses_location_param = uses_location_param
        self._jobs = jobs
        self.calls = []

    async def search(self, keyword, location=None, remote=False, page=1):
        self.calls.append((keyword, location))
        return list(self._jobs)


@pytest.mark.anyio
async def test_the_manager_returns_only_what_answers_the_search():
    from app.services.sources.manager import SourceManager

    source = _FakeSource("fake", [
        _job("Data Engineer", skills=["Spark"], source="fake"),
        _job("Graphic Designer", source="fake"),
        _job("Data Engineer", location="Austin, TX", source="fake"),
    ])
    manager = SourceManager(sources=[source])

    results = await manager.fetch(SearchCriteria.build(keywords=["data engineer"]))

    assert [(job.title, job.location) for job in results] == [
        ("Data Engineer", "Bengaluru, India")
    ]


@pytest.mark.anyio
async def test_every_city_is_searched_not_just_the_first():
    """
    The fan-out used to take `locations[0]` and drop the rest, so a resume
    listing three preferred cities was only ever searched in one of them.
    """
    from app.services.sources.manager import SourceManager

    source = _FakeSource("fake", [])
    manager = SourceManager(sources=[source])

    await manager.fetch(
        SearchCriteria.build(keywords=["backend"], locations=["Pune", "Hyderabad"])
    )

    assert {location for _, location in source.calls} == {"Pune", "Hyderabad"}


@pytest.mark.anyio
async def test_a_board_source_is_not_refetched_once_per_city():
    """
    Sources with no location parameter return the same list whatever city is
    asked for, so asking once per city is pure waste.
    """
    from app.services.sources.manager import SourceManager

    board = _FakeSource("board", [], uses_location_param=False)
    manager = SourceManager(sources=[board])

    await manager.fetch(
        SearchCriteria.build(keywords=["backend"], locations=["Pune", "Hyderabad", "Delhi"])
    )

    assert board.calls == [("backend", None)]


@pytest.mark.anyio
async def test_one_failing_source_does_not_sink_the_search():
    from app.services.sources.manager import SourceManager

    class _Broken:
        source_name = "broken"
        uses_location_param = True

        async def search(self, **kwargs):
            raise RuntimeError("upstream is down")

    working = _FakeSource("fake", [_job("Data Engineer", skills=["Spark"], source="fake")])
    manager = SourceManager(sources=[_Broken(), working])

    results = await manager.fetch(SearchCriteria.build(keywords=["data engineer"]))
    assert [job.title for job in results] == ["Data Engineer"]


# ──────────────────────── database-side location aliases ─────────────────────

def test_location_aliases_cover_the_stored_spellings():
    aliases = location_aliases("Bangalore")
    assert "bengaluru" in aliases and "bangalore" in aliases


def test_a_country_query_expands_to_the_whole_market():
    aliases = location_aliases("India")
    assert {"bengaluru", "pune", "karnataka"} <= set(aliases)
