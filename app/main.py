from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes_dashboard import router as dashboard_router
from app.api.routes_exports import router as exports_router
from app.api.routes_health import router as health_router
from app.api.routes_jobs import router as jobs_router
from app.api.routes_market import router as market_router
from app.api.routes_metrics import router as metrics_router
from app.api.routes_narratives import router as narratives_router
from app.api.routes_outcomes import router as outcomes_router
from app.api.routes_breakouts import router as breakouts_router
from app.api.routes_debug import router as debug_router
from app.api.routes_exit_plans import router as exit_plans_router
from app.api.routes_quality import router as quality_router
from app.api.routes_scanner import router as scanner_router
from app.api.routes_signals import router as signals_router
from app.api.routes_tokens import router as tokens_router
from app.api.routes_wallets import router as wallets_router
from app.config import get_settings
from app.logging_setup import setup_logging
from app.scheduler import build_scheduler
from app.storage.db import init_db

scheduler = build_scheduler()


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
    init_db()
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)
static_dir = Path(__file__).resolve().parent / "web" / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.include_router(dashboard_router)
app.include_router(health_router)
app.include_router(signals_router)
app.include_router(tokens_router)
app.include_router(outcomes_router)
app.include_router(metrics_router)
app.include_router(market_router)
app.include_router(quality_router)
app.include_router(scanner_router)
app.include_router(exit_plans_router)
app.include_router(wallets_router)
app.include_router(breakouts_router)
app.include_router(narratives_router)
app.include_router(exports_router)
app.include_router(jobs_router)
app.include_router(debug_router)
