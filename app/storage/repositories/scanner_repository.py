from __future__ import annotations

from datetime import UTC, date, datetime, time

from sqlalchemy import desc, select

from app.storage.db import (
    BreakoutSignalSnapshot,
    DexScreenerValidation,
    DemandSignalSnapshot,
    DiscardedEntry,
    DiscoveryCandidate,
    ExitPlanSnapshot,
    HolderDistributionSnapshot,
    NarrativeSignalSnapshot,
    PaidAttentionSnapshot,
    ScanSession,
    ScannerFlag,
    SignalCompositeSnapshot,
    SocialSignalSnapshot,
    WalletFlowSnapshot,
    WhaleSignalSnapshot,
    WatchlistEntry,
    get_session,
)


class ScannerRepository:
    def create_session(self, config_json: dict, source_summary_json: dict) -> int:
        with get_session() as session:
            row = ScanSession(
                started_at=datetime.now(UTC),
                status="running",
                degraded=False,
                config_json=config_json,
                source_summary_json=source_summary_json,
                notes_json={},
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return row.id

    def complete_session(
        self,
        session_id: int,
        *,
        status: str,
        degraded: bool,
        discovered_count: int,
        validated_count: int,
        classified_count: int,
        watchlist_count: int,
        discarded_count: int,
        source_summary_json: dict,
        notes_json: dict,
    ) -> None:
        with get_session() as session:
            row = session.get(ScanSession, session_id)
            if row is None:
                return
            row.finished_at = datetime.now(UTC)
            row.status = status
            row.degraded = degraded
            row.discovered_count = discovered_count
            row.validated_count = validated_count
            row.classified_count = classified_count
            row.watchlist_count = watchlist_count
            row.discarded_count = discarded_count
            row.source_summary_json = source_summary_json
            row.notes_json = notes_json
            session.commit()

    def latest_session(self) -> ScanSession | None:
        with get_session() as session:
            stmt = select(ScanSession).order_by(desc(ScanSession.id)).limit(1)
            return session.scalars(stmt).first()

    def latest_session_with_watchlist(self) -> ScanSession | None:
        with get_session() as session:
            stmt = (
                select(ScanSession)
                .where(ScanSession.watchlist_count > 0)
                .order_by(desc(ScanSession.id))
                .limit(1)
            )
            return session.scalars(stmt).first()

    def session_by_id(self, session_id: int) -> ScanSession | None:
        with get_session() as session:
            return session.get(ScanSession, session_id)

    def add_discovery_candidates(self, rows: list[dict]) -> None:
        if not rows:
            return
        with get_session() as session:
            for item in rows:
                session.add(
                    DiscoveryCandidate(
                        scan_session_id=item["scan_session_id"],
                        token_address=item["token_address"],
                        symbol=item.get("symbol", "UNK"),
                        source=item.get("source", "birdeye"),
                        detected_at=item.get("detected_at", datetime.now(UTC)),
                        token_age_minutes=item.get("token_age_minutes", 0.0),
                        liquidity_usd=item.get("liquidity_usd", 0.0),
                        volume_1h_usd=item.get("volume_1h_usd", 0.0),
                        transactions_1h=item.get("transactions_1h", 0),
                        buys_1h=item.get("buys_1h", 0),
                        sells_1h=item.get("sells_1h", 0),
                        buys_sells_ratio=item.get("buys_sells_ratio", 0.0),
                        market_cap_usd=item.get("market_cap_usd", 0.0),
                        price_change_5m=item.get("price_change_5m", 0.0),
                        price_change_1h=item.get("price_change_1h", 0.0),
                        volume_acceleration=item.get("volume_acceleration", 0.0),
                        metadata_source=item.get("metadata_source", "unknown"),
                        metadata_confidence=item.get("metadata_confidence", "unverified"),
                        metadata_is_fallback=item.get("metadata_is_fallback", False),
                        metadata_last_source=item.get("metadata_last_source", "unknown"),
                        metadata_last_validated_at=item.get("metadata_last_validated_at"),
                        metadata_conflict=item.get("metadata_conflict", False),
                        raw_json=item.get("raw_json", {}),
                    )
                )
            session.commit()

    def add_dex_validations(self, rows: list[dict]) -> None:
        if not rows:
            return
        with get_session() as session:
            for item in rows:
                session.add(
                    DexScreenerValidation(
                        scan_session_id=item["scan_session_id"],
                        token_address=item["token_address"],
                        source=item.get("source", "dexscreener"),
                        validated_at=item.get("validated_at", datetime.now(UTC)),
                        primary_pair=item.get("primary_pair", ""),
                        chain_id=item.get("chain_id", ""),
                        dex_id=item.get("dex_id", ""),
                        liquidity_usd=item.get("liquidity_usd", 0.0),
                        volume_1h_usd=item.get("volume_1h_usd", 0.0),
                        price_change_5m=item.get("price_change_5m", 0.0),
                        price_change_1h=item.get("price_change_1h", 0.0),
                        boosts_active=item.get("boosts_active", 0.0),
                        paid_orders=item.get("paid_orders", 0.0),
                        activity_score=item.get("activity_score", 0.0),
                        organic_flow_ok=item.get("organic_flow_ok", False),
                        metadata_source=item.get("metadata_source", "unknown"),
                        metadata_confidence=item.get("metadata_confidence", "unverified"),
                        metadata_is_fallback=item.get("metadata_is_fallback", False),
                        metadata_last_source=item.get("metadata_last_source", "unknown"),
                        metadata_last_validated_at=item.get("metadata_last_validated_at"),
                        metadata_conflict=item.get("metadata_conflict", False),
                        flags_json=item.get("flags_json", {}),
                        raw_json=item.get("raw_json", {}),
                    )
                )
            session.commit()

    def add_flags(self, rows: list[dict]) -> None:
        if not rows:
            return
        with get_session() as session:
            for item in rows:
                session.add(
                    ScannerFlag(
                        scan_session_id=item["scan_session_id"],
                        token_address=item["token_address"],
                        flag_name=item["flag_name"],
                        flag_value=item.get("flag_value", False),
                        details_json=item.get("details_json", {}),
                        created_at=item.get("created_at", datetime.now(UTC)),
                    )
                )
            session.commit()

    def add_watchlist_entries(self, rows: list[dict]) -> None:
        if not rows:
            return
        with get_session() as session:
            for item in rows:
                session.add(
                    WatchlistEntry(
                        scan_session_id=item["scan_session_id"],
                        token_address=item["token_address"],
                        symbol=item.get("symbol", "UNK"),
                        category=item["category"],
                        score_long=item.get("score_long", 0.0),
                        score_short=item.get("score_short", 0.0),
                        confidence=item.get("confidence", 0.0),
                        risk_label=item.get("risk_label", "medio"),
                        risk_value=item.get("risk_value", 0.0),
                        liquidity_usd=item.get("liquidity_usd", 0.0),
                        rank_order=item.get("rank_order", 0),
                        main_reason=item.get("main_reason", ""),
                        explanation=item.get("explanation", ""),
                        metadata_source=item.get("metadata_source", "unknown"),
                        metadata_confidence=item.get("metadata_confidence", "unverified"),
                        metadata_is_fallback=item.get("metadata_is_fallback", False),
                        metadata_last_source=item.get("metadata_last_source", "unknown"),
                        metadata_last_validated_at=item.get("metadata_last_validated_at"),
                        metadata_conflict=item.get("metadata_conflict", False),
                        payload_json=item.get("payload_json", {}),
                        created_at=item.get("created_at", datetime.now(UTC)),
                    )
                )
            session.commit()

    def add_discarded_entries(self, rows: list[dict]) -> None:
        if not rows:
            return
        with get_session() as session:
            for item in rows:
                session.add(
                    DiscardedEntry(
                        scan_session_id=item["scan_session_id"],
                        token_address=item["token_address"],
                        symbol=item.get("symbol", "UNK"),
                        category=item.get("category", "NO TRADE"),
                        discard_reason=item.get("discard_reason", ""),
                        metadata_source=item.get("metadata_source", "unknown"),
                        metadata_confidence=item.get("metadata_confidence", "unverified"),
                        metadata_is_fallback=item.get("metadata_is_fallback", False),
                        metadata_last_source=item.get("metadata_last_source", "unknown"),
                        metadata_last_validated_at=item.get("metadata_last_validated_at"),
                        metadata_conflict=item.get("metadata_conflict", False),
                        flags_json=item.get("flags_json", {}),
                        created_at=item.get("created_at", datetime.now(UTC)),
                    )
                )
            session.commit()

    def add_signal_dimension_snapshots(
        self,
        whale_rows: list[dict],
        social_rows: list[dict],
        demand_rows: list[dict],
        narrative_rows: list[dict],
        breakout_rows: list[dict],
        paid_attention_rows: list[dict],
        composite_rows: list[dict],
        exit_plan_rows: list[dict],
    ) -> None:
        with get_session() as session:
            for item in whale_rows:
                session.add(
                    WhaleSignalSnapshot(
                        scan_session_id=item["scan_session_id"],
                        token_address=item["token_address"],
                        ts=item.get("ts", datetime.now(UTC)),
                        whale_accumulation_score=item.get("whale_accumulation_score", 0.0),
                        smart_wallet_presence_score=item.get("smart_wallet_presence_score", 0.0),
                        net_whale_inflow=item.get("net_whale_inflow", 0.0),
                        repeated_buyer_score=item.get("repeated_buyer_score", 0.0),
                        insider_risk_score=item.get("insider_risk_score", 0.0),
                        dev_sell_pressure_score=item.get("dev_sell_pressure_score", 0.0),
                        payload_json=item.get("payload_json", {}),
                    )
                )

            for item in social_rows:
                session.add(
                    SocialSignalSnapshot(
                        scan_session_id=item["scan_session_id"],
                        token_address=item["token_address"],
                        ts=item.get("ts", datetime.now(UTC)),
                        social_velocity_score=item.get("social_velocity_score", 0.0),
                        community_growth_score=item.get("community_growth_score", 0.0),
                        organic_engagement_score=item.get("organic_engagement_score", 0.0),
                        bot_suspicion_score=item.get("bot_suspicion_score", 0.0),
                        narrative_repetition_score=item.get("narrative_repetition_score", 0.0),
                        social_wallet_divergence_score=item.get("social_wallet_divergence_score", 0.0),
                        payload_json=item.get("payload_json", {}),
                    )
                )

            for item in demand_rows:
                session.add(
                    DemandSignalSnapshot(
                        scan_session_id=item["scan_session_id"],
                        token_address=item["token_address"],
                        ts=item.get("ts", datetime.now(UTC)),
                        transaction_demand_score=item.get("transaction_demand_score", 0.0),
                        tx_count_acceleration=item.get("tx_count_acceleration", 0.0),
                        organic_volume_score=item.get("organic_volume_score", 0.0),
                        wash_trading_suspicion_score=item.get("wash_trading_suspicion_score", 0.0),
                        buyer_distribution_score=item.get("buyer_distribution_score", 0.0),
                        trade_continuity_score=item.get("trade_continuity_score", 0.0),
                        payload_json=item.get("payload_json", {}),
                    )
                )

            for item in narrative_rows:
                session.add(
                    NarrativeSignalSnapshot(
                        scan_session_id=item["scan_session_id"],
                        token_address=item["token_address"],
                        ts=item.get("ts", datetime.now(UTC)),
                        narrative_strength_score=item.get("narrative_strength_score", 0.0),
                        meme_clarity_score=item.get("meme_clarity_score", 0.0),
                        viral_repeatability_score=item.get("viral_repeatability_score", 0.0),
                        cross_source_narrative_score=item.get("cross_source_narrative_score", 0.0),
                        paid_vs_organic_narrative_gap=item.get("paid_vs_organic_narrative_gap", 0.0),
                        cult_signal_score=item.get("cult_signal_score", 0.0),
                        payload_json=item.get("payload_json", {}),
                    )
                )

            for item in breakout_rows:
                session.add(
                    BreakoutSignalSnapshot(
                        scan_session_id=item["scan_session_id"],
                        token_address=item["token_address"],
                        ts=item.get("ts", datetime.now(UTC)),
                        breakout_setup_score=item.get("breakout_setup_score", 0.0),
                        consolidation_quality_score=item.get("consolidation_quality_score", 0.0),
                        breakout_confirmation_score=item.get("breakout_confirmation_score", 0.0),
                        overextension_penalty=item.get("overextension_penalty", 0.0),
                        entry_timing_score=item.get("entry_timing_score", 0.0),
                        invalidation_quality_score=item.get("invalidation_quality_score", 0.0),
                        payload_json=item.get("payload_json", {}),
                    )
                )

            for item in paid_attention_rows:
                session.add(
                    PaidAttentionSnapshot(
                        scan_session_id=item["scan_session_id"],
                        token_address=item["token_address"],
                        ts=item.get("ts", datetime.now(UTC)),
                        boost_intensity=item.get("boost_intensity", 0.0),
                        paid_attention_high=bool(item.get("paid_attention_high", False)),
                        promo_flow_divergence=bool(item.get("promo_flow_divergence", False)),
                        paid_vs_organic_gap=item.get("paid_vs_organic_gap", 0.0),
                        payload_json=item.get("payload_json", {}),
                    )
                )

            for item in exit_plan_rows:
                session.add(
                    ExitPlanSnapshot(
                        scan_session_id=item["scan_session_id"],
                        token_address=item["token_address"],
                        ts=item.get("ts", datetime.now(UTC)),
                        entry_zone=item.get("entry_zone", 0.0),
                        invalidation_zone=item.get("invalidation_zone", 0.0),
                        tp1=item.get("tp1", 0.0),
                        tp2=item.get("tp2", 0.0),
                        tp3=item.get("tp3", 0.0),
                        partial_take_profit_plan=item.get("partial_take_profit_plan", ""),
                        exit_plan_viability=item.get("exit_plan_viability", 0.0),
                        payload_json=item.get("payload_json", {}),
                    )
                )

            for item in composite_rows:
                session.add(
                    SignalCompositeSnapshot(
                        scan_session_id=item["scan_session_id"],
                        token_address=item["token_address"],
                        ts=item.get("ts", datetime.now(UTC)),
                        whale_accumulation_score=item.get("whale_accumulation_score", 0.0),
                        social_momentum_score=item.get("social_momentum_score", 0.0),
                        demand_quality_score=item.get("demand_quality_score", 0.0),
                        narrative_strength_score=item.get("narrative_strength_score", 0.0),
                        breakout_timing_score=item.get("breakout_timing_score", 0.0),
                        speculative_momentum_score=item.get("speculative_momentum_score", 0.0),
                        gate_notes=item.get("gate_notes", ""),
                        payload_json=item.get("payload_json", {}),
                    )
                )
            session.commit()

    def add_paid_attention_snapshots(self, rows: list[dict]) -> None:
        if not rows:
            return
        with get_session() as session:
            for item in rows:
                session.add(
                    PaidAttentionSnapshot(
                        scan_session_id=item["scan_session_id"],
                        token_address=item["token_address"],
                        ts=item.get("ts", datetime.now(UTC)),
                        boost_intensity=item.get("boost_intensity", 0.0),
                        paid_attention_high=bool(item.get("paid_attention_high", False)),
                        promo_flow_divergence=bool(item.get("promo_flow_divergence", False)),
                        paid_vs_organic_gap=item.get("paid_vs_organic_gap", 0.0),
                        payload_json=item.get("payload_json", {}),
                    )
                )
            session.commit()

    def add_exit_plan_snapshots(self, rows: list[dict]) -> None:
        if not rows:
            return
        with get_session() as session:
            for item in rows:
                session.add(
                    ExitPlanSnapshot(
                        scan_session_id=item["scan_session_id"],
                        token_address=item["token_address"],
                        ts=item.get("ts", datetime.now(UTC)),
                        entry_zone=item.get("entry_zone", 0.0),
                        invalidation_zone=item.get("invalidation_zone", 0.0),
                        tp1=item.get("tp1", 0.0),
                        tp2=item.get("tp2", 0.0),
                        tp3=item.get("tp3", 0.0),
                        partial_take_profit_plan=item.get("partial_take_profit_plan", ""),
                        exit_plan_viability=item.get("exit_plan_viability", 0.0),
                        payload_json=item.get("payload_json", {}),
                    )
                )
            session.commit()

    def add_wallet_intelligence_snapshots(
        self,
        wallet_flow_rows: list[dict],
        holder_distribution_rows: list[dict],
    ) -> None:
        if not wallet_flow_rows and not holder_distribution_rows:
            return

        with get_session() as session:
            for item in wallet_flow_rows:
                session.add(
                    WalletFlowSnapshot(
                        scan_session_id=item["scan_session_id"],
                        token_address=item["token_address"],
                        ts=item.get("ts", datetime.now(UTC)),
                        whale_accumulation_score=item.get("whale_accumulation_score", 0.0),
                        smart_wallet_presence_score=item.get("smart_wallet_presence_score", 0.0),
                        net_whale_inflow=item.get("net_whale_inflow", 0.0),
                        repeated_buyer_score=item.get("repeated_buyer_score", 0.0),
                        insider_risk_score=item.get("insider_risk_score", 0.0),
                        dev_sell_pressure_score=item.get("dev_sell_pressure_score", 0.0),
                        wallet_flow_score=item.get("wallet_flow_score", 0.0),
                        labeled_wallet_count=item.get("labeled_wallet_count", 0),
                        payload_json=item.get("payload_json", {}),
                    )
                )

            for item in holder_distribution_rows:
                session.add(
                    HolderDistributionSnapshot(
                        scan_session_id=item["scan_session_id"],
                        token_address=item["token_address"],
                        ts=item.get("ts", datetime.now(UTC)),
                        top10_holders_pct=item.get("top10_holders_pct", 0.0),
                        top25_holders_pct=item.get("top25_holders_pct", 0.0),
                        holder_concentration_score=item.get("holder_concentration_score", 0.0),
                        suspicious_cluster_score=item.get("suspicious_cluster_score", 0.0),
                        connected_wallet_clusters=item.get("connected_wallet_clusters", 0),
                        organic_distribution_score=item.get("organic_distribution_score", 0.0),
                        payload_json=item.get("payload_json", {}),
                    )
                )
            session.commit()

    def watchlist_for_day(self, for_day: date) -> list[WatchlistEntry]:
        start = datetime.combine(for_day, time.min, tzinfo=UTC)
        end = datetime.combine(for_day, time.max, tzinfo=UTC)
        with get_session() as session:
            stmt = (
                select(WatchlistEntry)
                .where(WatchlistEntry.created_at >= start, WatchlistEntry.created_at <= end)
                .order_by(desc(WatchlistEntry.id))
            )
            return list(session.scalars(stmt).all())

    def watchlist_for_session(self, session_id: int) -> list[WatchlistEntry]:
        with get_session() as session:
            stmt = (
                select(WatchlistEntry)
                .where(WatchlistEntry.scan_session_id == session_id)
                .order_by(desc(WatchlistEntry.rank_order), desc(WatchlistEntry.id))
            )
            return list(session.scalars(stmt).all())

    def discarded_for_day(self, for_day: date) -> list[DiscardedEntry]:
        start = datetime.combine(for_day, time.min, tzinfo=UTC)
        end = datetime.combine(for_day, time.max, tzinfo=UTC)
        with get_session() as session:
            stmt = (
                select(DiscardedEntry)
                .where(DiscardedEntry.created_at >= start, DiscardedEntry.created_at <= end)
                .order_by(desc(DiscardedEntry.id))
            )
            return list(session.scalars(stmt).all())

    def discarded_for_session(self, session_id: int) -> list[DiscardedEntry]:
        with get_session() as session:
            stmt = (
                select(DiscardedEntry)
                .where(DiscardedEntry.scan_session_id == session_id)
                .order_by(desc(DiscardedEntry.id))
            )
            return list(session.scalars(stmt).all())

    def sessions_history(self, limit: int = 20) -> list[ScanSession]:
        with get_session() as session:
            stmt = select(ScanSession).order_by(desc(ScanSession.id)).limit(limit)
            return list(session.scalars(stmt).all())

    def discovery_for_session(self, session_id: int) -> list[DiscoveryCandidate]:
        with get_session() as session:
            stmt = (
                select(DiscoveryCandidate)
                .where(DiscoveryCandidate.scan_session_id == session_id)
                .order_by(desc(DiscoveryCandidate.id))
            )
            return list(session.scalars(stmt).all())

    def validations_for_session(self, session_id: int) -> list[DexScreenerValidation]:
        with get_session() as session:
            stmt = (
                select(DexScreenerValidation)
                .where(DexScreenerValidation.scan_session_id == session_id)
                .order_by(desc(DexScreenerValidation.id))
            )
            return list(session.scalars(stmt).all())

    def token_watchlist_latest(self, token_address: str) -> WatchlistEntry | None:
        with get_session() as session:
            stmt = (
                select(WatchlistEntry)
                .where(WatchlistEntry.token_address == token_address)
                .order_by(desc(WatchlistEntry.id))
                .limit(1)
            )
            return session.scalars(stmt).first()

    def token_discarded_latest(self, token_address: str) -> DiscardedEntry | None:
        with get_session() as session:
            stmt = (
                select(DiscardedEntry)
                .where(DiscardedEntry.token_address == token_address)
                .order_by(desc(DiscardedEntry.id))
                .limit(1)
            )
            return session.scalars(stmt).first()

    def token_latest_signals(self, token_address: str) -> dict:
        with get_session() as session:
            whale = session.scalars(
                select(WhaleSignalSnapshot)
                .where(WhaleSignalSnapshot.token_address == token_address)
                .order_by(desc(WhaleSignalSnapshot.id))
                .limit(1)
            ).first()
            social = session.scalars(
                select(SocialSignalSnapshot)
                .where(SocialSignalSnapshot.token_address == token_address)
                .order_by(desc(SocialSignalSnapshot.id))
                .limit(1)
            ).first()
            demand = session.scalars(
                select(DemandSignalSnapshot)
                .where(DemandSignalSnapshot.token_address == token_address)
                .order_by(desc(DemandSignalSnapshot.id))
                .limit(1)
            ).first()
            narrative = session.scalars(
                select(NarrativeSignalSnapshot)
                .where(NarrativeSignalSnapshot.token_address == token_address)
                .order_by(desc(NarrativeSignalSnapshot.id))
                .limit(1)
            ).first()
            breakout = session.scalars(
                select(BreakoutSignalSnapshot)
                .where(BreakoutSignalSnapshot.token_address == token_address)
                .order_by(desc(BreakoutSignalSnapshot.id))
                .limit(1)
            ).first()
            composite = session.scalars(
                select(SignalCompositeSnapshot)
                .where(SignalCompositeSnapshot.token_address == token_address)
                .order_by(desc(SignalCompositeSnapshot.id))
                .limit(1)
            ).first()

        def as_dict(row: object, keys: list[str]) -> dict:
            if row is None:
                return {}
            return {k: getattr(row, k, None) for k in keys}

        return {
            "whale": as_dict(
                whale,
                [
                    "whale_accumulation_score",
                    "smart_wallet_presence_score",
                    "net_whale_inflow",
                    "repeated_buyer_score",
                    "insider_risk_score",
                    "dev_sell_pressure_score",
                ],
            ),
            "social": as_dict(
                social,
                [
                    "social_velocity_score",
                    "community_growth_score",
                    "organic_engagement_score",
                    "bot_suspicion_score",
                    "narrative_repetition_score",
                    "social_wallet_divergence_score",
                ],
            ),
            "demand": as_dict(
                demand,
                [
                    "transaction_demand_score",
                    "tx_count_acceleration",
                    "organic_volume_score",
                    "wash_trading_suspicion_score",
                    "buyer_distribution_score",
                    "trade_continuity_score",
                ],
            ),
            "narrative": as_dict(
                narrative,
                [
                    "narrative_strength_score",
                    "meme_clarity_score",
                    "viral_repeatability_score",
                    "cross_source_narrative_score",
                    "paid_vs_organic_narrative_gap",
                    "cult_signal_score",
                ],
            ),
            "breakout": as_dict(
                breakout,
                [
                    "breakout_setup_score",
                    "consolidation_quality_score",
                    "breakout_confirmation_score",
                    "overextension_penalty",
                    "entry_timing_score",
                    "invalidation_quality_score",
                ],
            ),
            "composite": as_dict(
                composite,
                [
                    "whale_accumulation_score",
                    "social_momentum_score",
                    "demand_quality_score",
                    "narrative_strength_score",
                    "breakout_timing_score",
                    "speculative_momentum_score",
                    "gate_notes",
                ],
            ),
        }

    def latest_whales(self, limit: int = 20) -> list[WhaleSignalSnapshot]:
        with get_session() as session:
            stmt = select(WhaleSignalSnapshot).order_by(desc(WhaleSignalSnapshot.id)).limit(limit)
            return list(session.scalars(stmt).all())

    def latest_social(self, limit: int = 20) -> list[SocialSignalSnapshot]:
        with get_session() as session:
            stmt = select(SocialSignalSnapshot).order_by(desc(SocialSignalSnapshot.id)).limit(limit)
            return list(session.scalars(stmt).all())

    def latest_demand(self, limit: int = 20) -> list[DemandSignalSnapshot]:
        with get_session() as session:
            stmt = select(DemandSignalSnapshot).order_by(desc(DemandSignalSnapshot.id)).limit(limit)
            return list(session.scalars(stmt).all())

    def latest_narrative(self, limit: int = 20) -> list[NarrativeSignalSnapshot]:
        with get_session() as session:
            stmt = select(NarrativeSignalSnapshot).order_by(desc(NarrativeSignalSnapshot.id)).limit(limit)
            return list(session.scalars(stmt).all())

    def latest_breakouts(self, limit: int = 20) -> list[BreakoutSignalSnapshot]:
        with get_session() as session:
            stmt = select(BreakoutSignalSnapshot).order_by(desc(BreakoutSignalSnapshot.id)).limit(limit)
            return list(session.scalars(stmt).all())

    def latest_wallet_flows(self, limit: int = 20) -> list[WalletFlowSnapshot]:
        with get_session() as session:
            stmt = select(WalletFlowSnapshot).order_by(desc(WalletFlowSnapshot.id)).limit(limit)
            return list(session.scalars(stmt).all())

    def wallet_flow_for_token(self, token_address: str, limit: int = 40) -> list[WalletFlowSnapshot]:
        with get_session() as session:
            stmt = (
                select(WalletFlowSnapshot)
                .where(WalletFlowSnapshot.token_address == token_address)
                .order_by(desc(WalletFlowSnapshot.id))
                .limit(limit)
            )
            return list(session.scalars(stmt).all())

    def latest_holder_distribution_for_token(self, token_address: str) -> HolderDistributionSnapshot | None:
        with get_session() as session:
            stmt = (
                select(HolderDistributionSnapshot)
                .where(HolderDistributionSnapshot.token_address == token_address)
                .order_by(desc(HolderDistributionSnapshot.id))
                .limit(1)
            )
            return session.scalars(stmt).first()

    def latest_paid_attention(self, limit: int = 20) -> list[PaidAttentionSnapshot]:
        with get_session() as session:
            stmt = select(PaidAttentionSnapshot).order_by(desc(PaidAttentionSnapshot.id)).limit(limit)
            return list(session.scalars(stmt).all())

    def token_paid_attention_latest(self, token_address: str) -> PaidAttentionSnapshot | None:
        with get_session() as session:
            stmt = (
                select(PaidAttentionSnapshot)
                .where(PaidAttentionSnapshot.token_address == token_address)
                .order_by(desc(PaidAttentionSnapshot.id))
                .limit(1)
            )
            return session.scalars(stmt).first()

    def latest_exit_plans(self, limit: int = 20) -> list[ExitPlanSnapshot]:
        with get_session() as session:
            stmt = select(ExitPlanSnapshot).order_by(desc(ExitPlanSnapshot.id)).limit(limit)
            return list(session.scalars(stmt).all())

    def token_exit_plan_latest(self, token_address: str) -> ExitPlanSnapshot | None:
        with get_session() as session:
            stmt = (
                select(ExitPlanSnapshot)
                .where(ExitPlanSnapshot.token_address == token_address)
                .order_by(desc(ExitPlanSnapshot.id))
                .limit(1)
            )
            return session.scalars(stmt).first()
