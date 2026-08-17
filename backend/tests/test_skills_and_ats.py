"""Tests for skill extraction, canonical identity, and the ATS checker."""

from app.schemas.ai import AtsCheckRequest, ResumeProfile, TailorResumeRequest
from app.services.ai.heuristic import heuristic_ats_check, heuristic_tailor
from app.services.job_identity import job_fingerprint
from app.services.skill_extractor import extract_skills, normalize_skills, strip_html


# ------------------------------------------------------------ skill mining

def test_extracts_skills_from_a_description():
    skills = extract_skills(
        "You will build services in Python and deploy them to Kubernetes on AWS."
    )
    assert {"Python", "Kubernetes", "AWS"} <= set(skills)


def test_word_boundaries_prevent_false_positives():
    """'Go' must not fire on 'Django', and 'React' must not fire on 'reactive'."""
    skills = extract_skills("We use Django. Our culture is reactive and fast-moving.")
    assert "Go" not in skills
    assert "React" not in skills
    assert "Django" in skills


def test_html_is_stripped_before_matching():
    assert "Python" in extract_skills("<p>Strong <b>Python</b> experience</p>")
    assert "<" not in strip_html("<p>hello</p>")


def test_corroborated_source_tags_are_kept():
    """A tag the description backs up is a real requirement."""
    result = normalize_skills(
        ["Salesforce"], "You will administer Salesforce and write Terraform.", "SRE"
    )
    assert "Salesforce" in result    # tag corroborated by the description
    assert "Terraform" in result     # mined from the description


def test_uncorroborated_source_tags_are_dropped():
    """
    Remotive tags a posting with its browse categories, not its requirements —
    a real "Senior DevOps Engineer" arrived tagged php/ios/android/.Net. Those
    made the matcher measure coverage against noise, so they are discarded
    unless the job text mentions them.
    """
    result = normalize_skills(
        ["php", "ios", "android", ".Net", "data science"],
        "We run Kubernetes on AWS and automate with Terraform.",
        "Senior DevOps Engineer",
    )
    assert {"Kubernetes", "AWS", "Terraform"} <= set(result)
    for noise in ("php", "ios", "android", ".Net", "data science"):
        assert noise not in result


def test_duplicate_tags_are_not_repeated():
    result = normalize_skills(["kubernetes", "Kubernetes"], "Kubernetes clusters", "")
    assert len([s for s in result if s.lower() == "kubernetes"]) == 1


def test_skill_count_is_capped():
    everything = " ".join(
        ["Python", "Java", "Docker", "Kubernetes", "AWS", "Azure", "GCP", "React",
         "Vue", "Angular", "Kafka", "Redis", "MongoDB", "MySQL", "Spark", "Airflow",
         "Terraform", "Ansible", "Jenkins", "Grafana"]
    )
    assert len(extract_skills(everything)) <= 15


# ------------------------------------------------------- canonical identity

def test_same_posting_with_cosmetic_differences_shares_a_fingerprint():
    a = job_fingerprint("Acme Corp", "Senior DevOps Engineer", "Worldwide", True)
    b = job_fingerprint("Acme Corp Inc.", "DevOps Engineer (Remote)", "Anywhere", True)
    assert a == b


def test_different_companies_do_not_collide():
    a = job_fingerprint("Acme Corp", "DevOps Engineer", "London", False)
    b = job_fingerprint("Globex", "DevOps Engineer", "London", False)
    assert a != b


def test_different_roles_do_not_collide():
    a = job_fingerprint("Acme", "DevOps Engineer", "London", False)
    b = job_fingerprint("Acme", "Data Scientist", "London", False)
    assert a != b


def test_onsite_roles_in_different_cities_stay_separate():
    a = job_fingerprint("Acme", "DevOps Engineer", "London, UK", False)
    b = job_fingerprint("Acme", "DevOps Engineer", "Berlin, Germany", False)
    assert a != b


# ------------------------------------------------------------- ATS checker

GOOD_RESUME = ResumeProfile(
    full_name="Test Candidate",
    target_role="DevOps Engineer",
    summary="Summary of experience.",
    skills=["Docker", "Kubernetes", "AWS", "Terraform", "Python", "Jenkins"],
    experience_years=5,
    raw_text=(
        "Test Candidate\ntest@example.com | +44 7700 900000\n\n"
        "SUMMARY\nDevOps engineer.\n\n"
        "SKILLS\nDocker, Kubernetes, AWS, Terraform, Python\n\n"
        "EXPERIENCE\nPlatform engineer at Acme. " + "Delivered infrastructure work. " * 60 +
        "\n\nEDUCATION\nB.Tech Computer Science, University of Testing\n"
    ),
)


def test_well_formed_resume_scores_well():
    result = heuristic_ats_check(AtsCheckRequest(resume=GOOD_RESUME))
    assert result.score >= 90
    assert set(result.detected_sections) >= {"Contact", "Skills", "Experience", "Education"}


def test_missing_contact_details_are_flagged_as_critical():
    resume = GOOD_RESUME.model_copy(update={"raw_text": "SKILLS\nDocker\nEXPERIENCE\nWork."})
    result = heuristic_ats_check(AtsCheckRequest(resume=resume))
    assert any(i.severity == "critical" for i in result.issues)
    assert result.score < 90


def test_unparseable_resume_is_called_out():
    resume = GOOD_RESUME.model_copy(update={"raw_text": "", "summary": ""})
    result = heuristic_ats_check(AtsCheckRequest(resume=resume))
    assert result.word_count == 0
    assert any("no text could be extracted" in i.message.lower() for i in result.issues)


def test_ats_score_never_goes_negative():
    resume = ResumeProfile(
        full_name="X", target_role="X", summary="", skills=[], experience_years=0, raw_text=""
    )
    assert heuristic_ats_check(AtsCheckRequest(resume=resume)).score >= 0


# ---------------------------------------------------------------- tailoring

def test_tailoring_reprioritizes_without_inventing():
    request = TailorResumeRequest(
        job_id="1",
        job_title="Kubernetes Platform Engineer",
        company="Acme",
        job_description="You will run Kubernetes and write Go.",
        job_skills=["Kubernetes", "Go"],
        resume=GOOD_RESUME,
    )
    result = heuristic_tailor(request)

    # Relevant skills float to the front...
    assert result.prioritized_skills[0] == "Kubernetes"
    # ...every returned skill is one the candidate actually claimed...
    assert set(result.prioritized_skills) == set(GOOD_RESUME.skills)
    # ...and a requirement they lack is named as a gap, not silently added.
    assert "Go" in result.keywords_to_add
