import hashlib
from typing import List

import httpx


class EmbeddingsClient:
    """Клиент для сервиса эмбеддингов с локальным fallback."""

    def __init__(self, base_url: str = "http://localhost:8001", fallback_dimension: int = 384):
        self.base_url = base_url
        self.fallback_dimension = fallback_dimension
        self.client = httpx.AsyncClient(timeout=30.0)

    def _fallback_embedding(self, text: str) -> List[float]:
        seed = hashlib.sha256(text.encode("utf-8")).digest()
        vector = []

        for idx in range(self.fallback_dimension):
            byte = seed[idx % len(seed)]
            vector.append((byte / 255.0) * 2 - 1)

        return vector

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Получить эмбеддинги для текстов (или fallback при недоступности сервиса)."""

        try:
            response = await self.client.post(
                f"{self.base_url}/embed",
                json={"texts": texts}
            )
            response.raise_for_status()

            result = response.json()
            return result["embeddings"]

        except Exception:
            return [self._fallback_embedding(text) for text in texts]

    async def check_health(self) -> bool:
        """Проверка доступности сервиса."""

        try:
            response = await self.client.get(f"{self.base_url}/health")
            if response.status_code != 200:
                return False

            data = response.json()
            return bool(data.get("model_loaded", False) and data.get("status") == "healthy")
        except Exception:
            return False

    async def close(self):
        await self.client.aclose()
