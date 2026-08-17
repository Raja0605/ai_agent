"""
Role/title matching, tuned for how Indian job boards name roles.

The filter this replaces asked whether every word of the query appeared
*anywhere* in a job's title, company, skills or first 2000 characters of
description. Almost every posting satisfies that. A search for "data engineer"
matched a frontend role whose description happened to say "engineer" in the
boilerplate and "data" in a bullet about analytics — so the role filter passed
through most of the board and the user saw results they had not asked for.

The rule here is that a query's *discriminating* words must show up in the
title or the extracted skills. A description mention is not evidence that a
posting is for that role; it is evidence the words exist in English.

Query words are sorted into three kinds, because they have to be enforced
differently:

* **Seniority** ("senior", "fresher", "SDE-2") — soft. A senior search should
  still surface a role titled just "Backend Engineer", but must not return an
  internship. Enforced as a conflict check, not a requirement.
* **Role nouns** ("engineer", "analyst", "manager") — matched by equivalence
  class. "Developer" and "Engineer" are the same job in this market;
  "Analyst" and "Engineer" are not, so "Data Analyst" must not return "Data
  Engineer".
* **Domain words** ("java", "react", "devops") — hard requirement, satisfied
  by the title or the skill list.

Indian-market specifics that drive the tables below: the SDE ladder is the
default title at most product companies here (Naukri and LinkedIn postings say
"SDE-2" where a US board would say "Senior Software Engineer"), "fresher" is
the standard term for an entry-level candidate and has no US equivalent, and
stacks are advertised by acronym — MERN, MEAN, ".NET Full Stack".
"""

import re
from typing import Iterable, List, Optional, Sequence, Set, Tuple

# Applied to the lowercased string before tokenizing, longest phrase first, so
# multi-word titles collapse to comparable single tokens.
_PHRASE_CANON: List[Tuple[str, str]] = [
    ("software development engineer", "swe"),
    ("member of technical staff", "swe"),
    ("software engineer", "swe"),
    ("software developer", "swe"),
    ("site reliability engineer", "sre engineer"),
    ("machine learning", "ml"),
    ("artificial intelligence", "ai"),
    ("deep learning", "ml"),
    ("data science", "datascience"),
    ("quality assurance", "qa"),
    ("full stack", "fullstack"),
    ("full-stack", "fullstack"),
    ("front end", "frontend"),
    ("front-end", "frontend"),
    ("back end", "backend"),
    ("back-end", "backend"),
    ("dot net", "dotnet"),
    (".net", "dotnet"),
    ("c#", "csharp"),
    ("c++", "cplusplus"),
    ("node.js", "nodejs"),
    ("node js", "nodejs"),
    ("react.js", "react"),
    ("reactjs", "react"),
    ("angular.js", "angular"),
    ("angularjs", "angular"),
    ("vue.js", "vue"),
    ("power bi", "powerbi"),
    ("business intelligence", "bi"),
    ("product manager", "product manager"),
    ("project manager", "project manager"),
]

# Words with no discriminating power. The Indian entries matter: portal titles
# routinely read "Urgent Requirement for Java Developer | 3-5 Yrs | Bangalore".
_STOPWORDS: Set[str] = {
    "a", "an", "the", "and", "or", "of", "for", "in", "at", "to", "with", "on",
    "job", "jobs", "role", "roles", "position", "positions", "opening",
    "openings", "vacancy", "vacancies", "hiring", "requirement", "requirements",
    "required", "urgent", "immediate", "immediately", "joiner", "joiners",
    "experience", "experienced", "exp", "yrs", "yr", "year", "years", "ctc",
    "lpa", "salary", "notice", "period", "wfh", "wfo", "work", "from", "home",
    "opportunity", "opportunities", "we", "are", "is", "new", "only", "apply",
}

# Rough ladder position. Only used to reject a *conflict* between what the user
# asked for and what the posting offers.
_SENIORITY_RANK = {
    "intern": 0, "internship": 0, "trainee": 0, "apprentice": 0,
    "fresher": 1, "freshers": 1, "graduate": 1, "entry": 1, "junior": 1, "jr": 1,
    "associate": 2,
    "mid": 3, "intermediate": 3,
    "senior": 4, "sr": 4,
    "lead": 5, "staff": 5,
    "principal": 6, "head": 7, "director": 7, "vp": 8, "chief": 8,
}

