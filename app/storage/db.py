from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


class Token(Base):
    __tablename__ = "tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    network: Mapped[str] = mapped_column(String(20), index=True)
    address: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class ScoreSnapshot(Base):
    __tablename__ = "score_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token_address: Mapped[str] = mapped_column(String(128), index=True)
    token_symbol: Mapped[str] = mapped_column(String(32), index=True, default="TOKEN")
    token_name: Mapped[str] = mapped_column(String(128), default="")
    token_chain: Mapped[str] = mapped_column(String(24), index=True, default="solana")
    principal_pair: Mapped[str] = mapped_column(String(128), default="")
    metadata_source: Mapped[str] = mapped_column(String(24), index=True, default="unknown")
    metadata_confidence: Mapped[str] = mapped_column(String(16), index=True, default="unverified")
    metadata_is_fallback: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_last_source: Mapped[str] = mapped_column(String(24), index=True, default="unknown")
    metadata_last_validated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    metadata_conflict: Mapped[bool] = mapped_column(Boolean, default=False)
    identity_quality_score: Mapped[int] = mapped_column(Integer, default=50, index=True)
    identity_gate_reason: Mapped[str] = mapped_column(String(256), default="")
    identity_rule_applied: Mapped[str] = mapped_column(String(64), default="")
    identity_confidence_cap: Mapped[float] = mapped_column(Float, default=1.0)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True, default=datetime.utcnow)
    entry_price: Mapped[float] = mapped_column(Float, default=0.0)
    long_score: Mapped[float] = mapped_column(Float)
    short_score: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    penalties: Mapped[float] = mapped_column(Float)
    veto: Mapped[bool] = mapped_column(Boolean, default=False)
    decision: Mapped[str] = mapped_column(String(20), index=True)
    reasons_json: Mapped[dict] = mapped_column(JSON, default=dict)
    features_json: Mapped[dict] = mapped_column(JSON, default=dict)


