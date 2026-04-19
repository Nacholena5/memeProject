from app.config import get_settings
from app.scoring.score_model import ScoreResult


def decide_signal(score: ScoreResult, shortable: bool) -> str:
    settings = get_settings()

    if score.confidence < settings.min_confidence:
        return "IGNORE"

    long_ok = score.long_score >= settings.long_threshold
    short_ok = shortable and score.short_score >= settings.short_threshold

    if long_ok and short_ok:
        return "LONG_SETUP" if score.long_score >= score.short_score else "SHORT_SETUP"
    if long_ok:
        return "LONG_SETUP"
    if short_ok:
        return "SHORT_SETUP"

    return "IGNORE"
