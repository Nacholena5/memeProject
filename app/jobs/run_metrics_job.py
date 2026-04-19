from app.analytics.metrics_service import MetricsService
from app.config import get_settings
from app.storage.repositories.signal_repository import SignalRepository


class MetricsJob:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._repo = SignalRepository()
        self._service = MetricsService(self._repo)

    def run(self) -> None:
        horizons = [h.strip() for h in self._settings.outcome_horizons.split(",") if h.strip()]
        snapshots = self._service.compute_all(horizons)
        for snap in snapshots:
            self._repo.save_performance_report(
                horizon=snap.horizon,
                n_signals=snap.n_signals,
                win_rate=snap.win_rate,
                avg_win=snap.avg_win,
                avg_loss=snap.avg_loss,
                expectancy=snap.expectancy,
                precision_top_decile=snap.precision_top_decile,
                max_drawdown_proxy=snap.max_drawdown_proxy,
                sharpe_proxy=snap.sharpe_proxy,
            )
