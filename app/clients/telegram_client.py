from app.clients.base_client import BaseHttpClient


class TelegramClient(BaseHttpClient):
    def __init__(self, bot_token: str) -> None:
        super().__init__(base_url=f"https://api.telegram.org/bot{bot_token}")

    async def send_message(self, chat_id: str, text: str) -> dict:
        return await self.post(
            "sendMessage",
            json_body={
                "chat_id": chat_id,
                "text": text,
                "disable_web_page_preview": True,
            },
        )
