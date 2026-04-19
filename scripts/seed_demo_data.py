from __future__ import annotations

import random
from datetime import datetime, timedelta

from app.storage.db import PerformanceReport, ScoreSnapshot, SignalOutcome, get_session, init_db


def seed() -> None:
    init_db()

    now = datetime.utcnow()
    tokens = [
        ("So11111111111111111111111111111111111111112", "LONG_SETUP"),
        ("DezXAZ8z7PnrnRJjz3wXBoRgixCa6a7YaB1pPB263", "SHORT_SETUP"),
        ("EKpQGSJtjMFqKZ6aC8hQvA2tqZ5P5Y4H3x8nP9f1meme", "LONG_SETUP"),
        ("Fh3hFf3d3a2f9kLw9D3xQ8M9h2a1z0meme11111", "LONG_SETUP"),
        ("9xQeWvG816bUx9EPf8NfM6w2BeZ7FEfcYkgmeme2222", "SHORT_SETUP"),
    ]

    with get_session() as session:
        existing = session.query(ScoreSnapshot).count()
        if existing > 0:
            print("Demo data already exists. Skipping seed.")
            return

        score_ids: list[int] = []
        for i in range(80):
            token_address, decision = random.choice(tokens)
            ts = now - timedelta(minutes=15 * (80 - i))
            entry_price = round(random.uniform(0.00001, 0.01), 8)
            long_score = round(random.uniform(55, 92), 2)
            short_score = round(random.uniform(45, 90), 2)
            confidence = round(random.uniform(0.55, 0.92), 3)
            penalties = round(random.uniform(0, 12), 2)

            if decision == "SHORT_SETUP":
                short_score = max(short_score, 70)
            else:
                long_score = max(long_score, 70)

            row = ScoreSnapshot(
                token_address=token_address,
                ts=ts,
                entry_price=entry_price,
                long_score=long_score,
                short_score=short_score,
                confidence=confidence,
                penalties=penalties,
                veto=False,
                decision=decision,
                reasons_json={
                    "top_positive": [["momentum", 0.78], ["liquidity_quality", 0.69], ["wallet_flow", 0.64]],
                    "top_risks": [["overextension", 0.41], ["distribution_signal", 0.38]],
                    "penalties": penalties,
                    "veto_reasons": [],
                },
                features_json={
                    "momentum": round(random.uniform(0.4, 0.95), 3),
                    "technical_structure": round(random.uniform(0.35, 0.9), 3),
                    "volume_acceleration": round(random.uniform(0.2, 0.95), 3),
                    "wallet_flow": round(random.uniform(0.2, 0.9), 3),
                },
            )
            session.add(row)
            session.flush()
            score_ids.append(row.id)

        for sid in score_ids:
            for horizon in ["1h", "4h", "24h"]:
                ret = random.uniform(-12, 18)
                session.add(
                    SignalOutcome(
                        score_snapshot_id=sid,
                        horizon=horizon,
                        ret_pct=round(ret, 3),
                        max_fav_excursion=round(max(ret, 0) + random.uniform(0.1, 2.5), 3),
                        max_adv_excursion=round(max(-ret, 0) + random.uniform(0.1, 2.5), 3),
                    )
                )

        for i in range(24):
            ts = now - timedelta(hours=24 - i)
            for horizon in ["1h", "4h", "24h"]:
                win_rate = random.uniform(0.42, 0.71)
                avg_win = random.uniform(2.2, 7.5)
                avg_loss = -random.uniform(1.4, 4.8)
                expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
                session.add(
                    PerformanceReport(
                        ts=ts,
                        horizon=horizon,
                        n_signals=random.randint(40, 140),
                        win_rate=round(win_rate, 4),
                        avg_win=round(avg_win, 3),
                        avg_loss=round(avg_loss, 3),
                        expectancy=round(expectancy, 3),
                        precision_top_decile=round(random.uniform(0.5, 0.86), 4),
                        max_drawdown_proxy=round(-random.uniform(4, 23), 3),
                        sharpe_proxy=round(random.uniform(0.2, 1.8), 3),
                    )
                )

        session.commit()

    print("Demo seed inserted: score_snapshots, signal_outcomes, performance_reports")


if __name__ == "__main__":
    seed()
