from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.clients.polymarket_client import PolymarketClient
from app.config import get_settings


class EventSentimentService:
    def __init__(self) -> None:
        self.settings = get_settings()
        headers = {}
        if self.settings.polymarket_api_key:
            headers["Authorization"] = f"Bearer {self.settings.polymarket_api_key}"
        self.client = PolymarketClient(self.settings.polymarket_base_url, default_headers=headers)

    @staticmethod
    def _to_float(value: Any) -> float:
        try:
            return float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _keywords_from_text(text: str) -> set[str]:
        return {token.strip().lower() for token in text.split() if token.strip()}

    @staticmethod
    def _score_from_change(change: float) -> float:
        return max(0.0, min(100.0, abs(change) * 16.0))

    @staticmethod
    def _is_negative_event(title: str, description: str) -> bool:
        text = f"{title} {description}".lower()
        negative_terms = ["ban", "regulation", "law", "legal", "tax", "selloff", "crash", "drop", "bear", "recession", "inflation", "sanction", "delist"]
        return any(term in text for term in negative_terms)

    @staticmethod
    def _is_relevant_topic(title: str, description: str) -> bool:
        text = f"{title} {description}".lower()
        positive_terms = ["solana", "meme", "crypto", "btc", "bitcoin", "macro", "regulation", "event", "catalyst"]
        return any(term in text for term in positive_terms)

    def _parse_event(self, raw: dict[str, Any]) -> dict[str, Any]:
        title = str(raw.get("title") or raw.get("name") or raw.get("question") or "").strip()
        description = str(raw.get("description") or raw.get("summary") or "").strip()
        prob = self._to_float(raw.get("probability") or raw.get("impliedProbability") or raw.get("probability_usd"))
        if 0.0 <= prob <= 1.0:
            prob = prob * 100.0
        probability_change_1h = self._to_float(raw.get("probability_change_1h") or raw.get("probChange1h") or raw.get("p_change_1h") or 0.0)
        probability_change_4h = self._to_float(raw.get("probability_change_4h") or raw.get("probChange4h") or 0.0)
        probability_change_24h = self._to_float(raw.get("probability_change_24h") or raw.get("probChange24h") or 0.0)
        volume_usd = self._to_float(raw.get("volume_usd") or raw.get("liquidity") or raw.get("volume") or 0.0)
        resolution_ts = raw.get("resolution") or raw.get("resolutionDate") or raw.get("resolved_at")
        if isinstance(resolution_ts, str):
            try:
                resolution_at = datetime.fromisoformat(resolution_ts.replace("Z", "+00:00"))
            except ValueError:
                resolution_at = None
        elif isinstance(resolution_ts, (int, float)):
            resolution_at = datetime.fromtimestamp(float(resolution_ts), tz=timezone.utc)
        else:
            resolution_at = None

        now = datetime.now(timezone.utc)
        time_to_resolution = None
        if resolution_at:
            time_delta = resolution_at - now
            time_to_resolution = max(0.0, time_delta.total_seconds() / 3600.0)

        relevance = 60.0 if self._is_relevant_topic(title, description) else 25.0
        sentiment = self._score_from_change(probability_change_24h)
        if probability_change_24h < 0.0:
            sentiment = max(0.0, 50.0 - sentiment)

        return {
            "market_id": str(raw.get("id") or raw.get("marketId") or title)[:64],
            "title": title,
            "description": description,
            "probability": round(min(max(prob, 0.0), 100.0), 1),
            "probability_change_1h": probability_change_1h,
            "probability_change_4h": probability_change_4h,
            "probability_change_24h": probability_change_24h,
            "volume_usd": volume_usd,
            "resolution_at": resolution_at.isoformat() if resolution_at else None,
            "hours_to_resolution": round(time_to_resolution, 1) if time_to_resolution is not None else None,
            "is_negative": self._is_negative_event(title, description),
            "is_relevant": self._is_relevant_topic(title, description),
            "source": raw.get("source") or "polymarket",
            "confidence": 0.7 if self._is_relevant_topic(title, description) else 0.4,
            "raw_json": raw,
        }

    async def compute_event_context(self) -> dict[str, Any]:
        if not self.settings.polymarket_enabled:
            return {
                "status": "disabled",
                "reason": "Polymarket integration no habilitada",
                "source_freshness": "disabled",
                "confidence": 0.0,
                "top_events": [],
                "computed_at": datetime.now(timezone.utc).isoformat(),
            }

        keywords = [term.strip() for term in self.settings.polymarket_search_terms.split(",") if term.strip()]
        events: list[dict[str, Any]] = []
        for query in keywords:
            rows = await self.client.search_markets(query=query, limit=24)
            for raw in rows:
                parsed = self._parse_event(raw)
                if parsed["title"]:
                    events.append(parsed)

        if not events:
            return {
                "status": "insufficient_data",
                "reason": "No se detectaron mercados relevantes en Polymarket",
                "source_freshness": "stale",
                "confidence": 0.0,
                "top_events": [],
                "computed_at": datetime.now(timezone.utc).isoformat(),
            }

        unique: dict[str, dict[str, Any]] = {}
        for event in events:
            unique[event["market_id"]] = event
        events = list(unique.values())
        events.sort(key=lambda item: (item["volume_usd"] or 0.0), reverse=True)

        positive = [e for e in events if e["probability_change_24h"] > 0.0]
        negative = [e for e in events if e["probability_change_24h"] < 0.0]
        avg_sentiment = sum(e["probability_change_24h"] for e in events) / max(1, len(events))
        consensus_shift = sum(abs(e["probability_change_24h"]) for e in events) / max(1, len(events))
        macro_risk = sum(1.0 for e in events if e["is_negative"]) / max(1, len(events)) * 100.0
        relevance = sum(1.0 for e in events if e["is_relevant"]) / max(1, len(events)) * 100.0
        urgency = max(0.0, min(100.0, 100.0 - min(e["hours_to_resolution"] or 100.0 for e in events)))
        volume_score = min(100.0, sum(e["volume_usd"] for e in events) / 120000.0)

        return {
            "status": "ok",
            "source_freshness": "realtime",
            "confidence": round(min(0.95, 0.45 + len(events) * 0.03 + relevance * 0.003), 3),
            "relevance_score": round(min(100.0, relevance + 10.0), 1),
            "catalyst_probability_score": round(min(100.0, max((e["probability"] for e in events), default=0.0)), 1),
            "catalyst_urgency_score": round(min(100.0, urgency), 1),
            "event_sentiment_score": round(min(100.0, max(0.0, 50.0 + avg_sentiment * 1.2)), 1),
            "event_volume_score": round(min(100.0, volume_score), 1),
            "consensus_shift_score": round(min(100.0, consensus_shift * 1.8), 1),
            "macro_event_risk_score": round(min(100.0, macro_risk * 0.9), 1),
            "narrative_event_alignment_score": round(min(100.0, relevance * 1.1), 1),
            "top_events": events[:6],
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }

    def token_event_alignment(self, token_symbol: str, token_name: str, validation: dict[str, Any], event_context: dict[str, Any]) -> dict[str, float]:
        if event_context.get("status") != "ok" or not event_context.get("top_events"):
            return {
                "event_relevance_score": 0.0,
                "catalyst_probability_score": 0.0,
                "catalyst_urgency_score": 0.0,
                "event_sentiment_score": 0.0,
                "event_volume_score": 0.0,
                "consensus_shift_score": 0.0,
                "macro_event_risk_score": 0.0,
                "narrative_alignment_score": 0.0,
            }

        token_text = f"{token_symbol} {token_name} {validation.get('primary_pair','')} {validation.get('dex_id','')}".lower()
        relevance_multiplier = 1.0 if any(keyword in token_text for keyword in ["sol", "solana", "meme", token_symbol.lower()]) else 0.55
        relevance_score = event_context.get("relevance_score", 0.0) * relevance_multiplier
        narrative_alignment_score = event_context.get("narrative_event_alignment_score", 0.0) * relevance_multiplier
        catalyst_probability_score = event_context.get("catalyst_probability_score", 0.0) * relevance_multiplier
        catalyst_urgency_score = event_context.get("catalyst_urgency_score", 0.0) if relevance_multiplier > 0.6 else event_context.get("catalyst_urgency_score", 0.0) * 0.5
        event_sentiment_score = event_context.get("event_sentiment_score", 0.0) * relevance_multiplier
        event_volume_score = event_context.get("event_volume_score", 0.0) * relevance_multiplier
        consensus_shift_score = event_context.get("consensus_shift_score", 0.0) * (1.0 if relevance_multiplier > 0.8 else 0.75)
        macro_event_risk_score = event_context.get("macro_event_risk_score", 0.0)

        return {
            "event_relevance_score": round(min(100.0, relevance_score), 1),
            "catalyst_probability_score": round(min(100.0, catalyst_probability_score), 1),
            "catalyst_urgency_score": round(min(100.0, catalyst_urgency_score), 1),
            "event_sentiment_score": round(min(100.0, event_sentiment_score), 1),
            "event_volume_score": round(min(100.0, event_volume_score), 1),
            "consensus_shift_score": round(min(100.0, consensus_shift_score), 1),
            "macro_event_risk_score": round(min(100.0, macro_event_risk_score), 1),
            "narrative_alignment_score": round(min(100.0, narrative_alignment_score), 1),
        }
