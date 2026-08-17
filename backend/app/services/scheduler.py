"""
Background scheduler for loops.

An asyncio task inside the API process rather than Celery or a cron container:
the workload is a handful of HTTP fetches on a multi-hour cadence, and adding
a broker plus a worker image for that would cost more operationally than it
returns. If loops ever grow to a scale where a single process is the wrong
place for them, this is the seam to replace.
"""

import asyncio
import logging

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.services.loop_service import due_loops, run_loop

logger = logging.getLogger("jobpulse.scheduler")

_task: asyncio.Task | None = None


async def _tick() -> None:
    """One pass: run every loop whose cadence has elapsed."""
    async with AsyncSessionLocal() as db:
        loops = await due_loops(db)
        if not loops:
            return

        logger.info("Scheduler: %d loop(s) due.", len(loops))
        for loop in loops:
            # run_loop never raises; a failing loop is recorded on the row and
            # must not stop the ones behind it.
            await run_loop(db, loop)


async def _scheduler_forever() -> None:
    interval = max(60, settings.LOOP_SCHEDULER_INTERVAL_SECONDS)
    logger.info("Loop scheduler started (every %ds).", interval)

    while True:
        try:
            await _tick()
        except asyncio.CancelledError:
            raise
        except Exception:
            # A failure inside the tick itself (e.g. the DB being down) must
            # not kill the scheduler permanently — log it and try again.
            logger.exception("Scheduler tick failed; continuing.")

        await asyncio.sleep(interval)


def start() -> None:
    global _task
    if not settings.LOOP_SCHEDULER_ENABLED:
        logger.info("Loop scheduler disabled by configuration.")
        return
    if _task is not None and not _task.done():
        return
    _task = asyncio.create_task(_scheduler_forever(), name="jobpulse-loop-scheduler")


async def stop() -> None:
    global _task
    if _task is None:
        return
    _task.cancel()
    try:
        await _task
    except asyncio.CancelledError:
        pass
    finally:
        _task = None
        logger.info("Loop scheduler stopped.")
