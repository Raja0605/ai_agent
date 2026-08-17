"""
Live smoke test for the search path.

Hits the real sources and reports what they returned versus what survived the
role/location filter. The company career boards need no credentials, so this
produces meaningful output with an empty `.env` — sources that need a key log
a "skipping" line and contribute nothing.

The tests in `tests/` cover the rules in isolation with no network. This is
the complement: proof that the rules do the right thing against live listings.

    cd backend
    ./.venv/Scripts/python.exe scripts/smoke_search.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Runnable directly, without needing PYTHONPATH set.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import job_filter                       # noqa: E402
from app.services.job_filter import SearchCriteria        # noqa: E402
from app.services.sources.manager import SourceManager    # noqa: E402

logging.basicConfig(level=logging.WARNING)


async def probe(manager, everything, label, **kwargs):
    """Filter the already-fetched listings and report what survives."""
    criteria = SearchCriteria.build(**kwargs)
    kept = job_filter.apply(everything, criteria)

    print(f"\n{'=' * 72}")
    print(label)
    print(f"  roles={criteria.keywords or '(any)'}  cities={criteria.locations or '(any)'}"
          f"  remote={criteria.remote}  india_only={criteria.india_only}")
    print(f"{'=' * 72}")
    print(f"  fetched          : {len(everything)}")
    print(f"  passed the filter: {len(kept)}")

    by_source: dict[str, int] = {}
    for job in kept:
        by_source[job.source] = by_source.get(job.source, 0) + 1
    if by_source:
        print(f"  by source        : {by_source}")

    for job in kept[:8]:
        print(f"    - {job.title[:52]:<52} | {job.location[:26]:<26} | {job.company[:18]}")
    if not kept:
        print("    (nothing matched)")

    return kept


async def main():
    manager = SourceManager()
    print("Registered sources:", [s.source_name for s in manager.sources])
    print("Sources needing an API key log a 'skipping' line and return nothing.\n")

    # Fetched once with no criteria, then filtered repeatedly — the sources
    # are asked for their listings, not re-queried per scenario.
    everything = await manager.fetch(SearchCriteria.build(keywords=[], india_only=False))

    await probe(manager, everything, "1. Everything the sources carry, India only",
                keywords=[])
    await probe(manager, everything, "2. Role enforcement: 'data engineer'",
                keywords=["data engineer"])
    await probe(manager, everything, "3. Role + city: 'backend engineer' in Bangalore",
                keywords=["backend engineer"], locations=["Bangalore"])
    await probe(manager, everything, "4. Alias check: the same search spelled 'Bengaluru'",
                keywords=["backend engineer"], locations=["Bengaluru"])
    await probe(manager, everything, "5. Remote only",
                keywords=["engineer"], remote=True)
    await probe(manager, everything, "6. Negative control: a role nobody is hiring for",
                keywords=["underwater basket weaver"])

    # The specific false positive this filter exists to prevent: matching on
    # the description made "data engineer" return most of the board.
    print(f"\n{'=' * 72}")
    print("7. False-positive check: does 'data engineer' return non-data roles?")
    print(f"{'=' * 72}")
    kept = job_filter.apply(everything, SearchCriteria.build(keywords=["data engineer"]))
    off_target = [
        job for job in kept
        if not any(word in job.title.lower()
                   for word in ("data", "analytics", "ml", "machine"))
    ]
    print(f"  matched {len(kept)}; {len(off_target)} have no data-ish word in the title")
    for job in off_target[:10]:
        print(f"    ? {job.title} | skills={job.skills[:6]}")
    if not off_target:
        print("  clean — every match is genuinely a data role")


if __name__ == "__main__":
    if sys.platform == "win32":
        # The default proactor loop can emit spurious connection-reset noise
        # on shutdown when many HTTPS clients close at once.
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
