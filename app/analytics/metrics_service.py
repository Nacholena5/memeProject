from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

from app.storage.repositories.signal_repository import SignalRepository


@dataclass
class MetricsSnapshot:
    horizon: str
    n_signals: int
    win_rate: float
    avg_win: float
    avg_loss: float
    expectancy: float
    precision_top_decile: float
    max_drawdown_proxy: float
    sharpe_proxy: float


class MetricsService:
    def __init__(self, repo: SignalRepository | None = None) -> None:
        self._repo = repo or SignalRepository()

    @staticmethod
    def _max_drawdown_proxy(returns: list[float]) -> float:
        if not returns:
            return 0.0
        eq = 1.0
        peak = 1.0
        max_dd = 0.0
        for ret_pct in returns:
            eq *= 1.0 + (ret_pct / 100.0)
            peak = max(peak, eq)
            dd = (eq / peak) - 1.0
            max_dd = min(max_dd, dd)
        return max_dd * 100.0

    @staticmethod
    def _sharpe_proxy(returns: list[float]) -> float:
        if len(returns) < 2:
            return 0.0
        mean = sum(returns) / len(returns)
        variance = sum((x - mean) ** 2 for x in returns) / (len(returns) - 1)
        std = sqrt(max(variance, 1e-12))
        return mean / std

    def compute_for_horizon(self, horizon: str, min_rows: int = 30) -> MetricsSnapshot | None:
        rows = self._repo.outcomes_with_scores(horizon=horizon, limit=10_000)
        if len(rows) < min_rows:
            return None

        returns = [float(row["ret_pct"]) for row in rows]
        wins = [r for r in returns if r > 0]
        losses = [r for r in returns if r <= 0]

        n = len(returns)
        win_rate = (len(wins) / n) if n else 0.0
        avg_win = sum(wins) / len(wins) if wins else 0.0
        avg_loss = sum(losses) / len(losses) if losses else 0.0
        expectancy = (win_rate * avg_win) + ((1.0 - win_rate) * avg_loss)

        ranked = sorted(rows, key=lambda x: float(x["signal_score"]), reverse=True)
        top_cut = max(1, int(len(ranked) * 0.1))
        top_rows = ranked[:top_cut]
        top_wins = sum(1 for row in top_rows if float(row["ret_pct"]) > 0)
        precision_top_decile = top_wins / len(top_rows)

        max_dd_proxy = self._max_drawdown_proxy(returns)
        sharpe_proxy = self._sharpe_proxy(returns)

        return MetricsSnapshot(
            horizon=horizon,
            n_signals=n,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            expectancy=expectancy,
            precision_top_decile=precision_top_decile,
            max_drawdown_proxy=max_dd_proxy,
            sharpe_proxy=sharpe_proxy,
        )

    def compute_all(self, horizons: list[str]) -> list[MetricsSnapshot]:
        out: list[MetricsSnapshot] = []
        for horizon in horizons:
            snap = self.compute_for_horizon(horizon)
            if snap is not None:
                out.append(snap)
        return out
