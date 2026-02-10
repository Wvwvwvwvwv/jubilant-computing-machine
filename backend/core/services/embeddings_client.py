import httpx
from typing import List

class EmbeddingsClient:
    """Клиент для сервиса эмбеддингов"""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Получить эмбеддинги для текстов"""
        
        try:
            response = await self.client.post(
                f"{self.base_url}/embed",
                json={"texts": texts}
            )
            response.raise_for_status()
            
            result = response.json()
            return result["embeddings"]
            
        except httpx.HTTPError as e:
            raise Exception(f"Embeddings service error: {str(e)}")
    
    async def check_health(self) -> bool:
        """Проверка доступности сервиса"""
        
        try:
            response = await self.client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False
    
    async def close(self):
        await self.client.aclose()
