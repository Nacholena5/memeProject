from fastapi import APIRouter

from app.services.data_quality_service import DataQualityService

router = APIRouter(prefix="/quality", tags=["quality"])


@router.get("/summary")
def quality_summary() -> dict:
    service = DataQualityService()
    return service.compute()
