from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env.local", ".env"), env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="dev", alias="APP_ENV")
    app_name: str = Field(default="meme-research", alias="APP_NAME")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    network: str = Field(default="solana", alias="NETWORK")
    scan_interval_seconds: int = Field(default=300, alias="SCAN_INTERVAL_SECONDS")

    database_url: str = Field(
        default="sqlite:///./meme_research.db",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    dexscreener_base_url: str = Field(default="https://api.dexscreener.com", alias="DEXSCREENER_BASE_URL")
    birdeye_base_url: str = Field(default="https://public-api.birdeye.so", alias="BIRDEYE_BASE_URL")
    birdeye_api_key: str = Field(default="", alias="BIRDEYE_API_KEY")
    goplus_base_url: str = Field(default="https://api.gopluslabs.io", alias="GOPLUS_BASE_URL")
    honeypot_base_url: str = Field(default="https://api.honeypot.is", alias="HONEYPOT_BASE_URL")
    helius_rpc_url: str = Field(default="https://mainnet.helius-rpc.com", alias="HELIUS_RPC_URL")
    helius_api_key: str = Field(default="", alias="HELIUS_API_KEY")
    coinglass_base_url: str = Field(default="https://open-api.coinglass.com", alias="COINGLASS_BASE_URL")
    coinglass_api_key: str = Field(default="", alias="COINGLASS_API_KEY")

    polymarket_enabled: bool = Field(default=False, alias="POLYMARKET_ENABLED")
    polymarket_base_url: str = Field(default="https://api.polymarket.com", alias="POLYMARKET_BASE_URL")
    polymarket_api_key: str = Field(default="", alias="POLYMARKET_API_KEY")
    polymarket_search_terms: str = Field(default="solana,meme,crypto sentiment,BTC,macro,regulation", alias="POLYMARKET_SEARCH_TERMS")
    scanner_polymarket_impact: float = Field(default=0.08, alias="SCANNER_POLYMARKET_IMPACT")
    scanner_polymarket_max_event_boost: float = Field(default=8.0, alias="SCANNER_POLYMARKET_MAX_EVENT_BOOST")
    scanner_polymarket_risk_penalty: float = Field(default=6.0, alias="SCANNER_POLYMARKET_RISK_PENALTY")

    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(default="", alias="TELEGRAM_CHAT_ID")

    min_liquidity_usd: float = Field(default=50000, alias="MIN_LIQUIDITY_USD")
    min_volume_1h_usd: float = Field(default=20000, alias="MIN_VOLUME_1H_USD")
    max_spread_bps: float = Field(default=200, alias="MAX_SPREAD_BPS")
    max_top10_holders_pct: float = Field(default=70, alias="MAX_TOP10_HOLDERS_PCT")
    min_lp_locked_pct: float = Field(default=60, alias="MIN_LP_LOCKED_PCT")

    long_threshold: float = Field(default=70, alias="LONG_THRESHOLD")
    short_threshold: float = Field(default=72, alias="SHORT_THRESHOLD")
    min_confidence: float = Field(default=0.65, alias="MIN_CONFIDENCE")
    top_k: int = Field(default=10, alias="TOP_K")
    alert_dedupe_minutes: int = Field(default=30, alias="ALERT_DEDUPE_MINUTES")
    outcome_horizons: str = Field(default="1h,4h,24h", alias="OUTCOME_HORIZONS")
    log_dir: str = Field(default="./logs", alias="LOG_DIR")
    log_file: str = Field(default="meme_research.log", alias="LOG_FILE")

    scanner_auto_enabled: bool = Field(default=True, alias="SCANNER_AUTO_ENABLED")
    scanner_interval_minutes: int = Field(default=30, alias="SCANNER_INTERVAL_MINUTES")
    scanner_discovery_limit: int = Field(default=120, alias="SCANNER_DISCOVERY_LIMIT")
    scanner_min_token_age_minutes: int = Field(default=30, alias="SCANNER_MIN_TOKEN_AGE_MINUTES")
    scanner_max_token_age_hours: int = Field(default=72, alias="SCANNER_MAX_TOKEN_AGE_HOURS")
    scanner_min_liquidity_usd: float = Field(default=80_000, alias="SCANNER_MIN_LIQUIDITY_USD")
    scanner_min_volume_1h_usd: float = Field(default=40_000, alias="SCANNER_MIN_VOLUME_1H_USD")
    scanner_min_transactions_1h: int = Field(default=120, alias="SCANNER_MIN_TRANSACTIONS_1H")
    scanner_min_buys_sells_ratio: float = Field(default=1.1, alias="SCANNER_MIN_BUYS_SELLS_RATIO")
    scanner_max_buys_sells_ratio: float = Field(default=2.8, alias="SCANNER_MAX_BUYS_SELLS_RATIO")
    scanner_min_market_cap_usd: float = Field(default=300_000, alias="SCANNER_MIN_MARKET_CAP_USD")
    scanner_max_market_cap_usd: float = Field(default=25_000_000, alias="SCANNER_MAX_MARKET_CAP_USD")
    scanner_min_volume_acceleration: float = Field(default=0.12, alias="SCANNER_MIN_VOLUME_ACCELERATION")
    scanner_max_paid_attention_score: float = Field(default=2.0, alias="SCANNER_MAX_PAID_ATTENTION_SCORE")
    scanner_max_risk_for_long: float = Field(default=35.0, alias="SCANNER_MAX_RISK_FOR_LONG")
    scanner_max_risk_for_short: float = Field(default=32.0, alias="SCANNER_MAX_RISK_FOR_SHORT")
    scanner_min_score_for_long: float = Field(default=68.0, alias="SCANNER_MIN_SCORE_FOR_LONG")
    scanner_min_confidence_for_long: float = Field(default=0.72, alias="SCANNER_MIN_CONFIDENCE_FOR_LONG")
    scanner_min_score_for_short: float = Field(default=70.0, alias="SCANNER_MIN_SCORE_FOR_SHORT")
    scanner_min_confidence_for_short: float = Field(default=0.74, alias="SCANNER_MIN_CONFIDENCE_FOR_SHORT")
    scanner_min_data_quality_score: float = Field(default=65.0, alias="SCANNER_MIN_DATA_QUALITY_SCORE")
    scanner_max_vertical_pump_pct: float = Field(default=55.0, alias="SCANNER_MAX_VERTICAL_PUMP_PCT")
    scanner_watchlist_strong_limit: int = Field(default=3, alias="SCANNER_WATCHLIST_STRONG_LIMIT")
    scanner_watchlist_observe_limit: int = Field(default=3, alias="SCANNER_WATCHLIST_OBSERVE_LIMIT")
    scanner_watchlist_short_limit: int = Field(default=2, alias="SCANNER_WATCHLIST_SHORT_LIMIT")

    scanner_min_whale_score_for_priority: float = Field(default=55.0, alias="SCANNER_MIN_WHALE_SCORE_FOR_PRIORITY")
    scanner_max_bot_suspicion: float = Field(default=62.0, alias="SCANNER_MAX_BOT_SUSPICION")
    scanner_min_transaction_demand: float = Field(default=48.0, alias="SCANNER_MIN_TRANSACTION_DEMAND")
    scanner_max_paid_vs_organic_gap: float = Field(default=35.0, alias="SCANNER_MAX_PAID_VS_ORGANIC_GAP")
    scanner_min_breakout_setup_score: float = Field(default=52.0, alias="SCANNER_MIN_BREAKOUT_SETUP_SCORE")
    scanner_max_overextension_penalty: float = Field(default=38.0, alias="SCANNER_MAX_OVEREXTENSION_PENALTY")
    scanner_min_speculative_momentum_for_boost: float = Field(default=54.0, alias="SCANNER_MIN_SPECULATIVE_MOMENTUM_FOR_BOOST")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