# How far apart two ladder positions must be before they are different jobs.
# 3 puts senior(4) vs junior(1) and fresher(1) vs lead(5) out of range, while
# leaving senior(4) vs mid(3) and lead(5) vs senior(4) as acceptable overlap.
_SENIORITY_CONFLICT_GAP = 3

# Role nouns, grouped by equivalence class. Same class = same job as far as a
# search is concerned; different class = genuinely different work.
_ROLE_CLASSES: List[Set[str]] = [
    {"engineer", "developer", "programmer", "dev", "swe", "sde", "coder"},
    {"analyst"},
    {"scientist"},
    {"architect"},
    {"manager"},
    {"consultant"},
    {"designer"},
    {"administrator", "admin"},
    {"tester", "qa", "sdet"},
    {"specialist"},
    {"executive"},
    {"intern"},
    {"recruiter"},
    {"writer"},
]

_ROLE_NOUN_TO_CLASS = {
    noun: index for index, group in enumerate(_ROLE_CLASSES) for noun in group
}

# Domain words that mean the same thing to a searcher.
_EQUIVALENT_GROUPS: List[Set[str]] = [
    {"fullstack", "mern", "mean"},
    {"ml", "machinelearning"},
    {"ai", "genai"},
    {"devops", "sre"},
    {"dotnet", "csharp"},
    {"nodejs", "node"},
    {"js", "javascript"},
    {"ts", "typescript"},
    {"k8s", "kubernetes"},
    {"gcp", "googlecloud"},
    {"postgres", "postgresql"},
    {"datascience", "datascientist"},
    {"bi", "powerbi"},
]

_EQUIVALENTS: dict[str, Set[str]] = {}
for _group in _EQUIVALENT_GROUPS:
    for _member in _group:
        _EQUIVALENTS.setdefault(_member, set()).update(_group)

_WORD = re.compile(r"[a-z0-9]+")
# Matches an SDE/L level suffix: "SDE-2", "SDE II", "L4".
_LEVEL_SUFFIX = re.compile(r"\b(sde|swe|l)\s*[-–]?\s*([1-4]|i{1,3}|iv)\b")
_LEVEL_TO_RANK = {"1": 1, "i": 1, "2": 3, "ii": 3, "3": 4, "iii": 4, "4": 5, "iv": 5}


def _canonicalize(text: Optional[str]) -> str:
    if not text:
        return ""
    lowered = text.lower()
    for phrase, replacement in _PHRASE_CANON:
        if phrase in lowered:
            lowered = lowered.replace(phrase, f" {replacement} ")
    return lowered


def _tokens(text: Optional[str]) -> List[str]:
    return [word for word in _WORD.findall(_canonicalize(text)) if word not in _STOPWORDS]


def _seniority_rank(text: Optional[str]) -> Optional[int]:
    """
    The ladder position a string advertises, if any.

    Checks the SDE/L level suffix first because "SDE-2" carries a level that
    the plain word list cannot see.
    """
    canonical = _canonicalize(text)

    level = _LEVEL_SUFFIX.search(canonical)
    if level:
        rank = _LEVEL_TO_RANK.get(level.group(2))
        if rank is not None:
            return rank

    ranks = [
        _SENIORITY_RANK[word]
        for word in _WORD.findall(canonical)
        if word in _SENIORITY_RANK
    ]
    # The highest claim wins: "Senior Software Engineer, Associate Director"
    # is a senior role, and titles list the junior word only in passing.
    return max(ranks) if ranks else None


def _role_class(token: str) -> Optional[int]:
    """
    The role-noun class of a token, tolerating a plural.

    Titles are written both ways — "Data Labeling Specialists", "Software
    Engineers" — and without the plural form those titles register as naming
    no role at all, which switches off the check that keeps a specialist role
    out of an engineer search.
    """
    if token in _ROLE_NOUN_TO_CLASS:
        return _ROLE_NOUN_TO_CLASS[token]
    if token.endswith("s") and token[:-1] in _ROLE_NOUN_TO_CLASS:
        return _ROLE_NOUN_TO_CLASS[token[:-1]]
    return None