class AlertSent(Base):
    __tablename__ = "alerts_sent"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token_address: Mapped[str] = mapped_column(String(128), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    decision: Mapped[str] = mapped_column(String(20), index=True)
    channel: Mapped[str] = mapped_column(String(20), default="telegram")
    message_hash: Mapped[str] = mapped_column(String(128), index=True)


class SignalOutcome(Base):
    __tablename__ = "signal_outcomes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    score_snapshot_id: Mapped[int] = mapped_column(Integer, index=True)
    horizon: Mapped[str] = mapped_column(String(10), index=True)
    ret_pct: Mapped[float] = mapped_column(Float, default=0.0)
    max_fav_excursion: Mapped[float] = mapped_column(Float, default=0.0)
    max_adv_excursion: Mapped[float] = mapped_column(Float, default=0.0)


class PerformanceReport(Base):
    __tablename__ = "performance_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True, default=datetime.utcnow)
    horizon: Mapped[str] = mapped_column(String(10), index=True)
    n_signals: Mapped[int] = mapped_column(Integer, default=0)
    win_rate: Mapped[float] = mapped_column(Float, default=0.0)
    avg_win: Mapped[float] = mapped_column(Float, default=0.0)
    avg_loss: Mapped[float] = mapped_column(Float, default=0.0)
    expectancy: Mapped[float] = mapped_column(Float, default=0.0)
    precision_top_decile: Mapped[float] = mapped_column(Float, default=0.0)
    max_drawdown_proxy: Mapped[float] = mapped_column(Float, default=0.0)
    sharpe_proxy: Mapped[float] = mapped_column(Float, default=0.0)


class ScanSession(Base):
    __tablename__ = "scan_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, index=True, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(24), index=True, default="running")
    degraded: Mapped[bool] = mapped_column(Boolean, default=False)
    source_summary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    config_json: Mapped[dict] = mapped_column(JSON, default=dict)
    discovered_count: Mapped[int] = mapped_column(Integer, default=0)
    validated_count: Mapped[int] = mapped_column(Integer, default=0)
    classified_count: Mapped[int] = mapped_column(Integer, default=0)
    watchlist_count: Mapped[int] = mapped_column(Integer, default=0)
    discarded_count: Mapped[int] = mapped_column(Integer, default=0)
    notes_json: Mapped[dict] = mapped_column(JSON, default=dict)


class DiscoveryCandidate(Base):
    __tablename__ = "discovery_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_session_id: Mapped[int] = mapped_column(Integer, index=True)
    token_address: Mapped[str] = mapped_column(String(128), index=True)
    symbol: Mapped[str] = mapped_column(String(32), default="UNK")
    source: Mapped[str] = mapped_column(String(32), default="birdeye")
    detected_at: Mapped[datetime] = mapped_column(DateTime, index=True, default=datetime.utcnow)
    token_age_minutes: Mapped[float] = mapped_column(Float, default=0.0)
    liquidity_usd: Mapped[float] = mapped_column(Float, default=0.0)
    volume_1h_usd: Mapped[float] = mapped_column(Float, default=0.0)
    transactions_1h: Mapped[int] = mapped_column(Integer, default=0)
    buys_1h: Mapped[int] = mapped_column(Integer, default=0)
    sells_1h: Mapped[int] = mapped_column(Integer, default=0)
    buys_sells_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    market_cap_usd: Mapped[float] = mapped_column(Float, default=0.0)
    price_change_5m: Mapped[float] = mapped_column(Float, default=0.0)
    price_change_1h: Mapped[float] = mapped_column(Float, default=0.0)
    volume_acceleration: Mapped[float] = mapped_column(Float, default=0.0)
    metadata_source: Mapped[str] = mapped_column(String(24), default="unknown")
    metadata_confidence: Mapped[str] = mapped_column(String(16), default="unverified")
    metadata_is_fallback: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_last_source: Mapped[str] = mapped_column(String(24), default="unknown")
    metadata_last_validated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    metadata_conflict: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_json: Mapped[dict] = mapped_column(JSON, default=dict)


class DexScreenerValidation(Base):
    __tablename__ = "dexscreener_validations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_session_id: Mapped[int] = mapped_column(Integer, index=True)
    token_address: Mapped[str] = mapped_column(String(128), index=True)
    source: Mapped[str] = mapped_column(String(32), default="dexscreener")
    validated_at: Mapped[datetime] = mapped_column(DateTime, index=True, default=datetime.utcnow)
    primary_pair: Mapped[str] = mapped_column(String(128), default="")
    chain_id: Mapped[str] = mapped_column(String(24), default="")
    dex_id: Mapped[str] = mapped_column(String(64), default="")
    liquidity_usd: Mapped[float] = mapped_column(Float, default=0.0)
    volume_1h_usd: Mapped[float] = mapped_column(Float, default=0.0)
    price_change_5m: Mapped[float] = mapped_column(Float, default=0.0)
    price_change_1h: Mapped[float] = mapped_column(Float, default=0.0)
    boosts_active: Mapped[float] = mapped_column(Float, default=0.0)
    paid_orders: Mapped[float] = mapped_column(Float, default=0.0)
    activity_score: Mapped[float] = mapped_column(Float, default=0.0)
    organic_flow_ok: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_source: Mapped[str] = mapped_column(String(24), default="unknown")
    metadata_confidence: Mapped[str] = mapped_column(String(16), default="unverified")
    metadata_is_fallback: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_last_source: Mapped[str] = mapped_column(String(24), default="unknown")
    metadata_last_validated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    metadata_conflict: Mapped[bool] = mapped_column(Boolean, default=False)
    flags_json: Mapped[dict] = mapped_column(JSON, default=dict)
    raw_json: Mapped[dict] = mapped_column(JSON, default=dict)


class ScannerFlag(Base):
    __tablename__ = "scanner_flags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_session_id: Mapped[int] = mapped_column(Integer, index=True)
    token_address: Mapped[str] = mapped_column(String(128), index=True)
    flag_name: Mapped[str] = mapped_column(String(64), index=True)
    flag_value: Mapped[bool] = mapped_column(Boolean, default=False)
    details_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True, default=datetime.utcnow)


