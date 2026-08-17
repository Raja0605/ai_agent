"""
Skill extraction from free-text job descriptions.

Sources are wildly inconsistent about skills: Remotive returns real tags,
Adzuna returns nothing usable (its adapter used to echo the search keyword
back as the only "skill"). Anything that reaches the matcher with an empty or
fake skill list produces a meaningless match score, so descriptions are mined
for a known vocabulary instead.

This is deliberately a curated vocabulary rather than an NLP model: it is
dependency-free, deterministic, and easy to audit when a score looks wrong.
"""

import re
from typing import Iterable, List

# Canonical skill name -> patterns that should map onto it.
# Patterns are matched case-insensitively against the description with word
# boundaries, so "Go" does not match "Django" and "R" does not match "React".
_SKILL_PATTERNS: dict[str, List[str]] = {
    # Cloud / platform
    "AWS": [r"aws", r"amazon web services", r"\bec2\b", r"\bs3\b", r"\beks\b"],
    "Azure": [r"azure"],
    "GCP": [r"gcp", r"google cloud"],
    "Kubernetes": [r"kubernetes", r"\bk8s\b"],
    "Docker": [r"docker"],
    "Terraform": [r"terraform"],
    "Ansible": [r"ansible"],
    "Helm": [r"helm"],
    "ArgoCD": [r"argo\s?cd", r"argocd"],
    "Linux": [r"linux", r"unix"],
    "CI/CD": [r"ci/cd", r"ci-cd", r"continuous integration", r"continuous delivery"],
    "Jenkins": [r"jenkins"],
    "GitHub Actions": [r"github actions"],
    "GitLab CI": [r"gitlab ci"],
    "Prometheus": [r"prometheus"],
    "Grafana": [r"grafana"],
    "Datadog": [r"datadog"],
    "Vault": [r"hashicorp vault", r"\bvault\b"],
    "Serverless": [r"serverless", r"lambda functions?"],
    # Languages
    "Python": [r"python"],
    "JavaScript": [r"javascript"],
    "TypeScript": [r"typescript"],
    "Java": [r"\bjava\b"],
    "Go": [r"\bgolang\b", r"\bgo lang\b"],
    "Ruby": [r"\bruby\b"],
    "PHP": [r"\bphp\b"],
    "C#": [r"c#", r"\.net\b", r"dotnet"],
    "C++": [r"c\+\+"],
    "Rust": [r"\brust\b"],
    "Scala": [r"\bscala\b"],
    "Kotlin": [r"kotlin"],
    "Swift": [r"\bswift\b"],
    "Bash": [r"\bbash\b", r"shell scripting"],
    # Frontend
    "React": [r"\breact\b", r"react\.js", r"reactjs"],
    "Vue": [r"\bvue\b", r"vue\.js", r"vuejs"],
    "Angular": [r"angular"],
    "Next.js": [r"next\.js", r"nextjs"],
    "Tailwind": [r"tailwind"],
    "HTML/CSS": [r"\bhtml\b", r"\bcss\b"],
    # Backend / data
    "Node.js": [r"node\.js", r"nodejs", r"\bnode\b"],
    "Django": [r"django"],
    "Flask": [r"flask"],
    "FastAPI": [r"fastapi"],
    "Spring": [r"spring boot", r"\bspring\b"],
    "GraphQL": [r"graphql"],
    "REST APIs": [r"rest api", r"restful"],
    "gRPC": [r"grpc"],
    "SQL": [r"\bsql\b"],
    "PostgreSQL": [r"postgres", r"postgresql"],
    "MySQL": [r"mysql"],
    "MongoDB": [r"mongodb", r"\bmongo\b"],
    "Redis": [r"redis"],
    "Elasticsearch": [r"elasticsearch", r"\belastic\b"],
    "Kafka": [r"kafka"],
    "RabbitMQ": [r"rabbitmq"],
    "Spark": [r"\bspark\b", r"pyspark"],
    "Airflow": [r"airflow"],
    "dbt": [r"\bdbt\b"],
    "Snowflake": [r"snowflake"],
    # ML / AI
    "Machine Learning": [r"machine learning", r"\bml\b"],
    "PyTorch": [r"pytorch"],
    "TensorFlow": [r"tensorflow"],
    "LLMs": [r"\bllm\b", r"large language model"],
    # Practices
    "Agile": [r"\bagile\b", r"\bscrum\b"],
    "Microservices": [r"microservices?"],
    "Testing": [r"unit test", r"\bpytest\b", r"\bjest\b", r"test automation"],
    "Security": [r"devsecopsc?", r"\bappsec\b", r"security best practices"],
    "Git": [r"\bgit\b"],
}

