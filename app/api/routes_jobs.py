from fastapi import APIRouter

from app.jobs.run_scan_job import run_scan_cycle

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/run-scan")
async def run_scan() -> dict:
    top = await run_scan_cycle()
    return {"count": len(top), "top": top}