class WatchlistEntry(Base):
    __tablename__ = "watchlist_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_session_id: Mapped[int] = mapped_column(Integer, index=True)
    token_address: Mapped[str] = mapped_column(String(128), index=True)
    symbol: Mapped[str] = mapped_column(String(32), default="UNK")
    category: Mapped[str] = mapped_column(String(32), index=True)
    score_long: Mapped[float] = mapped_column(Float, default=0.0)
    score_short: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    risk_label: Mapped[str] = mapped_column(String(16), default="medio")
    risk_value: Mapped[float] = mapped_column(Float, default=0.0)
    liquidity_usd: Mapped[float] = mapped_column(Float, default=0.0)
    rank_order: Mapped[int] = mapped_column(Integer, default=0)
    main_reason: Mapped[str] = mapped_column(String(280), default="")
    explanation: Mapped[str] = mapped_column(String(500), default="")
    metadata_source: Mapped[str] = mapped_column(String(24), default="unknown")
    metadata_confidence: Mapped[str] = mapped_column(String(16), default="unverified")
    metadata_is_fallback: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_last_source: Mapped[str] = mapped_column(String(24), default="unknown")
    metadata_last_validated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    metadata_conflict: Mapped[bool] = mapped_column(Boolean, default=False)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True, default=datetime.utcnow)


class DiscardedEntry(Base):
    __tablename__ = "discarded_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_session_id: Mapped[int] = mapped_column(Integer, index=True)
    token_address: Mapped[str] = mapped_column(String(128), index=True)
    symbol: Mapped[str] = mapped_column(String(32), default="UNK")
    category: Mapped[str] = mapped_column(String(32), default="NO TRADE")
    discard_reason: Mapped[str] = mapped_column(String(280), default="")
    metadata_source: Mapped[str] = mapped_column(String(24), default="unknown")
    metadata_confidence: Mapped[str] = mapped_column(String(16), default="unverified")
    metadata_is_fallback: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_last_source: Mapped[str] = mapped_column(String(24), default="unknown")
    metadata_last_validated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    metadata_conflict: Mapped[bool] = mapped_column(Boolean, default=False)
    flags_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True, default=datetime.utcnow)


class WhaleSignalSnapshot(Base):
    __tablename__ = "whale_signal_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_session_id: Mapped[int] = mapped_column(Integer, index=True)
    token_address: Mapped[str] = mapped_column(String(128), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True, default=datetime.utcnow)
    whale_accumulation_score: Mapped[float] = mapped_column(Float, default=0.0)
    smart_wallet_presence_score: Mapped[float] = mapped_column(Float, default=0.0)
    net_whale_inflow: Mapped[float] = mapped_column(Float, default=0.0)
    repeated_buyer_score: Mapped[float] = mapped_column(Float, default=0.0)
    insider_risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    dev_sell_pressure_score: Mapped[float] = mapped_column(Float, default=0.0)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)


class SocialSignalSnapshot(Base):
    __tablename__ = "social_signal_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_session_id: Mapped[int] = mapped_column(Integer, index=True)
    token_address: Mapped[str] = mapped_column(String(128), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True, default=datetime.utcnow)
    social_velocity_score: Mapped[float] = mapped_column(Float, default=0.0)
    community_growth_score: Mapped[float] = mapped_column(Float, default=0.0)
    organic_engagement_score: Mapped[float] = mapped_column(Float, default=0.0)
    bot_suspicion_score: Mapped[float] = mapped_column(Float, default=0.0)
    narrative_repetition_score: Mapped[float] = mapped_column(Float, default=0.0)
    social_wallet_divergence_score: Mapped[float] = mapped_column(Float, default=0.0)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)


