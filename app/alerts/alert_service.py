import hashlib
from datetime import datetime, timedelta

from app.alerts.templates import render_signal_message
from app.clients.telegram_client import TelegramClient
from app.config import get_settings
from app.scoring.score_model import ScoreResult
from app.storage.repositories.signal_repository import SignalRepository


class AlertService:
    def __init__(self, repo: SignalRepository) -> None:
        self._repo = repo
        self._settings = get_settings()
        self._telegram = TelegramClient(self._settings.telegram_bot_token) if self._settings.telegram_bot_token else None

    async def emit_if_enabled(self, symbol: str, address: str, decision: str, score: ScoreResult) -> None:
        if decision == "IGNORE":
            return

        dedupe_cutoff = datetime.utcnow() - timedelta(minutes=self._settings.alert_dedupe_minutes)
        if self._repo.has_recent_alert(address, decision, dedupe_cutoff):
            return

        message = render_signal_message(symbol, address, decision, score)
        msg_hash = hashlib.sha256(message.encode("utf-8")).hexdigest()

        if self._telegram and self._settings.telegram_chat_id:
            await self._telegram.send_message(self._settings.telegram_chat_id, message)

        self._repo.save_alert(token_address=address, decision=decision, message_hash=msg_hash)
