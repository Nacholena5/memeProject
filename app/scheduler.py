from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import get_settings
from app.jobs.run_metrics_job import MetricsJob
from app.jobs.run_outcome_job import OutcomeJob
from app.jobs.run_scan_job import run_scan_cycle


def build_scheduler() -> AsyncIOScheduler:
    settings = get_settings()
    metrics_job = MetricsJob()
    outcome_job = OutcomeJob()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_scan_cycle, "interval", seconds=settings.scan_interval_seconds, id="scan-cycle", replace_existing=True)
    scheduler.add_job(outcome_job.run, "interval", minutes=15, id="outcome-cycle", replace_existing=True)
    scheduler.add_job(metrics_job.run, "interval", hours=1, id="metrics-cycle", replace_existing=True)
    return scheduler
