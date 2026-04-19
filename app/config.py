from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="dev", alias="APP_ENV")
    app_name: str = Field(default="meme-research", alias="APP_NAME")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    network: str = Field(default="solana", alias="NETWORK")
    scan_interval_seconds: int = Field(default=300, alias="SCAN_INTERVAL_SECONDS")

    database_url: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5432/meme_research",
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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
