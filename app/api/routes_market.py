from fastapi import APIRouter

from app.services.event_sentiment_service import EventSentimentService
from app.services.market_context_service import MarketContextService

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/context")
async def market_context() -> dict:
    service = MarketContextService()
    return await service.compute_context()


@router.get("/events")
async def market_events() -> dict:
    service = EventSentimentService()
    return await service.compute_event_context()
