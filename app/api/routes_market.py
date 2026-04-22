from fastapi import APIRouter

from app.services.market_context_service import MarketContextService

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/context")
async def market_context() -> dict:
    service = MarketContextService()
    return await service.compute_context()
