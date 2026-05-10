import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.check_engine import run_fleet_checks
from app.services.triage_service import triage_failed_checks

logger = logging.getLogger(__name__)
settings = get_settings()

_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    global _scheduler
    if not settings.scheduler_enabled:
        logger.info("Scheduled checks are disabled")
        return
    if _scheduler and _scheduler.running:
        return

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        _run_scheduled_checks,
        "interval",
        seconds=settings.health_check_interval_seconds,
        id="fleet-health-checks",
        replace_existing=True,
        max_instances=1,
    )
    _scheduler.start()
    logger.info("Scheduled checks enabled every %s seconds", settings.health_check_interval_seconds)


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduled checks stopped")
    _scheduler = None


def _run_scheduled_checks() -> None:
    db = SessionLocal()
    try:
        result = asyncio.run(run_fleet_checks(db=db, active_only=True))
        logger.info("Scheduled fleet check completed run_id=%s devices=%s", result.run_id, result.checked_devices)
        if settings.auto_triage_enabled:
            triage_failed_checks(db=db)
    except Exception:
        logger.exception("Scheduled fleet check failed")
    finally:
        db.close()