class DemandSignalSnapshot(Base):
    __tablename__ = "demand_signal_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_session_id: Mapped[int] = mapped_column(Integer, index=True)
    token_address: Mapped[str] = mapped_column(String(128), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True, default=datetime.utcnow)
    transaction_demand_score: Mapped[float] = mapped_column(Float, default=0.0)
    tx_count_acceleration: Mapped[float] = mapped_column(Float, default=0.0)
    organic_volume_score: Mapped[float] = mapped_column(Float, default=0.0)
    wash_trading_suspicion_score: Mapped[float] = mapped_column(Float, default=0.0)
    buyer_distribution_score: Mapped[float] = mapped_column(Float, default=0.0)
    trade_continuity_score: Mapped[float] = mapped_column(Float, default=0.0)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)


class NarrativeSignalSnapshot(Base):
    __tablename__ = "narrative_signal_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_session_id: Mapped[int] = mapped_column(Integer, index=True)
    token_address: Mapped[str] = mapped_column(String(128), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True, default=datetime.utcnow)
    narrative_strength_score: Mapped[float] = mapped_column(Float, default=0.0)
    meme_clarity_score: Mapped[float] = mapped_column(Float, default=0.0)
    viral_repeatability_score: Mapped[float] = mapped_column(Float, default=0.0)
    cross_source_narrative_score: Mapped[float] = mapped_column(Float, default=0.0)
    paid_vs_organic_narrative_gap: Mapped[float] = mapped_column(Float, default=0.0)
    cult_signal_score: Mapped[float] = mapped_column(Float, default=0.0)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)


class BreakoutSignalSnapshot(Base):
    __tablename__ = "breakout_signal_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_session_id: Mapped[int] = mapped_column(Integer, index=True)
    token_address: Mapped[str] = mapped_column(String(128), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True, default=datetime.utcnow)
    breakout_setup_score: Mapped[float] = mapped_column(Float, default=0.0)
    consolidation_quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    breakout_confirmation_score: Mapped[float] = mapped_column(Float, default=0.0)
    overextension_penalty: Mapped[float] = mapped_column(Float, default=0.0)
    entry_timing_score: Mapped[float] = mapped_column(Float, default=0.0)
    invalidation_quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)


class PaidAttentionSnapshot(Base):
    __tablename__ = "paid_attention_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_session_id: Mapped[int] = mapped_column(Integer, index=True)
    token_address: Mapped[str] = mapped_column(String(128), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True, default=datetime.utcnow)
    boost_intensity: Mapped[float] = mapped_column(Float, default=0.0)
    paid_attention_high: Mapped[bool] = mapped_column(Boolean, default=False)
    promo_flow_divergence: Mapped[bool] = mapped_column(Boolean, default=False)
    paid_vs_organic_gap: Mapped[float] = mapped_column(Float, default=0.0)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)


class ExitPlanSnapshot(Base):
    __tablename__ = "exit_plan_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_session_id: Mapped[int] = mapped_column(Integer, index=True)
    token_address: Mapped[str] = mapped_column(String(128), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True, default=datetime.utcnow)
    entry_zone: Mapped[float] = mapped_column(Float, default=0.0)
    invalidation_zone: Mapped[float] = mapped_column(Float, default=0.0)
    tp1: Mapped[float] = mapped_column(Float, default=0.0)
    tp2: Mapped[float] = mapped_column(Float, default=0.0)
    tp3: Mapped[float] = mapped_column(Float, default=0.0)
    partial_take_profit_plan: Mapped[str] = mapped_column(String(256), default="")
    exit_plan_viability: Mapped[float] = mapped_column(Float, default=0.0)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)


class SignalCompositeSnapshot(Base):
    __tablename__ = "signal_composite_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_session_id: Mapped[int] = mapped_column(Integer, index=True)
    token_address: Mapped[str] = mapped_column(String(128), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True, default=datetime.utcnow)
    whale_accumulation_score: Mapped[float] = mapped_column(Float, default=0.0)
    social_momentum_score: Mapped[float] = mapped_column(Float, default=0.0)
    demand_quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    narrative_strength_score: Mapped[float] = mapped_column(Float, default=0.0)
    breakout_timing_score: Mapped[float] = mapped_column(Float, default=0.0)
    speculative_momentum_score: Mapped[float] = mapped_column(Float, default=0.0)
    gate_notes: Mapped[str] = mapped_column(String(280), default="")
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)


