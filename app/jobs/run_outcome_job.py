from datetime import datetime, timedelta

from app.config import get_settings
from app.storage.db import SignalOutcome, get_session
from app.storage.repositories.signal_repository import SignalRepository


class OutcomeJob:
    def __init__(self) -> None:
        self._repo = SignalRepository()
        self._settings = get_settings()

    @staticmethod
    def _parse_horizon(horizon: str) -> timedelta:
        value = horizon.strip().lower()
        if value.endswith("h"):
            return timedelta(hours=int(value[:-1]))
        if value.endswith("m"):
            return timedelta(minutes=int(value[:-1]))
        return timedelta(hours=1)

    def run(self) -> None:
        rows = self._repo.latest_signals(limit=300)
        horizons = [h.strip() for h in self._settings.outcome_horizons.split(",") if h.strip()]

        with get_session() as session:
            for row in rows:
                if row.decision not in {"LONG_SETUP", "SHORT_SETUP"}:
                    continue

                entry_price = float(row.entry_price or 0.0)
                if entry_price <= 0:
                    continue

                for horizon in horizons:
                    if self._repo.has_outcome(row.id, horizon):
                        continue

                    horizon_delta = self._parse_horizon(horizon)
                    target_ts = row.ts + horizon_delta
                    if datetime.utcnow() < target_ts:
                        continue

                    future = self._repo.first_snapshot_after(row.token_address, target_ts)
                    if not future or future.entry_price <= 0:
                        continue

                    window = self._repo.snapshots_in_window(row.token_address, row.ts, target_ts)
                    if not window:
                        continue

                    prices = [float(s.entry_price or 0.0) for s in window if float(s.entry_price or 0.0) > 0]
                    if not prices:
                        continue

                    future_price = float(future.entry_price)
                    raw_ret = (future_price / entry_price) - 1.0

                    if row.decision == "SHORT_SETUP":
                        ret_pct = (-raw_ret) * 100.0
                        max_fav = ((entry_price - min(prices)) / entry_price) * 100.0
                        max_adv = ((max(prices) - entry_price) / entry_price) * 100.0
                    else:
                        ret_pct = raw_ret * 100.0
                        max_fav = ((max(prices) - entry_price) / entry_price) * 100.0
                        max_adv = ((entry_price - min(prices)) / entry_price) * 100.0

                    session.add(
                        SignalOutcome(
                            score_snapshot_id=row.id,
                            horizon=horizon,
                            ret_pct=float(ret_pct),
                            max_fav_excursion=float(max_fav),
                            max_adv_excursion=float(max_adv),
                        )
                    )
            session.commit()
