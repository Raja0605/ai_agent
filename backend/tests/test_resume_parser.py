"""
Resume parsing tests.

The parser previously guessed an experience figure when the resume did not
state one ("2 if any skills were found"), and the browser held a second copy
that assigned everyone a flat 4 years. That number feeds directly into the
match score, so a guess there is a fabricated input to a user-facing result.
"""

from app.services.resume_parser import parse_resume_text

RESUME = """Alex Tester
alex@example.com | +44 7700 900111

SUMMARY
DevOps engineer with 6 years of experience running production infrastructure.

SKILLS
Docker, Kubernetes, Terraform, AWS, Python, Jenkins, Linux

EXPERIENCE
DevOps Engineer at Acme. Built CI/CD pipelines with Jenkins on AWS EKS.

EDUCATION
B.Tech Computer Science
"""


def test_skills_use_the_shared_canonical_vocabulary():
    """Same casing as job-side extraction, so the two are comparable."""
    skills = parse_resume_text(RESUME)["extracted_skills"]
    assert {"Docker", "Kubernetes", "Terraform", "AWS", "Python", "Jenkins", "Linux"} <= set(skills)
    # Not the lowercase forms the old parser emitted.
    assert "docker" not in skills


def test_stated_experience_is_read_from_the_text():
    assert parse_resume_text(RESUME)["experience_years"] == 6


def test_unstated_experience_is_zero_not_guessed():
    text = "Jane Doe\njane@example.com\n\nSKILLS\nPython, Docker, Kubernetes"
    assert parse_resume_text(text)["experience_years"] == 0


def test_absurd_experience_figures_are_rejected():
    """A '2015 years' typo or a stray year must not become the candidate's experience."""
    text = "Worked here since 2015. 99 years experience with Python."
    assert parse_resume_text(text)["experience_years"] == 0


def test_target_role_is_read_from_the_text_when_stated():
    assert "DevOps Engineer" in parse_resume_text(RESUME)["target_roles"]


def test_target_role_falls_back_to_skill_hints():
    text = "SKILLS\nReact, TypeScript, Vue"
    assert "Frontend Developer" in parse_resume_text(text)["target_roles"]


def test_empty_resume_produces_empty_results_not_defaults():
    parsed = parse_resume_text("")
    assert parsed["extracted_skills"] == []
    assert parsed["experience_years"] == 0
