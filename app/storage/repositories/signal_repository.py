from datetime import datetime

from sqlalchemy import and_, desc, select

from app.storage.db import AlertSent, PerformanceReport, ScoreSnapshot, SignalOutcome, get_session


class SignalRepository:
    def save_score_snapshot(
        self,
        token_address: str,
        entry_price: float,
        long_score: float,
        short_score: float,
        confidence: float,
        penalties: float,
        veto: bool,
        decision: str,
        reasons_json: dict,
        features_json: dict,
    ) -> int:
        with get_session() as session:
            row = ScoreSnapshot(
                token_address=token_address,
                ts=datetime.utcnow(),
                entry_price=entry_price,
                long_score=long_score,
                short_score=short_score,
                confidence=confidence,
                penalties=penalties,
                veto=veto,
                decision=decision,
                reasons_json=reasons_json,
                features_json=features_json,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return row.id

    def latest_signals(self, limit: int = 50) -> list[ScoreSnapshot]:
        with get_session() as session:
            stmt = select(ScoreSnapshot).order_by(desc(ScoreSnapshot.ts)).limit(limit)
            return list(session.scalars(stmt).all())

    def latest_top(self, decision: str, limit: int = 10) -> list[ScoreSnapshot]:
        with get_session() as session:
            order_by_col = ScoreSnapshot.long_score if decision == "LONG_SETUP" else ScoreSnapshot.short_score
            stmt = (
                select(ScoreSnapshot)
                .where(ScoreSnapshot.decision == decision)
                .order_by(desc(order_by_col), desc(ScoreSnapshot.ts))
                .limit(limit)
            )
            return list(session.scalars(stmt).all())

    def token_signal_history(self, token_address: str, limit: int = 200) -> list[ScoreSnapshot]:
        with get_session() as session:
            stmt = (
                select(ScoreSnapshot)
                .where(ScoreSnapshot.token_address == token_address)
                .order_by(ScoreSnapshot.ts.desc())
                .limit(limit)
            )
            return list(session.scalars(stmt).all())

    def save_alert(self, token_address: str, decision: str, message_hash: str, channel: str = "telegram") -> None:
        with get_session() as session:
            session.add(
                AlertSent(
                    token_address=token_address,
                    ts=datetime.utcnow(),
                    decision=decision,
                    channel=channel,
                    message_hash=message_hash,
                )
            )
            session.commit()

    def has_recent_alert(self, token_address: str, decision: str, not_before: datetime) -> bool:
        with get_session() as session:
            stmt = (
                select(AlertSent.id)
                .where(
                    and_(
                        AlertSent.token_address == token_address,
                        AlertSent.decision == decision,
                        AlertSent.ts >= not_before,
                    )
                )
                .limit(1)
            )
            return session.scalar(stmt) is not None

    def has_outcome(self, score_snapshot_id: int, horizon: str) -> bool:
        with get_session() as session:
            stmt = (
                select(SignalOutcome.id)
                .where(
                    and_(
                        SignalOutcome.score_snapshot_id == score_snapshot_id,
                        SignalOutcome.horizon == horizon,
                    )
                )
                .limit(1)
            )
            return session.scalar(stmt) is not None

    def first_snapshot_after(self, token_address: str, ts: datetime) -> ScoreSnapshot | None:
        with get_session() as session:
            stmt = (
                select(ScoreSnapshot)
                .where(and_(ScoreSnapshot.token_address == token_address, ScoreSnapshot.ts >= ts))
                .order_by(ScoreSnapshot.ts.asc())
                .limit(1)
            )
            return session.scalars(stmt).first()

    def snapshots_in_window(self, token_address: str, start_ts: datetime, end_ts: datetime) -> list[ScoreSnapshot]:
        with get_session() as session:
            stmt = (
                select(ScoreSnapshot)
                .where(
                    and_(
                        ScoreSnapshot.token_address == token_address,
                        ScoreSnapshot.ts >= start_ts,
                        ScoreSnapshot.ts <= end_ts,
                    )
                )
                .order_by(ScoreSnapshot.ts.asc())
            )
            return list(session.scalars(stmt).all())

    def latest_outcomes(self, limit: int = 100) -> list[SignalOutcome]:
        with get_session() as session:
            stmt = select(SignalOutcome).order_by(desc(SignalOutcome.id)).limit(limit)
            return list(session.scalars(stmt).all())

    def outcomes_with_scores(self, horizon: str, limit: int = 1000) -> list[dict]:
        with get_session() as session:
            signal_score = ScoreSnapshot.long_score
            stmt = (
                select(SignalOutcome, ScoreSnapshot)
                .join(ScoreSnapshot, ScoreSnapshot.id == SignalOutcome.score_snapshot_id)
                .where(SignalOutcome.horizon == horizon)
                .order_by(desc(SignalOutcome.id))
                .limit(limit)
            )
            rows = session.execute(stmt).all()
            out: list[dict] = []
            for outcome, score in rows:
                if score.decision == "SHORT_SETUP":
                    signal_score = score.short_score
                else:
                    signal_score = score.long_score
                out.append(
                    {
                        "score_snapshot_id": outcome.score_snapshot_id,
                        "horizon": outcome.horizon,
                        "ret_pct": outcome.ret_pct,
                        "signal_score": signal_score,
                        "decision": score.decision,
                    }
                )
            return out

    def save_performance_report(
        self,
        horizon: str,
        n_signals: int,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        expectancy: float,
        precision_top_decile: float,
        max_drawdown_proxy: float,
        sharpe_proxy: float,
    ) -> None:
        with get_session() as session:
            session.add(
                PerformanceReport(
                    ts=datetime.utcnow(),
                    horizon=horizon,
                    n_signals=n_signals,
                    win_rate=win_rate,
                    avg_win=avg_win,
                    avg_loss=avg_loss,
                    expectancy=expectancy,
                    precision_top_decile=precision_top_decile,
                    max_drawdown_proxy=max_drawdown_proxy,
                    sharpe_proxy=sharpe_proxy,
                )
            )
            session.commit()

    def latest_performance_reports(self, limit: int = 100) -> list[PerformanceReport]:
        with get_session() as session:
            stmt = select(PerformanceReport).order_by(desc(PerformanceReport.id)).limit(limit)
            return list(session.scalars(stmt).all())