class WalletFlowSnapshot(Base):
    __tablename__ = "wallet_flow_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_session_id: Mapped[int] = mapped_column(Integer, index=True)
    token_address: Mapped[str] = mapped_column(String(128), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True, default=datetime.utcnow)
    whale_accumulation_score: Mapped[float] = mapped_column(Float, default=0.0)
    smart_wallet_presence_score: Mapped[float] = mapped_column(Float, default=0.0)
    net_whale_inflow: Mapped[float] = mapped_column(Float, default=0.0)
    repeated_buyer_score: Mapped[float] = mapped_column(Float, default=0.0)
    insider_risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    dev_sell_pressure_score: Mapped[float] = mapped_column(Float, default=0.0)
    wallet_flow_score: Mapped[float] = mapped_column(Float, default=0.0)
    labeled_wallet_count: Mapped[int] = mapped_column(Integer, default=0)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)


class HolderDistributionSnapshot(Base):
    __tablename__ = "holder_distribution_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_session_id: Mapped[int] = mapped_column(Integer, index=True)
    token_address: Mapped[str] = mapped_column(String(128), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True, default=datetime.utcnow)
    top10_holders_pct: Mapped[float] = mapped_column(Float, default=0.0)
    top25_holders_pct: Mapped[float] = mapped_column(Float, default=0.0)
    holder_concentration_score: Mapped[float] = mapped_column(Float, default=0.0)
    suspicious_cluster_score: Mapped[float] = mapped_column(Float, default=0.0)
    connected_wallet_clusters: Mapped[int] = mapped_column(Integer, default=0)
    organic_distribution_score: Mapped[float] = mapped_column(Float, default=0.0)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)


settings = get_settings()
engine = create_engine(settings.database_url, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_score_snapshot_identity_columns()
    _ensure_scanner_identity_columns()


def _ensure_score_snapshot_identity_columns() -> None:
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("score_snapshots")}
    expected_columns: dict[str, str] = {
        "token_symbol": "VARCHAR(32)",
        "token_name": "VARCHAR(128)",
        "token_chain": "VARCHAR(24)",
        "principal_pair": "VARCHAR(128)",
        "metadata_source": "VARCHAR(24)",
        "metadata_confidence": "VARCHAR(16)",
        "metadata_is_fallback": "BOOLEAN",
        "metadata_last_source": "VARCHAR(24)",
        "metadata_last_validated_at": "DATETIME",
        "metadata_conflict": "BOOLEAN",
        "identity_quality_score": "INTEGER",
        "identity_gate_reason": "VARCHAR(256)",
        "identity_rule_applied": "VARCHAR(64)",
        "identity_confidence_cap": "FLOAT",
    }

    with engine.begin() as conn:
        for col_name, col_type in expected_columns.items():
            if col_name not in columns:
                conn.execute(text(f"ALTER TABLE score_snapshots ADD COLUMN {col_name} {col_type}"))

        conn.execute(text("UPDATE score_snapshots SET token_symbol = 'TOKEN' WHERE token_symbol IS NULL OR token_symbol = ''"))
        conn.execute(text("UPDATE score_snapshots SET token_name = 'Token sin nombre' WHERE token_name IS NULL OR token_name = ''"))
        conn.execute(text("UPDATE score_snapshots SET token_chain = 'solana' WHERE token_chain IS NULL OR token_chain = ''"))
        conn.execute(text("UPDATE score_snapshots SET principal_pair = '' WHERE principal_pair IS NULL"))
        conn.execute(text("UPDATE score_snapshots SET metadata_source = 'unknown' WHERE metadata_source IS NULL OR metadata_source = ''"))
        conn.execute(text("UPDATE score_snapshots SET metadata_confidence = 'unverified' WHERE metadata_confidence IS NULL OR metadata_confidence = ''"))
        conn.execute(text("UPDATE score_snapshots SET metadata_is_fallback = 0 WHERE metadata_is_fallback IS NULL"))
        conn.execute(text("UPDATE score_snapshots SET metadata_last_source = 'unknown' WHERE metadata_last_source IS NULL OR metadata_last_source = ''"))
        conn.execute(text("UPDATE score_snapshots SET metadata_conflict = 0 WHERE metadata_conflict IS NULL"))
        conn.execute(text("UPDATE score_snapshots SET metadata_source = 'local_fallback', metadata_confidence = 'fallback', metadata_is_fallback = 1, metadata_last_source = 'local_fallback' WHERE metadata_confidence = 'unverified' AND (token_symbol LIKE 'TK-%' OR token_name LIKE 'Token %')"))
        # Identity gate columns defaults
        conn.execute(text("UPDATE score_snapshots SET identity_quality_score = 50 WHERE identity_quality_score IS NULL"))
        conn.execute(text("UPDATE score_snapshots SET identity_gate_reason = '' WHERE identity_gate_reason IS NULL"))
        conn.execute(text("UPDATE score_snapshots SET identity_rule_applied = '' WHERE identity_rule_applied IS NULL"))
        conn.execute(text("UPDATE score_snapshots SET identity_confidence_cap = 1.0 WHERE identity_confidence_cap IS NULL"))

