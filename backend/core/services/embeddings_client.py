import httpx
from typing import List

class EmbeddingsClient:
    """Клиент для сервиса эмбеддингов"""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Получить эмбеддинги для текстов"""
        if not texts:
            return []
        
        try:
            response = await self.client.post(
                f"{self.base_url}/embed",
                json={"texts": texts}
            )
            response.raise_for_status()
            
            result = response.json()
            return result["embeddings"]
            
        except httpx.HTTPError:
            # Fallback для деградации без падения core-сервиса
            return self._fallback_embeddings(len(texts))

    @staticmethod
    def _fallback_embeddings(size: int, dim: int = 384) -> List[List[float]]:
        """Детерминированный fallback: нулевые векторы стандартной размерности."""
        return [[0.0] * dim for _ in range(size)]
    
    async def check_health(self) -> bool:
        """Проверка доступности сервиса"""
        
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False

    async def health_details(self) -> dict:
        """Детальная health-диагностика для логирования/диагноза."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            data = response.json()
            data["reachable"] = True
            return data
        except Exception as e:
            return {"reachable": False, "status": "unhealthy", "error": str(e)}
    
    async def close(self):
        await self.client.aclose()
