# Meme Research System (Solana-first)

MVP for meme coin discovery, risk filtering, scoring, and Telegram alerts.

## What this MVP does
- Scans opportunities every X minutes.
- Pulls data from DexScreener, Birdeye, GoPlus, Honeypot, and optional CoinGlass.
- Pulls wallet-flow signals from Helius (largest accounts + recent signatures).
- Applies hard risk veto and soft penalties.
- Computes long/short score + confidence.
- Stores snapshots in PostgreSQL.
- Sends alerts to Telegram.
- Deduplicates repeated alerts for the same token/setup in a configurable time window.
- Tracks outcomes at 1h/4h/24h horizons.
- Computes and stores evaluation metrics automatically (win rate, expectancy, top-decile precision, drawdown proxy, sharpe proxy).
- Exposes FastAPI endpoints for latest signals and token explanations.

## Quick start
1. Copy env file:
   - `copy .env.example .env`
2. Start PostgreSQL:
   - `docker compose up -d`
3. Install dependencies:
   - `pip install -r requirements.txt`
4. Run API:
   - `uvicorn app.main:app --reload`

## API
- `GET /` (dashboard web)
- `GET /health`
- `GET /signals/latest?limit=25`
- `GET /signals/top?decision=LONG_SETUP&limit=10`
- `GET /tokens/{address}/explain`
- `GET /outcomes/latest?limit=50`
- `GET /metrics/reports/latest?limit=50`
- `GET /metrics/live?horizon=4h`
- `POST /jobs/run-scan`

## Project layout
- `app/clients`: Provider adapters.
- `app/ingestion`: Discovery and context builders.
- `app/features`: TA and feature normalization.
- `app/scoring`: Risk gate, scoring, decision logic, explanations.
- `app/alerts`: Telegram formatter and sender.
- `app/storage`: DB models and repositories.
- `app/jobs`: Scan loop.
- `app/api`: HTTP routes.

## Notes
- Start with Solana meme coins only.
- Decision engine is deterministic and rules-based.
- LLM use is optional and only for explanation/reporting.
- No live execution in MVP.

## New env vars
- `HELIUS_RPC_URL`, `HELIUS_API_KEY`
- `ALERT_DEDUPE_MINUTES`
- `OUTCOME_HORIZONS` (example: `1h,4h,24h`)