def _ensure_scanner_identity_columns() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    scanner_tables = {
        "discovery_candidates": {
            "metadata_source": "VARCHAR(24)",
            "metadata_confidence": "VARCHAR(16)",
            "metadata_is_fallback": "BOOLEAN",
            "metadata_last_source": "VARCHAR(24)",
            "metadata_last_validated_at": "DATETIME",
            "metadata_conflict": "BOOLEAN",
        },
        "dexscreener_validations": {
            "metadata_source": "VARCHAR(24)",
            "metadata_confidence": "VARCHAR(16)",
            "metadata_is_fallback": "BOOLEAN",
            "metadata_last_source": "VARCHAR(24)",
            "metadata_last_validated_at": "DATETIME",
            "metadata_conflict": "BOOLEAN",
        },
        "watchlist_entries": {
            "metadata_source": "VARCHAR(24)",
            "metadata_confidence": "VARCHAR(16)",
            "metadata_is_fallback": "BOOLEAN",
            "metadata_last_source": "VARCHAR(24)",
            "metadata_last_validated_at": "DATETIME",
            "metadata_conflict": "BOOLEAN",
        },
        "discarded_entries": {
            "metadata_source": "VARCHAR(24)",
            "metadata_confidence": "VARCHAR(16)",
            "metadata_is_fallback": "BOOLEAN",
            "metadata_last_source": "VARCHAR(24)",
            "metadata_last_validated_at": "DATETIME",
            "metadata_conflict": "BOOLEAN",
        },
    }

    with engine.begin() as conn:
        for table_name, cols in scanner_tables.items():
            if table_name not in table_names:
                continue
            existing = {col["name"] for col in inspector.get_columns(table_name)}
            for col_name, col_type in cols.items():
                if col_name not in existing:
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}"))
            conn.execute(text(f"UPDATE {table_name} SET metadata_source = 'unknown' WHERE metadata_source IS NULL OR metadata_source = ''"))
            conn.execute(text(f"UPDATE {table_name} SET metadata_confidence = 'unverified' WHERE metadata_confidence IS NULL OR metadata_confidence = ''"))
            conn.execute(text(f"UPDATE {table_name} SET metadata_is_fallback = 0 WHERE metadata_is_fallback IS NULL"))
            conn.execute(text(f"UPDATE {table_name} SET metadata_last_source = 'unknown' WHERE metadata_last_source IS NULL OR metadata_last_source = ''"))
            conn.execute(text(f"UPDATE {table_name} SET metadata_conflict = 0 WHERE metadata_conflict IS NULL"))
            if 'symbol' in existing:
                conn.execute(text(f"UPDATE {table_name} SET metadata_source = 'local_fallback', metadata_confidence = 'fallback', metadata_is_fallback = 1, metadata_last_source = 'local_fallback' WHERE metadata_confidence = 'unverified' AND symbol LIKE 'TK-%'"))


def get_session() -> Session:
    return SessionLocal()