def _classify(tokens: Iterable[str]) -> Tuple[Set[int], Set[str]]:
    """Split tokens into role-noun classes and discriminating domain words."""
    role_classes: Set[int] = set()
    domain: Set[str] = set()

    for token in tokens:
        if token in _SENIORITY_RANK:
            continue
        role_class = _role_class(token)
        if role_class is not None:
            role_classes.add(role_class)
            continue
        domain.add(token)

    return role_classes, domain


def _satisfied(token: str, haystack: Set[str]) -> bool:
    """Whether a query word — or anything meaning the same — is present."""
    return bool(_EQUIVALENTS.get(token, {token}) & haystack)


def role_relevance(
    query: Optional[str],
    title: str,
    skills: Optional[Sequence[str]] = None,
    company: str = "",
) -> float:
    """
    How well a posting answers a role query, from 0.0 (no) to 1.0 (exactly).

    Returns 1.0 for an empty query: no role was asked for, so nothing is
    excluded. Anything at or above `RELEVANCE_THRESHOLD` is treated as a match
    by `matches_role`; the value itself is used to rank results.
    """
    if not query or not query.strip():
        return 1.0

    query_tokens = _tokens(query)
    if not query_tokens:
        return 1.0

    title_tokens = set(_tokens(title))
    skill_tokens: Set[str] = set()
    for skill in skills or []:
        skill_tokens.update(_tokens(skill))
    company_tokens = set(_tokens(company))

    # Searching a company by name is a first-class use of the same box — the
    # UI labels it "Role, skill or company".
    if company_tokens and set(query_tokens) <= company_tokens:
        return 1.0

    query_roles, query_domain = _classify(query_tokens)
    title_roles, title_domain = _classify(title_tokens)

    # ── Seniority: reject only a real conflict ───────────────────────────
    query_rank = _seniority_rank(query)
    title_rank = _seniority_rank(title)
    if (
        query_rank is not None
        and title_rank is not None
        and abs(query_rank - title_rank) >= _SENIORITY_CONFLICT_GAP
    ):
        return 0.0

    # ── Role noun: must agree when both sides name one ───────────────────
    # A posting titled "Backend — Payments Platform" names no role noun; that
    # is not evidence against it, so the check only bites when both declare.
    if query_roles and title_roles and not (query_roles & title_roles):
        return 0.0

    # ── Domain words: the hard requirement ───────────────────────────────
    if not query_domain:
        # Query was purely a role noun ("engineer", "senior manager"). The
        # checks above are all the signal available.
        return 1.0 if not query_roles or (query_roles & title_roles) else 0.55

    searchable = title_domain | skill_tokens
    hits_in_title = sum(1 for token in query_domain if _satisfied(token, title_domain))
    hits_anywhere = sum(1 for token in query_domain if _satisfied(token, searchable))

    if hits_anywhere < len(query_domain):
        return 0.0

    # A query naming a role ("data analyst") against a title that names none
    # ("Assistant Account Payable") has nothing to agree on, so a skill tag is
    # the only evidence — too thin. Require the title itself to carry the
    # domain word in that case. Titles that do name a role are unaffected, so
    # "react developer" still matches "Frontend Engineer" on its React skill.
    if query_roles and not title_roles and not hits_in_title:
        return 0.0

    # Every domain word is accounted for. Rank on how many landed in the
    # title, which is a much stronger signal than a skill-tag match.
    title_share = hits_in_title / len(query_domain)
    return 0.7 + 0.3 * title_share


#: Minimum relevance for a posting to count as answering the query.
RELEVANCE_THRESHOLD = 0.5


def matches_role(
    query: Optional[str],
    title: str,
    skills: Optional[Sequence[str]] = None,
    company: str = "",
) -> bool:
    """Whether a posting is actually for the role that was searched for."""
    return role_relevance(query, title, skills, company) >= RELEVANCE_THRESHOLD