# Compiled once at import; the endpoint path runs this per job.
_COMPILED: list[tuple[str, re.Pattern[str]]] = [
    (skill, re.compile("|".join(patterns), re.IGNORECASE))
    for skill, patterns in _SKILL_PATTERNS.items()
]

_HTML_TAG = re.compile(r"<[^>]+>")

# Upper bound on skills attached to one job. A job matching 40 vocabulary terms
# is a job whose description lists an entire tech radar; keeping every one of
# them would let a long description dominate the match denominator.
MAX_SKILLS_PER_JOB = 15


def strip_html(text: str) -> str:
    """Remotive descriptions arrive as HTML; match against the text only."""
    return _HTML_TAG.sub(" ", text or "")


def extract_skills(description: str, title: str = "", limit: int = MAX_SKILLS_PER_JOB) -> List[str]:
    """
    Mine text for known technical skills.

    Returns canonical skill names, ordered by the vocabulary's own order so the
    result is stable across runs for the same input. `limit` is raised for
    resumes, where a long skill list is the candidate's actual breadth rather
    than an employer padding a job ad.
    """
    haystack = f"{title}\n{strip_html(description)}"
    if not haystack.strip():
        return []

    found = [skill for skill, pattern in _COMPILED if pattern.search(haystack)]
    return found[:limit]


def _tag_is_corroborated(tag: str, haystack: str) -> bool:
    """
    Whether a source-provided tag is actually backed by the job text.

    Live Remotive data settled this: a "Senior DevOps Engineer" posting came
    tagged php, golang, java, ios, android, C#, .Net and data science. Those
    are the board's browse categories, not the role's requirements — and
    trusting them made the matcher measure skill coverage against noise, so a
    genuine DevOps match scored 48%.

    A tag that the description also mentions is a real requirement. One that
    it never mentions is a category label, and is dropped.
    """
    tokens = [t for t in re.findall(r"[a-z0-9+#.]+", tag.lower()) if t]
    if not tokens:
        return False
    return all(
        re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", haystack)
        for token in tokens
    )


def normalize_skills(raw_skills: Iterable[str], description: str = "", title: str = "") -> List[str]:
    """
    Build the final skill list for a job.

    The description is the authority. Source tags are included only when the
    job text corroborates them; unsupported tags are discarded. Comparison is
    case-insensitive so a tag of "kubernetes" is not duplicated alongside the
    extractor's "Kubernetes".
    """
    haystack = f"{title}\n{strip_html(description)}".lower()

    result: List[str] = []
    seen: set[str] = set()

    # Description-mined skills first — these are the ones with evidence.
    for skill in extract_skills(description, title):
        if skill.lower() not in seen:
            seen.add(skill.lower())
            result.append(skill)

    # Then any source tag the text actually supports, which catches
    # domain-specific terms the curated vocabulary does not cover.
    for skill in raw_skills or []:
        cleaned = (skill or "").strip()
        if not cleaned or cleaned.lower() in seen:
            continue
        if not _tag_is_corroborated(cleaned, haystack):
            continue
        seen.add(cleaned.lower())
        result.append(cleaned)

    return result[:MAX_SKILLS_PER_JOB]
