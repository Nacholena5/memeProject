from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, date, datetime

from app.clients.birdeye_client import BirdeyeClient
from app.clients.dexscreener_client import DexScreenerClient
from app.config import Settings, get_settings
from app.services.data_quality_service import DataQualityService
from app.services.identity_classification_service import classify_with_identity_gate
from app.services.event_sentiment_service import EventSentimentService
from app.services.market_context_service import MarketContextService
from app.services.signal_dimension_service import compute_signal_dimensions
from app.services.token_metadata_service import TokenMetadata, resolve_token_metadata
from app.storage.repositories.scanner_repository import ScannerRepository
from app.storage.repositories.signal_repository import SignalRepository


SCAN_LOCK = asyncio.Lock()


@dataclass
class ClassifiedToken:
    token_address: str
    symbol: str
    category: str
    main_reason: str
    explanation: str
    score_long: float
    score_short: float
    confidence: float
    risk_value: float
    risk_label: str
    liquidity_usd: float
    flags: dict[str, bool]
    payload: dict


class PlaybookScannerService:
    def __init__(self) -> None:
        self.settings: Settings = get_settings()
        self.repo = ScannerRepository()
        self.signal_repo = SignalRepository()
        self.market_service = MarketContextService()
        self.event_service = EventSentimentService()
        self.quality_service = DataQualityService()
        self.birdeye = BirdeyeClient(self.settings.birdeye_base_url, self.settings.birdeye_api_key)
        self.dex = DexScreenerClient(self.settings.dexscreener_base_url)

    def is_running(self) -> bool:
        return SCAN_LOCK.locked()

    async def run_scan(self, trigger: str = "manual") -> dict:
        if SCAN_LOCK.locked():
            return {"status": "busy", "message": "scan already running"}

        async with SCAN_LOCK:
            cfg = {
                "trigger": trigger,
                "min_liquidity_usd": self.settings.scanner_min_liquidity_usd,
                "min_volume_1h_usd": self.settings.scanner_min_volume_1h_usd,
                "min_transactions_1h": self.settings.scanner_min_transactions_1h,
                "min_token_age_minutes": self.settings.scanner_min_token_age_minutes,
                "max_token_age_hours": self.settings.scanner_max_token_age_hours,
            }
            source_summary = {
                "birdeye": "pending",
                "dexscreener": "pending",
                "dashboard_scores": "pending",
            }
            session_id = self.repo.create_session(config_json=cfg, source_summary_json=source_summary)
            degraded_reasons: list[str] = []

            try:
                discovered, source_mode = await self._discover_candidates(degraded_reasons)
                source_summary["birdeye"] = source_mode
                for row in discovered:
                    row["scan_session_id"] = session_id
                self.repo.add_discovery_candidates(discovered)

                validations, flag_rows, dex_mode = await self._validate_candidates(discovered, degraded_reasons)
                source_summary["dexscreener"] = dex_mode
                for row in validations:
                    row["scan_session_id"] = session_id
                for row in flag_rows:
                    row["scan_session_id"] = session_id
                self.repo.add_dex_validations(validations)
                self.repo.add_flags(flag_rows)

                market_context = await self.market_service.compute_context()
                event_context = await self.event_service.compute_event_context()
                quality = self.quality_service.compute()
                source_summary["dashboard_scores"] = "ok"
                source_summary["polymarket"] = event_context.get("status", "disabled")

                classified, signal_snapshots = self._classify(validations, market_context, quality, event_context, session_id)
                watchlist_rows, discarded_rows = self._build_watchlist_rows(classified, session_id)

                self.repo.add_signal_dimension_snapshots(
                    whale_rows=signal_snapshots["whale"],
                    social_rows=signal_snapshots["social"],
                    demand_rows=signal_snapshots["demand"],
                    narrative_rows=signal_snapshots["narrative"],
                    breakout_rows=signal_snapshots["breakout"],
                    paid_attention_rows=signal_snapshots["paid_attention"],
                    event_signal_rows=signal_snapshots["event_signal"],
                    composite_rows=signal_snapshots["composite"],
                    exit_plan_rows=signal_snapshots["exit_plan"],
                )
                self.repo.add_wallet_intelligence_snapshots(
                    wallet_flow_rows=signal_snapshots["wallet_flow"],
                    holder_distribution_rows=signal_snapshots["holder_distribution"],
                )
                self.repo.add_watchlist_entries(watchlist_rows)
                self.repo.add_discarded_entries(discarded_rows)

                degraded = len(degraded_reasons) > 0 or market_context.get("status") != "ok" or quality.get("status") != "ok"
                notes = {
                    "degraded_reasons": degraded_reasons,
                    "market_status": market_context.get("status"),
                    "quality_status": quality.get("status"),
                }

                self.repo.complete_session(
                    session_id,
                    status="completed",
                    degraded=degraded,
                    discovered_count=len(discovered),
                    validated_count=len(validations),
                    classified_count=len(classified),
                    watchlist_count=len(watchlist_rows),
                    discarded_count=len(discarded_rows),
                    source_summary_json=source_summary,
                    notes_json=notes,
                )

                return {
                    "status": "completed",
                    "scan_session_id": session_id,
                    "degraded": degraded,
                    "degraded_reasons": degraded_reasons,
                    "discovered": len(discovered),
                    "validated": len(validations),
                    "classified": len(classified),
                    "watchlist": len(watchlist_rows),
                    "discarded": len(discarded_rows),
                }
            except Exception as exc:  # noqa: BLE001
                degraded_reasons.append(f"scan error: {exc}")
                self.repo.complete_session(
                    session_id,
                    status="failed",
                    degraded=True,
                    discovered_count=0,
                    validated_count=0,
                    classified_count=0,
                    watchlist_count=0,
                    discarded_count=0,
                    source_summary_json=source_summary,
                    notes_json={"degraded_reasons": degraded_reasons},
                )
                return {
                    "status": "failed",
                    "scan_session_id": session_id,
                    "degraded": True,
                    "degraded_reasons": degraded_reasons,
                }

    async def _discover_candidates(self, degraded_reasons: list[str]) -> tuple[list[dict], str]:
        rows = await self.birdeye.recent_listings(limit=self.settings.scanner_discovery_limit)
        source_mode = "birdeye"
        if not rows:
            degraded_reasons.append("birdeye empty, fallback to dexscreener search")
            source_mode = "degraded"
            rows = await self.dex.search_pairs("solana meme")
            return self._normalize_discovery_from_dex(rows), "birdeye_fallback_dex"

        normalized = self._normalize_discovery_from_birdeye(rows)
        filtered = [x for x in normalized if self._passes_discovery_thresholds(x)]

        dedup: dict[str, dict] = {}
        for item in filtered:
            dedup[item["token_address"]] = item
        return list(dedup.values()), source_mode

    def _normalize_discovery_from_birdeye(self, rows: list[dict]) -> list[dict]:
        out: list[dict] = []
        now = datetime.now(UTC)
        for row in rows:
            token_address = str(
                row.get("address")
                or row.get("token_address")
                or row.get("mint")
                or row.get("tokenAddress")
                or ""
            ).strip()
            if not token_address:
                continue

            created_at = self._to_datetime(
                row.get("recent_listing_time")
                or row.get("created_at")
                or row.get("createdAt")
                or row.get("listedAt")
            )
            age_minutes = (now - created_at).total_seconds() / 60.0 if created_at else 999999.0
            volume_1h = self._to_float(row.get("v1hUSD") or row.get("volume_1h") or row.get("volume1hUSD"))
            volume_24h = self._to_float(row.get("v24hUSD") or row.get("volume_24h") or row.get("volume24hUSD"))
            txs_1h = self._to_int(row.get("tx1h") or row.get("txns_1h") or row.get("txns1h"))
            buys_1h = self._to_int(row.get("buy1h") or row.get("buys_1h") or row.get("txns1hBuy"))
            sells_1h = self._to_int(row.get("sell1h") or row.get("sells_1h") or row.get("txns1hSell"))
            ratio = buys_1h / max(1, sells_1h)
            liq = self._to_float(row.get("liquidity") or row.get("liquidityUSD") or row.get("liquidity_usd"))
            mcap = self._to_float(row.get("mc") or row.get("market_cap") or row.get("marketCap"))
            price_5m = self._to_float(row.get("priceChange5m") or row.get("price_change_5m") or row.get("priceChangeM5"))
            price_1h = self._to_float(row.get("priceChange1h") or row.get("price_change_1h") or row.get("priceChangeH1"))
            vol_acc = volume_1h / max(1.0, volume_24h)
            metadata = resolve_token_metadata(
                token_address=token_address,
                symbol=str(row.get("symbol") or row.get("tokenSymbol") or ""),
                name=str(row.get("name") or row.get("tokenName") or ""),
                chain="solana",
                principal_pair="",
                source_hint="birdeye",
                validated_at=now,
            )

            out.append(
                {
                    "token_address": token_address,
                    "symbol": metadata.token_symbol,
                    "name": metadata.token_name,
                    "chain": metadata.token_chain,
                    "principal_pair": metadata.principal_pair,
                    "source": "birdeye",
                    "detected_at": now,
                    "token_age_minutes": age_minutes,
                    "liquidity_usd": liq,
                    "volume_1h_usd": volume_1h,
                    "transactions_1h": txs_1h,
                    "buys_1h": buys_1h,
                    "sells_1h": sells_1h,
                    "buys_sells_ratio": ratio,
                    "market_cap_usd": mcap,
                    "price_change_5m": price_5m,
                    "price_change_1h": price_1h,
                    "volume_acceleration": vol_acc,
                    "metadata_source": metadata.metadata_source,
                    "metadata_confidence": metadata.metadata_confidence,
                    "metadata_is_fallback": metadata.metadata_is_fallback,
                    "metadata_last_source": metadata.metadata_last_source,
                    "metadata_last_validated_at": metadata.metadata_last_validated_at,
                    "metadata_conflict": metadata.metadata_conflict,
                    "raw_json": row,
                }
            )
        return out

    def _normalize_discovery_from_dex(self, rows: list[dict]) -> list[dict]:
        now = datetime.now(UTC)
        out: list[dict] = []
        for pair in rows:
            token_address = str((pair.get("baseToken") or {}).get("address") or "").strip()
            if not token_address:
                continue
            volume_h1 = self._to_float(((pair.get("volume") or {}).get("h1")))
            volume_h24 = self._to_float(((pair.get("volume") or {}).get("h24")))
            tx_h1_data = (pair.get("txns") or {}).get("h1") or {}
            buys = self._to_int(tx_h1_data.get("buys"))
            sells = self._to_int(tx_h1_data.get("sells"))
            metadata = resolve_token_metadata(
                token_address=token_address,
                symbol=str((pair.get("baseToken") or {}).get("symbol") or ""),
                name=str((pair.get("baseToken") or {}).get("name") or ""),
                chain=str(pair.get("chainId") or "solana"),
                principal_pair=str(pair.get("pairAddress") or ""),
                source_hint="dexscreener",
                validated_at=now,
            )
            out.append(
                {
                    "token_address": token_address,
                    "symbol": metadata.token_symbol,
                    "name": metadata.token_name,
                    "chain": metadata.token_chain,
                    "principal_pair": metadata.principal_pair,
                    "source": "dex_fallback",
                    "detected_at": now,
                    "token_age_minutes": 120.0,
                    "liquidity_usd": self._to_float((pair.get("liquidity") or {}).get("usd")),
                    "volume_1h_usd": volume_h1,
                    "transactions_1h": buys + sells,
                    "buys_1h": buys,
                    "sells_1h": sells,
                    "buys_sells_ratio": buys / max(1, sells),
                    "market_cap_usd": self._to_float(pair.get("marketCap")),
                    "price_change_5m": self._to_float((pair.get("priceChange") or {}).get("m5")),
                    "price_change_1h": self._to_float((pair.get("priceChange") or {}).get("h1")),
                    "volume_acceleration": volume_h1 / max(1.0, volume_h24),
                    "metadata_source": metadata.metadata_source,
                    "metadata_confidence": metadata.metadata_confidence,
                    "metadata_is_fallback": metadata.metadata_is_fallback,
                    "metadata_last_source": metadata.metadata_last_source,
                    "metadata_last_validated_at": metadata.metadata_last_validated_at,
                    "metadata_conflict": metadata.metadata_conflict,
                    "raw_json": pair,
                }
            )
        filtered = [x for x in out if self._passes_discovery_thresholds(x)]
        dedup: dict[str, dict] = {}
        for item in filtered:
            dedup[item["token_address"]] = item
        return list(dedup.values())

    def _passes_discovery_thresholds(self, row: dict) -> bool:
        age = row.get("token_age_minutes", 999999.0)
        if age < self.settings.scanner_min_token_age_minutes:
            return False
        if age > self.settings.scanner_max_token_age_hours * 60:
            return False

        if row.get("liquidity_usd", 0.0) < self.settings.scanner_min_liquidity_usd:
            return False
        if row.get("volume_1h_usd", 0.0) < self.settings.scanner_min_volume_1h_usd:
            return False
        if row.get("transactions_1h", 0) < self.settings.scanner_min_transactions_1h:
            return False

        ratio = row.get("buys_sells_ratio", 0.0)
        if ratio < self.settings.scanner_min_buys_sells_ratio or ratio > self.settings.scanner_max_buys_sells_ratio:
            return False

        mcap = row.get("market_cap_usd", 0.0)
        if mcap > 0:
            if mcap < self.settings.scanner_min_market_cap_usd:
                return False
            if mcap > self.settings.scanner_max_market_cap_usd:
                return False

        return row.get("volume_acceleration", 0.0) >= self.settings.scanner_min_volume_acceleration

    async def _validate_candidates(self, discovered: list[dict], degraded_reasons: list[str]) -> tuple[list[dict], list[dict], str]:
        validations: list[dict] = []
        flag_rows: list[dict] = []
        source_mode = "ok"

        for row in discovered:
            token_address = row["token_address"]
            flags = {
                "paid_attention_high": False,
                "promo_flow_divergence": False,
                "liquidity_fragile": False,
                "suspicious_vertical_pump": False,
                "insufficient_pair_quality": False,
                "organic_flow_ok": True,
            }
            row_metadata_source = str(row.get("metadata_source") or row.get("source") or "unknown")
            row_metadata_confidence = str(row.get("metadata_confidence") or "unverified")
            row_metadata_is_fallback = bool(row.get("metadata_is_fallback", False))
            row_metadata_conflict = bool(row.get("metadata_conflict", False))
            pairs: list[dict] = []
            try:
                pairs = await self.dex.token_pairs(token_address)
            except Exception:
                source_mode = "degraded"
                degraded_reasons.append(f"dex token endpoint failed for {token_address[:6]}")

            if not pairs:
                flags["insufficient_pair_quality"] = True
                flags["organic_flow_ok"] = False
                metadata = resolve_token_metadata(
                    token_address=token_address,
                    symbol=str(row.get("symbol") or ""),
                    name=str(row.get("name") or ""),
                    chain=str(row.get("chain") or "solana"),
                    principal_pair=str(row.get("principal_pair") or ""),
                    source_hint=row_metadata_source,
                    validated_at=datetime.now(UTC),
                )
                validation = {
                    "token_address": token_address,
                    "source": "dexscreener",
                    "symbol": metadata.token_symbol,
                    "name": metadata.token_name,
                    "chain": metadata.token_chain,
                    "principal_pair": metadata.principal_pair,
                    "validated_at": datetime.now(UTC),
                    "primary_pair": "",
                    "chain_id": "",
                    "dex_id": "",
                    "liquidity_usd": row.get("liquidity_usd", 0.0),
                    "volume_1h_usd": row.get("volume_1h_usd", 0.0),
                    "price_change_5m": row.get("price_change_5m", 0.0),
                    "price_change_1h": row.get("price_change_1h", 0.0),
                    "boosts_active": 0.0,
                    "paid_orders": 0.0,
                    "activity_score": 0.0,
                    "organic_flow_ok": False,
                    "metadata_source": metadata.metadata_source,
                    "metadata_confidence": metadata.metadata_confidence,
                    "metadata_is_fallback": metadata.metadata_is_fallback,
                    "metadata_last_source": metadata.metadata_last_source,
                    "metadata_last_validated_at": metadata.metadata_last_validated_at,
                    "metadata_conflict": metadata.metadata_conflict or row_metadata_conflict,
                    "flags_json": flags,
                    "raw_json": {},
                }
            else:
                primary = max(pairs, key=lambda p: self._to_float((p.get("liquidity") or {}).get("usd")))
                chain_id = str(primary.get("chainId") or "")
                liq = self._to_float((primary.get("liquidity") or {}).get("usd"))
                vol_h1 = self._to_float((primary.get("volume") or {}).get("h1"))
                price_h1 = self._to_float((primary.get("priceChange") or {}).get("h1"))
                price_m5 = self._to_float((primary.get("priceChange") or {}).get("m5"))
                boosts = self._to_float((primary.get("boosts") or {}).get("active"))
                paid_orders = self._to_float((primary.get("boosts") or {}).get("total"))
                tx_h1 = (primary.get("txns") or {}).get("h1") or {}
                buys = self._to_int(tx_h1.get("buys"))
                sells = self._to_int(tx_h1.get("sells"))
                ratio = buys / max(1, sells)
                metadata = resolve_token_metadata(
                    token_address=token_address,
                    symbol=str((primary.get("baseToken") or {}).get("symbol") or row.get("symbol") or ""),
                    name=str((primary.get("baseToken") or {}).get("name") or row.get("name") or ""),
                    chain=chain_id or str(row.get("chain") or "solana"),
                    principal_pair=str(primary.get("pairAddress") or row.get("principal_pair") or ""),
                    source_hint="dexscreener",
                    comparison_symbol=str(row.get("symbol") or ""),
                    comparison_name=str(row.get("name") or ""),
                    comparison_source=row_metadata_source,
                    validated_at=datetime.now(UTC),
                )

                flags["paid_attention_high"] = boosts > self.settings.scanner_max_paid_attention_score or paid_orders > 4
                flags["promo_flow_divergence"] = flags["paid_attention_high"] and ratio < 1.0
                flags["liquidity_fragile"] = liq < self.settings.scanner_min_liquidity_usd * 1.2
                flags["suspicious_vertical_pump"] = (
                    abs(price_h1) > self.settings.scanner_max_vertical_pump_pct
                    and liq < self.settings.scanner_min_liquidity_usd * 1.6
                )
                flags["insufficient_pair_quality"] = chain_id.lower() != "solana"
                flags["organic_flow_ok"] = not (
                    flags["promo_flow_divergence"]
                    or flags["liquidity_fragile"]
                    or flags["suspicious_vertical_pump"]
                    or flags["insufficient_pair_quality"]
                )

                activity_score = min(1.0, (buys + sells) / 300)

                validation = {
                    "token_address": token_address,
                    "source": "dexscreener",
                    "symbol": metadata.token_symbol,
                    "name": metadata.token_name,
                    "chain": metadata.token_chain,
                    "principal_pair": metadata.principal_pair,
                    "validated_at": datetime.now(UTC),
                    "primary_pair": str(primary.get("pairAddress") or ""),
                    "chain_id": chain_id,
                    "dex_id": str(primary.get("dexId") or ""),
                    "liquidity_usd": liq,
                    "volume_1h_usd": vol_h1,
                    "price_change_5m": price_m5,
                    "price_change_1h": price_h1,
                    "boosts_active": boosts,
                    "paid_orders": paid_orders,
                    "activity_score": activity_score,
                    "organic_flow_ok": flags["organic_flow_ok"],
                    "metadata_source": metadata.metadata_source,
                    "metadata_confidence": metadata.metadata_confidence,
                    "metadata_is_fallback": metadata.metadata_is_fallback,
                    "metadata_last_source": metadata.metadata_last_source,
                    "metadata_last_validated_at": metadata.metadata_last_validated_at,
                    "metadata_conflict": metadata.metadata_conflict or row_metadata_conflict,
                    "flags_json": flags,
                    "raw_json": primary,
                }

            validations.append(validation)
            for flag_name, flag_value in flags.items():
                flag_rows.append(
                    {
                        "token_address": token_address,
                        "flag_name": flag_name,
                        "flag_value": bool(flag_value),
                        "details_json": {"source": "dexscreener"},
                        "created_at": datetime.now(UTC),
                    }
                )

        return validations, flag_rows, source_mode

    def _classify(
        self,
        validations: list[dict],
        market_context: dict,
        quality: dict,
        event_context: dict,
        session_id: int,
    ) -> tuple[list[ClassifiedToken], dict[str, list[dict]]]:
        quality_score = self._quality_score(quality)
        market_bias_bearish = market_context.get("btc_trend") == "bajista" and market_context.get("sol_trend") == "bajista"
        context_degraded = market_context.get("status") != "ok"

        out: list[ClassifiedToken] = []
        snapshots: dict[str, list[dict]] = {
            "whale": [],
            "social": [],
            "demand": [],
            "narrative": [],
            "breakout": [],
            "paid_attention": [],
            "event_signal": [],
            "composite": [],
            "wallet_flow": [],
            "holder_distribution": [],
            "exit_plan": [],
        }
        for val in validations:
            token = val["token_address"]
            symbol = str(val.get("symbol") or self._symbol_for_token(token))
            flags = val.get("flags_json", {})
            score = self._latest_scores(token)
            metadata_confidence = str(val.get("metadata_confidence") or "unverified").lower()
            metadata_is_fallback = bool(val.get("metadata_is_fallback", False))
            metadata_conflict = bool(val.get("metadata_conflict", False))

            metadata = TokenMetadata(
                token_symbol=str(val.get("symbol") or "TOKEN"),
                token_name=str(val.get("name") or ""),
                token_chain=str(val.get("chain") or "solana"),
                principal_pair=str(val.get("principal_pair") or ""),
                metadata_source=str(val.get("metadata_source") or "unknown"),
                metadata_confidence=metadata_confidence,
                metadata_is_fallback=metadata_is_fallback,
                metadata_last_source=str(val.get("metadata_last_source") or "unknown"),
                metadata_last_validated_at=val.get("metadata_last_validated_at"),
                metadata_conflict=metadata_conflict,
            )

            score_long = score["long_score"]
            score_short = score["short_score"]
            confidence = score["confidence"]
            risk_value = self._risk_from(score, val)
            risk_label = self._risk_label(risk_value)

            classification = classify_with_identity_gate(
                token_address=token,
                symbol=symbol,
                score_long=score_long,
                score_short=score_short,
                confidence=confidence,
                risk_value=risk_value,
                metadata=metadata,
                flags=flags,
                quality_score=quality_score,
                market_bias_bearish=market_bias_bearish,
                context_degraded=context_degraded,
                organic_flow_ok=bool(val.get("organic_flow_ok", False)),
                scanner_settings={
                    "min_score_for_long": self.settings.scanner_min_score_for_long,
                    "min_score_for_short": self.settings.scanner_min_score_for_short,
                    "min_confidence_for_long": self.settings.scanner_min_confidence_for_long,
                    "min_confidence_for_short": self.settings.scanner_min_confidence_for_short,
                    "max_risk_for_long": self.settings.scanner_max_risk_for_long,
                    "max_risk_for_short": self.settings.scanner_max_risk_for_short,
                    "min_data_quality_score": self.settings.scanner_min_data_quality_score,
                },
            )

            category = classification["category"]
            reason = classification["reason"]
            explanation = classification["explanation"]
            confidence_final = classification["confidence_final"]
            risk_adjusted = classification["risk_adjusted"]
            risk_label_adjusted = self._risk_label(risk_adjusted)

            dim_input = self._dimension_input_from_validation(val)
            event_signal = self.event_service.token_event_alignment(symbol, str(val.get("name") or ""), val, event_context)
            dimensions = compute_signal_dimensions(validation=dim_input, score_payload=score, event_signal=event_signal)
            exit_plan = self._build_exit_plan(validation=val, dimensions=dimensions)
            category, reason, explanation, confidence_final = self._apply_dimension_overrides(
                category=category,
                reason=reason,
                explanation=explanation,
                confidence_final=confidence_final,
                metadata_confidence=metadata_confidence,
                risk_adjusted=risk_adjusted,
                dimensions=dimensions,
                exit_plan=exit_plan,
                flags=flags,
                quality_score=quality_score,
            )

            snapshot_now = datetime.now(UTC)
            snapshots["whale"].append(
                {
                    "scan_session_id": session_id,
                    "token_address": token,
                    "ts": snapshot_now,
                    **dimensions.whale,
                    "payload_json": {"category": category},
                }
            )
            snapshots["social"].append(
                {
                    "scan_session_id": session_id,
                    "token_address": token,
                    "ts": snapshot_now,
                    **dimensions.social,
                    "payload_json": {"category": category},
                }
            )
            snapshots["demand"].append(
                {
                    "scan_session_id": session_id,
                    "token_address": token,
                    "ts": snapshot_now,
                    **dimensions.demand,
                    "payload_json": {"category": category},
                }
            )
            snapshots["narrative"].append(
                {
                    "scan_session_id": session_id,
                    "token_address": token,
                    "ts": snapshot_now,
                    **dimensions.narrative,
                    "payload_json": {"category": category},
                }
            )
            snapshots["breakout"].append(
                {
                    "scan_session_id": session_id,
                    "token_address": token,
                    "ts": snapshot_now,
                    **dimensions.breakout,
                    "payload_json": {"category": category},
                }
            )
            snapshots["paid_attention"].append(
                {
                    "scan_session_id": session_id,
                    "token_address": token,
                    "ts": snapshot_now,
                    **dimensions.paid_attention,
                    "payload_json": {"category": category},
                }
            )
            snapshots["event_signal"].append(
                {
                    "scan_session_id": session_id,
                    "token_address": token,
                    "ts": snapshot_now,
                    **dimensions.event_signal,
                    "payload_json": {"category": category},
                }
            )
            exit_plan = self._build_exit_plan(validation=val, dimensions=dimensions)
            snapshots["exit_plan"].append(
                {
                    "scan_session_id": session_id,
                    "token_address": token,
                    "ts": snapshot_now,
                    **exit_plan,
                    "payload_json": {"category": category},
                }
            )
            snapshots["composite"].append(
                {
                    "scan_session_id": session_id,
                    "token_address": token,
                    "ts": snapshot_now,
                    **dimensions.composite,
                    "payload_json": {"category": category},
                }
            )

            wallet_flow_score = max(
                0.0,
                min(
                    100.0,
                    0.35 * dimensions.whale.get("whale_accumulation_score", 0.0)
                    + 0.25 * dimensions.whale.get("smart_wallet_presence_score", 0.0)
                    + 0.2 * dimensions.whale.get("repeated_buyer_score", 0.0)
                    + 0.2 * dimensions.whale.get("net_whale_inflow", 0.0)
                    - 0.25 * dimensions.whale.get("insider_risk_score", 0.0),
                ),
            )
            snapshots["wallet_flow"].append(
                {
                    "scan_session_id": session_id,
                    "token_address": token,
                    "ts": snapshot_now,
                    "whale_accumulation_score": dimensions.whale.get("whale_accumulation_score", 0.0),
                    "smart_wallet_presence_score": dimensions.whale.get("smart_wallet_presence_score", 0.0),
                    "net_whale_inflow": dimensions.whale.get("net_whale_inflow", 0.0),
                    "repeated_buyer_score": dimensions.whale.get("repeated_buyer_score", 0.0),
                    "insider_risk_score": dimensions.whale.get("insider_risk_score", 0.0),
                    "dev_sell_pressure_score": dimensions.whale.get("dev_sell_pressure_score", 0.0),
                    "wallet_flow_score": wallet_flow_score,
                    "labeled_wallet_count": int(max(2, min(18, round(wallet_flow_score / 8.0)))),
                    "payload_json": {
                        "category": category,
                        "main_reason": reason,
                    },
                }
            )

            holder_concentration_score = max(
                0.0,
                min(
                    100.0,
                    100.0 - dimensions.demand.get("buyer_distribution_score", 0.0),
                ),
            )
            top10_holders_pct = max(5.0, min(95.0, 22.0 + 0.6 * holder_concentration_score))
            top25_holders_pct = max(top10_holders_pct + 3.0, min(99.0, top10_holders_pct + 16.0))
            suspicious_cluster_score = max(
                0.0,
                min(
                    100.0,
                    0.65 * dimensions.social.get("social_wallet_divergence_score", 0.0)
                    + 0.35 * dimensions.demand.get("wash_trading_suspicion_score", 0.0),
                ),
            )
            connected_clusters = int(max(1, min(9, round(suspicious_cluster_score / 18.0))))
            organic_distribution_score = max(0.0, min(100.0, 100.0 - holder_concentration_score - suspicious_cluster_score * 0.2))

            snapshots["holder_distribution"].append(
                {
                    "scan_session_id": session_id,
                    "token_address": token,
                    "ts": snapshot_now,
                    "top10_holders_pct": top10_holders_pct,
                    "top25_holders_pct": top25_holders_pct,
                    "holder_concentration_score": holder_concentration_score,
                    "suspicious_cluster_score": suspicious_cluster_score,
                    "connected_wallet_clusters": connected_clusters,
                    "organic_distribution_score": organic_distribution_score,
                    "payload_json": {
                        "category": category,
                        "cluster_preview": [
                            {
                                "cluster_id": f"C{idx + 1}",
                                "wallets": int(max(2, min(8, 2 + idx))),
                                "risk": "high" if idx == 0 and suspicious_cluster_score >= 60 else "medium",
                            }
                            for idx in range(connected_clusters)
                        ],
                    },
                }
            )

            out.append(
                ClassifiedToken(
                    token_address=token,
                    symbol=symbol,
                    category=category,
                    main_reason=reason,
                    explanation=explanation,
                    score_long=score_long,
                    score_short=score_short,
                    confidence=confidence_final,
                    risk_value=risk_adjusted,
                    risk_label=risk_label_adjusted,
                    liquidity_usd=val.get("liquidity_usd", 0.0),
                    flags={k: bool(v) for k, v in flags.items()},
                    payload={
                        "validation": val,
                        "quality_score": quality_score,
                        "market_context": {
                            "status": market_context.get("status"),
                            "btc_trend": market_context.get("btc_trend"),
                            "sol_trend": market_context.get("sol_trend"),
                        },
                        "metadata_source": val.get("metadata_source", "unknown"),
                        "metadata_confidence": metadata_confidence,
                        "metadata_is_fallback": metadata_is_fallback,
                        "metadata_last_source": val.get("metadata_last_source", "unknown"),
                        "metadata_last_validated_at": val.get("metadata_last_validated_at"),
                        "metadata_conflict": metadata_conflict,
                        "identity_quality_score": classification.get("identity_quality_score"),
                        "identity_gate_reason": classification.get("identity_gate_reason"),
                        "identity_rule_applied": classification.get("identity_rule_applied"),
                        "confidence_cap": classification.get("confidence_cap"),
                        "confidence_original": classification.get("confidence_original"),
                        "confidence_final": confidence_final,
                        "risk_original": classification.get("risk_original"),
                        "risk_adjusted": risk_adjusted,
                        "signal_dimensions": {
                            "whale": dimensions.whale,
                            "social": dimensions.social,
                            "demand": dimensions.demand,
                            "narrative": dimensions.narrative,
                            "breakout": dimensions.breakout,
                            "paid_attention": dimensions.paid_attention,
                            "event_signal": dimensions.event_signal,
                            "composite": dimensions.composite,
                        },
                        "paid_attention": dimensions.paid_attention,
                        "exit_plan": exit_plan,
                        "actionable_explanation": self._build_actionable_explanation(
                            category=category,
                            main_reason=reason,
                            explanation=explanation,
                            dimensions=dimensions,
                            exit_plan=exit_plan,
                            flags=flags,
                        ),
                    },
                )
            )

        out.sort(key=lambda x: max(x.score_long, x.score_short), reverse=True)
        return out, snapshots

    def _build_watchlist_rows(self, classified: list[ClassifiedToken], session_id: int) -> tuple[list[dict], list[dict]]:
        now = datetime.now(UTC)
        watchlist_rows: list[dict] = []
        discarded_rows: list[dict] = []

        rank = 1
        for row in classified:
            base = {
                "scan_session_id": session_id,
                "token_address": row.token_address,
                "symbol": row.symbol,
                "created_at": now,
                "metadata_source": row.payload.get("metadata_source", "unknown"),
                "metadata_confidence": row.payload.get("metadata_confidence", "unverified"),
                "metadata_is_fallback": bool(row.payload.get("metadata_is_fallback", False)),
                "metadata_last_source": row.payload.get("metadata_last_source", "unknown"),
                "metadata_last_validated_at": row.payload.get("metadata_last_validated_at"),
                "metadata_conflict": bool(row.payload.get("metadata_conflict", False)),
                    "identity_quality_score": row.payload.get("identity_quality_score", 50),
                    "identity_gate_reason": row.payload.get("identity_gate_reason", ""),
                    "identity_rule_applied": row.payload.get("identity_rule_applied", ""),
                    "identity_confidence_cap": row.payload.get("confidence_cap", 1.0),
            }
            if row.category in {"IGNORE", "NO TRADE"}:
                discarded_rows.append(
                    {
                        **base,
                        "category": row.category,
                        "discard_reason": row.main_reason,
                        "flags_json": row.flags,
                    }
                )
                continue

            watchlist_rows.append(
                {
                    **base,
                    "category": row.category,
                    "score_long": row.score_long,
                    "score_short": row.score_short,
                    "confidence": row.confidence,
                    "risk_label": row.risk_label,
                    "risk_value": row.risk_value,
                    "liquidity_usd": row.liquidity_usd,
                    "rank_order": rank,
                    "main_reason": row.main_reason,
                    "explanation": row.explanation,
                    "payload_json": row.payload,
                }
            )
            rank += 1

        return watchlist_rows, discarded_rows

    def _build_exit_plan(self, validation: dict[str, object], dimensions: object) -> dict[str, object]:
        raw = validation.get("raw_json") or {}
        price = self._to_float(raw.get("price") or raw.get("last_price") or raw.get("lastPrice") or raw.get("price_usd") or 0.0)
        if price <= 0.0:
            price = self._to_float(validation.get("market_cap") or 0.0) / max(1.0, self._to_float(validation.get("volume_24h") or 0.0))
            price = price if price > 0 else 0.0

        entry_zone = price
        invalidation_zone = price * 0.92 if price > 0 else 0.0
        tp1 = price * 1.18 if price > 0 else 0.0
        tp2 = price * 1.35 if price > 0 else 0.0
        tp3 = price * 1.65 if price > 0 else 0.0
        boost_intensity = dimensions.paid_attention.get("boost_intensity", 0.0)
        overextension = dimensions.breakout.get("overextension_penalty", 0.0)
        demand = dimensions.demand.get("transaction_demand_score", 0.0)
        paid_gap = dimensions.paid_attention.get("paid_vs_organic_gap", 0.0)

        viability = max(
            0.0,
            min(
                100.0,
                45.0
                + 0.22 * dimensions.breakout.get("breakout_setup_score", 0.0)
                + 0.18 * demand
                - 0.28 * overextension
                - 0.18 * paid_gap
                - 0.12 * (dimensions.social.get("bot_suspicion_score", 0.0) or 0.0)
                + 0.1 * max(0.0, 100.0 - boost_intensity),
            )
        )
        take_profit_plan = "20% en TP1, 30% en TP2, 50% en TP3"
        if dimensions.paid_attention.get("paid_attention_high") and demand < self.settings.scanner_min_transaction_demand:
            take_profit_plan = "Mantener sólo si se confirma flujo orgánico; ajustar sell plan según riesgo."

        return {
            "entry_zone": entry_zone,
            "invalidation_zone": invalidation_zone,
            "tp1": tp1,
            "tp2": tp2,
            "tp3": tp3,
            "partial_take_profit_plan": take_profit_plan,
            "exit_plan_viability": viability,
        }

    def _build_actionable_explanation(
        self,
        *,
        category: str,
        main_reason: str,
        explanation: str,
        dimensions: object,
        exit_plan: dict[str, object],
        flags: dict,
    ) -> str:
        paid = dimensions.paid_attention
        event_signal = getattr(dimensions, "event_signal", {})
        reasons: list[str] = [explanation]
        if paid.get("paid_attention_high"):
            reasons.append("Paid attention alta: verificar que el torque sea orgánico antes de subir categoría.")
        if paid.get("promo_flow_divergence"):
            reasons.append("Promoción pagada detectada y flujo orgánico bajo; evitar entrada agresiva.")
        if event_signal.get("event_relevance_score", 0.0) >= 40.0 and event_signal.get("catalyst_urgency_score", 0.0) >= 35.0:
            reasons.append("Sube de prioridad por catalyst cercano detectado en Polymarket.")
        if event_signal.get("macro_event_risk_score", 0.0) >= 55.0:
            reasons.append("Se penaliza por riesgo macro/event-driven desfavorable.")
        if event_signal.get("narrative_alignment_score", 0.0) >= 40.0:
            reasons.append("Hay alineación entre narrativa del token y evento relevante del mercado.")
        if exit_plan.get("exit_plan_viability", 0.0) < 40.0:
            reasons.append("Plan de salida débil: priorizar la lista en lugar de entrada inmediata.")
        if dimensions.breakout.get("overextension_penalty", 0.0) > self.settings.scanner_max_overextension_penalty:
            reasons.append("Ruptura ya extendida; esperar una nueva ventana de entrada.")
        if flags.get("liquidity_fragile"):
            reasons.append("Liquidez frágil: no operar sin mayor confirmación de book.")
        return " ".join(reasons)

    def _latest_scores(self, token_address: str) -> dict:
        rows = self.signal_repo.token_signal_history(token_address=token_address, limit=1)
        if not rows:
            return {
                "long_score": 48.0,
                "short_score": 44.0,
                "confidence": 0.56,
                "penalties": 6.0,
            }
        row = rows[0]
        penalties = self._to_float((row.reasons_json or {}).get("penalties"))
        return {
            "long_score": self._to_float(row.long_score),
            "short_score": self._to_float(row.short_score),
            "confidence": self._to_float(row.confidence),
            "penalties": penalties,
        }

    def _symbol_for_token(self, token_address: str) -> str:
        rows = self.signal_repo.token_signal_history(token_address=token_address, limit=1)
        if rows:
            return token_address[:6].upper()
        return token_address[:6].upper()

    def _risk_from(self, score: dict, validation: dict) -> float:
        risk = score.get("penalties", 6.0) * 4
        if validation.get("flags_json", {}).get("liquidity_fragile"):
            risk += 12
        if validation.get("flags_json", {}).get("promo_flow_divergence"):
            risk += 14
        if validation.get("flags_json", {}).get("suspicious_vertical_pump"):
            risk += 10
        if not validation.get("organic_flow_ok"):
            risk += 8
        return max(0.0, min(100.0, risk))

    def _risk_label(self, value: float) -> str:
        if value <= 32:
            return "bajo"
        if value <= 52:
            return "medio"
        return "alto"

    def _quality_score(self, quality: dict) -> float:
        if quality.get("status") == "ok":
            return 85.0
        reasons = quality.get("degraded_reasons") or []
        penalty = min(35.0, len(reasons) * 9.0)
        return max(45.0, 82.0 - penalty)

    def _dimension_input_from_validation(self, validation: dict) -> dict:
        raw = validation.get("raw_json") or {}
        tx_h1 = (raw.get("txns") or {}).get("h1") or {}
        tx_h24 = (raw.get("txns") or {}).get("h24") or {}
        buys_h1 = self._to_int(tx_h1.get("buys"))
        sells_h1 = self._to_int(tx_h1.get("sells"))
        buys_h24 = self._to_int(tx_h24.get("buys"))
        sells_h24 = self._to_int(tx_h24.get("sells"))

        flags_json = validation.get("flags_json") or {}
        active_flags = [k for k, v in flags_json.items() if bool(v)]

        return {
            "flags": active_flags,
            "buys_24h": buys_h24 or buys_h1 * 8,
            "sells_24h": sells_h24 or sells_h1 * 8,
            "volume_24h": self._to_float((raw.get("volume") or {}).get("h24")) or self._to_float(validation.get("volume_1h_usd")) * 6,
            "market_cap": self._to_float(raw.get("marketCap")),
            "paid_orders_24h": self._to_float(validation.get("paid_orders")),
            "activity_score": self._to_float(validation.get("activity_score")),
            "boosts_active": self._to_float(validation.get("boosts_active")),
            "price_change_1h": self._to_float(validation.get("price_change_1h")),
            "price_change_5m": self._to_float(validation.get("price_change_5m")),
            "status": "ok",
        }

    def _apply_dimension_overrides(
        self,
        *,
        category: str,
        reason: str,
        explanation: str,
        confidence_final: float,
        metadata_confidence: str,
        risk_adjusted: float,
        dimensions: object,
        exit_plan: dict[str, float | str] | None,
        flags: dict,
        quality_score: float,
    ) -> tuple[str, str, str, float]:
        composite = dimensions.composite
        demand = dimensions.demand
        social = dimensions.social
        narrative = dimensions.narrative
        breakout = dimensions.breakout
        paid_attention = dimensions.paid_attention
        event_signal = getattr(dimensions, "event_signal", {})

        min_demand = self.settings.scanner_min_transaction_demand
        max_overext = self.settings.scanner_max_overextension_penalty
        max_bot = self.settings.scanner_max_bot_suspicion
        max_paid_gap = self.settings.scanner_max_paid_vs_organic_gap
        min_whale_for_priority = self.settings.scanner_min_whale_score_for_priority
        min_breakout_setup = self.settings.scanner_min_breakout_setup_score
        min_speculative_boost = self.settings.scanner_min_speculative_momentum_for_boost
        exit_viability = (exit_plan or {}).get("exit_plan_viability", 0.0)

        if paid_attention.get("paid_attention_high") and paid_attention.get("paid_vs_organic_gap", 0.0) > max_paid_gap:
            category = "NO TRADE"
            reason = "Paid attention riesgosa"
            explanation = (
                "NO TRADE por paid attention alta sin demanda orgánica compatible y brecha paid-vs-organic elevada."
            )
            confidence_final = min(confidence_final, 0.40)
            return category, reason, explanation, confidence_final

        if category == "LONG ahora":
            if (
                demand.get("transaction_demand_score", 0.0) < min_demand
                or breakout.get("overextension_penalty", 0.0) > max_overext
                or social.get("bot_suspicion_score", 0.0) > max_bot
                or narrative.get("paid_vs_organic_narrative_gap", 0.0) > max_paid_gap
            ):
                category = "WATCHLIST prioritaria"
                reason = "Confirmacion de flujo/timing insuficiente"
                explanation = (
                    "Se degrada LONG a WATCHLIST prioritaria porque las dimensiones nuevas detectan "
                    "demanda/timing/social no suficientemente sanos para entrada inmediata."
                )
                confidence_final = min(confidence_final, 0.74)

        if category == "WATCHLIST secundaria":
            if (
                composite.get("speculative_momentum_score", 0.0) >= min_speculative_boost
                and demand.get("transaction_demand_score", 0.0) >= min_demand
                and breakout.get("breakout_setup_score", 0.0) >= min_breakout_setup
                and composite.get("whale_accumulation_score", 0.0) >= min_whale_for_priority
                and social.get("bot_suspicion_score", 0.0) <= max_bot
                and risk_adjusted <= self.settings.scanner_max_risk_for_long + 6
                and quality_score >= self.settings.scanner_min_data_quality_score
                and metadata_confidence in {"confirmed", "inferred"}
                and not flags.get("liquidity_fragile")
            ):
                category = "WATCHLIST prioritaria"
                reason = "Momentum especulativo confirmado"
                explanation = (
                    "Sube a WATCHLIST prioritaria por combinacion favorable de demanda real, "
                    "ballenas, timing de breakout y momentum social organico."
                )
                confidence_final = min(0.82, confidence_final + 0.03)

        if category == "WATCHLIST secundaria":
            if (
                event_signal.get("event_relevance_score", 0.0) >= 40.0
                and event_signal.get("catalyst_urgency_score", 0.0) >= 35.0
                and event_signal.get("event_sentiment_score", 0.0) >= 45.0
                and event_signal.get("narrative_alignment_score", 0.0) >= 35.0
                and risk_adjusted <= self.settings.scanner_max_risk_for_long + 8
            ):
                category = "WATCHLIST prioritaria"
                reason = "Catalyst relevante en Polymarket"
                explanation = (
                    "Sube de prioridad por catalyst cercano detectado en Polymarket y alineacion narrativa."
                )
                confidence_final = min(0.80, confidence_final + 0.04)

        if category in {"WATCHLIST prioritaria", "WATCHLIST secundaria"}:
            if (
                demand.get("wash_trading_suspicion_score", 0.0) >= 65.0
                and social.get("social_wallet_divergence_score", 0.0) >= 35.0
            ):
                category = "NO TRADE"
                reason = "Hype social sin confirmacion on-chain"
                explanation = (
                    "NO TRADE por divergencia entre social y flujo on-chain con sospecha de wash trading."
                )
                confidence_final = min(confidence_final, 0.45)

        if event_signal.get("macro_event_risk_score", 0.0) >= 60.0:
            if category == "LONG ahora":
                category = "WATCHLIST prioritaria"
                reason = "Riesgo macro/event-driven"
                explanation = (
                    "Se degrada LONG por riesgo macro/event-driven adverso detectado en Polymarket."
                )
                confidence_final = min(confidence_final, 0.72)
            elif category == "WATCHLIST prioritaria":
                category = "WATCHLIST secundaria"
                reason = "Catalyst macro adverso"
                explanation = (
                    "Se reduce prioridad por riesgo macro/event-driven desfavorable de Polymarket."
                )
                confidence_final = min(confidence_final, 0.64)

        if category in {"WATCHLIST prioritaria", "WATCHLIST secundaria", "LONG ahora"}:
            if (
                narrative.get("paid_vs_organic_narrative_gap", 0.0) > max_paid_gap
                and social.get("bot_suspicion_score", 0.0) > (max_bot - 8)
            ):
                category = "NO TRADE"
                reason = "Paid attention dominante"
                explanation = (
                    "NO TRADE por brecha alta paid-vs-organic y sospecha social elevada sin validacion suficiente de traccion real."
                )
                confidence_final = min(confidence_final, 0.4)

            elif breakout.get("overextension_penalty", 0.0) > max_overext:
                category = "WATCHLIST secundaria"
                reason = "Setup sobreextendido"
                explanation = (
                    "Se reduce prioridad por ruptura tardia/sobreextendida; se espera mejor ventana de entrada."
                )
                confidence_final = min(confidence_final, 0.58)

        if exit_viability < 38.0 and category in {"LONG ahora", "WATCHLIST prioritaria"}:
            category = "WATCHLIST secundaria"
            reason = "Salida no viable"
            explanation = (
                "El plan de salida es demasiado débil para apoyar un LONG o una watchlist prioritaria."
            )
            confidence_final = min(confidence_final, 0.6)

        if exit_viability < 20.0 and category == "LONG ahora":
            category = "NO TRADE"
            reason = "Plan de salida no sostenible"
            explanation = (
                "NO TRADE porque la viabilidad del plan de salida es demasiado baja para una entrada sana."
            )
            confidence_final = min(confidence_final, 0.38)

        return category, reason, explanation, confidence_final

    @staticmethod
    def _to_float(value: object) -> float:
        try:
            return float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _to_int(value: object) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _to_datetime(value: object) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=UTC)
        if isinstance(value, (int, float)):
            ts = float(value)
            if ts > 1_000_000_000_000:
                ts = ts / 1000.0
            return datetime.fromtimestamp(ts, tz=UTC)
        if isinstance(value, str):
            parsed = value.strip()
            if not parsed:
                return None
            try:
                return datetime.fromisoformat(parsed.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None


scanner_service = PlaybookScannerService()


def _blocker_bucket(reason: str) -> str:
    text = str(reason or "").lower()
    if any(key in text for key in ("ident", "fallback", "unverified", "metadata", "conflict")):
        return "identity"
    if any(key in text for key in ("liquidez", "liquidity", "slippage", "volume")):
        return "liquidity"
    if any(key in text for key in ("quality", "degrad", "coverage", "frescura")):
        return "data_quality"
    if any(key in text for key in ("riesgo", "risk", "honeypot", "flag", "veto")):
        return "risk"
    return "other"


def _dominant_blocker(counts: dict[str, int]) -> str:
    ordered = [
        ("identity", "Identidad"),
        ("risk", "Riesgo"),
        ("liquidity", "Liquidez"),
        ("data_quality", "Data quality"),
        ("other", "Otros"),
    ]
    winner = max(ordered, key=lambda item: counts.get(item[0], 0))
    return winner[1] if counts.get(winner[0], 0) > 0 else "Sin bloqueo dominante"


def _session_freshness(session) -> dict:
    if session is None:
        return {"freshness": "none", "minutes_ago": None}
    if session.finished_at is None:
        return {"freshness": "running", "minutes_ago": 0.0}
    now = datetime.now(UTC)
    finished_at = session.finished_at
    if finished_at.tzinfo is None:
        finished_at = finished_at.replace(tzinfo=UTC)
    minutes = max(0.0, (now - finished_at).total_seconds() / 60.0)
    if minutes <= 60:
        label = "fresco"
    elif minutes <= 180:
        label = "degradado"
    else:
        label = "vencido"
    return {"freshness": label, "minutes_ago": round(minutes, 1)}


def _select_session_session(current, latest_valid):
    if current and current.status == "completed" and not current.degraded and current.watchlist_count > 0:
        return current, "current"
    if latest_valid is not None:
        return latest_valid, "latest_valid"
    if current is not None:
        return current, "current"
    return None, "none"


def _session_payload(session, scope: str) -> dict | None:
    if session is None:
        return None
    freshness = _session_freshness(session)
    return {
        "scan_session_id": session.id,
        "source": scope,
        "status": session.status,
        "degraded": session.degraded,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "finished_at": session.finished_at.isoformat() if session.finished_at else None,
        "watchlist_count": session.watchlist_count,
        "discarded_count": session.discarded_count,
        "freshness": freshness["freshness"],
        "minutes_ago": freshness["minutes_ago"],
        "sources": session.source_summary_json,
        "notes": session.notes_json,
    }


def watchlist_today_payload(q: str | None = None, identity: str | None = None) -> dict:
    settings = get_settings()
    repo = scanner_service.repo
    today = date.today()
    today_rows = repo.watchlist_for_day(today)
    rows = list(today_rows)

    source = "today" if rows else "none"
    current_session = repo.session_by_id(rows[0].scan_session_id) if rows else None
    latest_valid = repo.latest_valid_session()
    latest_valid_payload = None
    if latest_valid is not None and (current_session is None or latest_valid.id != current_session.id):
        latest_valid_payload = _session_payload(latest_valid, "latest_valid")

    normalized_q = (q or "").strip().lower()
    normalized_identity = (identity or "").strip().lower()
    if normalized_q:
        rows = [
            x
            for x in rows
            if normalized_q in (x.token_address or "").lower()
            or normalized_q in (x.symbol or "").lower()
            or normalized_q in ((x.payload_json or {}).get("validation", {}).get("name") or "").lower()
        ]
    if normalized_identity:
        rows = [x for x in rows if (x.metadata_confidence or "").lower() == normalized_identity]

    strong = [x for x in rows if x.category == "LONG ahora"][: settings.scanner_watchlist_strong_limit]
    priority = [x for x in rows if x.category == "WATCHLIST prioritaria"][: settings.scanner_watchlist_observe_limit]
    secondary = [x for x in rows if x.category == "WATCHLIST secundaria"][: settings.scanner_watchlist_observe_limit]
    shorts = [x for x in rows if x.category == "SHORT solo paper"][: settings.scanner_watchlist_short_limit]

    blocked_counts = {"identity": 0, "risk": 0, "liquidity": 0, "data_quality": 0, "other": 0}
    discarded_rows = scanner_service.repo.discarded_for_day(today)
    for entry in discarded_rows:
        blocked_counts[_blocker_bucket(entry.discard_reason)] += 1

    latest_nonempty = repo.latest_session_with_watchlist()
    latest_nonempty_payload = None
    if latest_nonempty is not None:
        latest_nonempty_payload = {
            "scan_session_id": latest_nonempty.id,
            "finished_at": latest_nonempty.finished_at.isoformat() if latest_nonempty.finished_at else None,
            "watchlist_count": latest_nonempty.watchlist_count,
            "discarded_count": latest_nonempty.discarded_count,
        }

    empty_explanation = None
    if len(rows) == 0:
        empty_explanation = (
            "No hubo candidatas operables en la sesión actual; "
            f"bloqueadas por identidad {blocked_counts['identity']}, "
            f"riesgo {blocked_counts['risk']}, "
            f"liquidez {blocked_counts['liquidity']} y "
            f"data quality {blocked_counts['data_quality']}."
        )

    return {
        "date": today.isoformat(),
        "source": source,
        "is_live": bool(rows),
        "current_session": _session_payload(current_session, "today") if current_session is not None else None,
        "latest_valid_session": latest_valid_payload,
        "strong": [_watch_row(x, source_type="live") for x in strong],
        "priority": [_watch_row(x, source_type="live") for x in priority],
        "secondary": [_watch_row(x, source_type="live") for x in secondary],
        "short_paper": [_watch_row(x, source_type="live") for x in shorts],
        "today_total": len(today_rows),
        "total": len(rows),
        "blocked_breakdown": blocked_counts,
        "dominant_blocker": _dominant_blocker(blocked_counts),
        "excluded_total": len(discarded_rows),
        "latest_nonempty_watchlist": latest_nonempty_payload,
        "empty_explanation": empty_explanation,
        "latest_valid_available": bool(latest_valid_payload),
    }


def discarded_today_payload() -> dict:
    rows = scanner_service.repo.discarded_for_day(date.today())
    source = "today"

    payload = [
        {
            "token_address": x.token_address,
            "symbol": x.symbol,
            "category": x.category,
            "operability_status": "bloqueado" if x.category != "NO TRADE" else "no_trade",
            "discard_reason": x.discard_reason,
            "metadata_source": x.metadata_source,
            "metadata_confidence": x.metadata_confidence,
            "metadata_is_fallback": x.metadata_is_fallback,
            "metadata_last_source": x.metadata_last_source,
            "metadata_last_validated_at": x.metadata_last_validated_at.isoformat() if x.metadata_last_validated_at else None,
            "metadata_conflict": x.metadata_conflict,
            "flags": x.flags_json,
            "ts": x.created_at.isoformat(),
            "scan_session_id": x.scan_session_id,
        }
        for x in rows
    ]
    return {"date": date.today().isoformat(), "source": source, "total": len(payload), "rows": payload}


def _operability_from_category(category: str) -> tuple[str, str]:
    normalized = str(category or "").strip().lower()
    if normalized == "long ahora":
        return "operable", "Cumple reglas de operabilidad para LONG"
    if normalized in {"watchlist prioritaria", "watchlist secundaria", "short solo paper"}:
        return "watchlist", "Se mantiene en seguimiento operativo"
    if normalized in {"ignore", "no trade"}:
        return "no_trade", "No cumple mínimos de tradeabilidad"
    return "bloqueado", "Bloqueado por reglas de seguridad/calidad"


def _watch_row(row: object, source_type: str = "live") -> dict:
    payload = row.payload_json or {}
    dimensions = (payload.get("signal_dimensions") or {})
    composite = dimensions.get("composite") or {}
    operability_status, operability_reason = _operability_from_category(row.category)
    data_origin = source_type
    if row.metadata_is_fallback or (row.metadata_confidence or "").lower() in {"fallback", "unverified"}:
        data_origin = "fallback"
    return {
        "token_address": row.token_address,
        "symbol": row.symbol,
        "category": row.category,
        "operability_status": operability_status,
        "operability_reason": operability_reason,
        "operability_blocker": row.main_reason if operability_status in {"watchlist", "bloqueado", "no_trade"} else None,
        "score_long": row.score_long,
        "score_short": row.score_short,
        "confidence": row.confidence,
        "risk_label": row.risk_label,
        "risk_value": row.risk_value,
        "liquidity_usd": row.liquidity_usd,
        "metadata_source": row.metadata_source,
        "metadata_confidence": row.metadata_confidence,
        "metadata_is_fallback": row.metadata_is_fallback,
        "metadata_last_source": row.metadata_last_source,
        "metadata_last_validated_at": row.metadata_last_validated_at.isoformat() if row.metadata_last_validated_at else None,
        "metadata_conflict": row.metadata_conflict,
        "rank": row.rank_order,
        "main_reason": row.main_reason,
        "explanation": row.explanation,
        "signal_dimensions": dimensions,
        "paid_attention": payload.get("paid_attention", {}),
        "exit_plan": payload.get("exit_plan", {}),
        "actionable_explanation": payload.get("actionable_explanation", ""),
        "whale_accumulation_score": composite.get("whale_accumulation_score", 0.0),
        "social_momentum_score": composite.get("social_momentum_score", 0.0),
        "demand_quality_score": composite.get("demand_quality_score", 0.0),
        "narrative_strength_score": composite.get("narrative_strength_score", 0.0),
        "breakout_timing_score": composite.get("breakout_timing_score", 0.0),
        "speculative_momentum_score": composite.get("speculative_momentum_score", 0.0),
        "ts": row.created_at.isoformat(),
        "scan_session_id": row.scan_session_id,
        "source_type": source_type,
        "data_origin": data_origin,
    }
