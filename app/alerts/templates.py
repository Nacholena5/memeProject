from app.scoring.score_model import ScoreResult


def render_signal_message(symbol: str, address: str, decision: str, score: ScoreResult) -> str:
    pos = ", ".join([f"{k}:{v:.2f}" for k, v in score.reasons.get("top_positive", [])])
    risks = ", ".join([f"{k}:{v:.2f}" for k, v in score.reasons.get("top_risks", [])])

    return (
        f"{decision} | {symbol}\\n"
        f"addr: {address}\\n"
        f"long: {score.long_score:.1f} | short: {score.short_score:.1f} | conf: {score.confidence:.2f}\\n"
        f"penalties: {score.penalties:.1f}\\n"
        f"drivers: {pos}\\n"
        f"risks: {risks}"
    )
