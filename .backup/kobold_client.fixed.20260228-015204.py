import httpx
from typing import Any, List

class KoboldClient:
    """Клиент для KoboldCpp API"""

    def __init__(self, base_url: str = "http://localhost:5001"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=120.0)

    async def generate(
        self,
        messages: List[Any],
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 40
    ) -> str:
        """Генерация текста через KoboldCpp"""

        prompt = self._format_messages(messages)

        payload = {
            "prompt": prompt,
            "max_length": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "rep_pen": 1.1,
            "stop_sequence": ["</s>", "User:", "Assistant:"]
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/generate",
                json=payload
            )
            response.raise_for_status()

            result = response.json()
            return result["results"][0]["text"].strip()

        except httpx.HTTPError as e:
            raise Exception(f"KoboldCpp error: {str(e)}")

    @staticmethod
    def _msg_field(msg: Any, field: str, default: str = "") -> str:
        """Безопасно получить поле сообщения из dict или Pydantic-модели."""
        if isinstance(msg, dict):
            value = msg.get(field, default)
        else:
            value = getattr(msg, field, default)
        return value if isinstance(value, str) else str(value)

    def _format_messages(self, messages: List[Any]) -> str:
        """Форматирование сообщений в промпт"""

        formatted = []
        for msg in messages:
            role = self._msg_field(msg, "role", "user")
            content = self._msg_field(msg, "content", "")

            if role == "system":
                formatted.append(f"System: {content}")
            elif role == "user":
                formatted.append(f"User: {content}")
            elif role == "assistant":
                formatted.append(f"Assistant: {content}")

        formatted.append("Assistant:")
        return "\n\n".join(formatted)

    async def check_health(self) -> bool:
        """Проверка доступности KoboldCpp"""

        try:
            response = await self.client.get(f"{self.base_url}/api/v1/model")
            return response.status_code == 200
        except Exception:
            return False

    async def close(self):
        await self.client.aclose()
