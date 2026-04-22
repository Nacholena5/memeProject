from __future__ import annotations

from datetime import datetime, timezone

from app.storage.repositories.signal_repository import SignalRepository


class DataQualityService:
    def __init__(self) -> None:
        self._repo = SignalRepository()

    @staticmethod
    def _freshness_label(minutes: float | None, ok_threshold: int, warn_threshold: int) -> str:
        if minutes is None:
            return "sin datos"
        if minutes <= ok_threshold:
            return "fresco"
        if minutes <= warn_threshold:
            return "degradado"
        return "vencido"

    @staticmethod
    def _minutes_ago(ts: datetime | None) -> float | None:
        if ts is None:
            return None
        now = datetime.now(timezone.utc)
        ts_aware = ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts.astimezone(timezone.utc)
        return max(0.0, (now - ts_aware).total_seconds() / 60.0)

    def compute(self) -> dict:
        latest_signal_ts = self._repo.latest_signal_timestamp()
        latest_outcome_ts = self._repo.latest_outcome_timestamp()
        latest_metrics_ts = self._repo.latest_metrics_timestamp()
        counts = self._repo.latest_counts()

        signal_min = self._minutes_ago(latest_signal_ts)
        outcome_min = self._minutes_ago(latest_outcome_ts)
        metrics_min = self._minutes_ago(latest_metrics_ts)

        signal_fresh = self._freshness_label(signal_min, ok_threshold=10, warn_threshold=60)
        outcome_fresh = self._freshness_label(outcome_min, ok_threshold=30, warn_threshold=180)
        metrics_fresh = self._freshness_label(metrics_min, ok_threshold=60, warn_threshold=360)

        degraded_flags = []
        if signal_fresh != "fresco":
            degraded_flags.append("señales no frescas")
        if outcome_fresh != "fresco":
            degraded_flags.append("outcomes no frescos")
        if metrics_fresh != "fresco":
            degraded_flags.append("métricas no frescas")
        if counts["signals"] == 0:
            degraded_flags.append("sin cobertura de señales")
        if counts["metrics"] == 0:
            degraded_flags.append("sin cobertura de métricas")

        status = "ok" if len(degraded_flags) == 0 else "degradado"

        return {
            "status": status,
            "datasets": {
                "signals": {
                    "count": counts["signals"],
                    "freshness": signal_fresh,
                    "minutes_ago": None if signal_min is None else round(signal_min, 1),
                    "last_update": latest_signal_ts.isoformat() if latest_signal_ts else None,
                },
                "outcomes": {
                    "count": counts["outcomes"],
                    "freshness": outcome_fresh,
                    "minutes_ago": None if outcome_min is None else round(outcome_min, 1),
                    "last_update": latest_outcome_ts.isoformat() if latest_outcome_ts else None,
                },
                "metrics": {
                    "count": counts["metrics"],
                    "freshness": metrics_fresh,
                    "minutes_ago": None if metrics_min is None else round(metrics_min, 1),
                    "last_update": latest_metrics_ts.isoformat() if latest_metrics_ts else None,
                },
            },
            "degraded_reasons": degraded_flags,
            "calculated_at": datetime.now(timezone.utc).isoformat(),
        }
