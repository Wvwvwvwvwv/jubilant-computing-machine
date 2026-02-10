import httpx
from typing import List, Dict

class KoboldClient:
    """Клиент для KoboldCpp API"""
    
    def __init__(self, base_url: str = "http://localhost:5001"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def generate(
        self,
        messages: List[Dict],
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 40
    ) -> str:
        """Генерация текста через KoboldCpp"""
        
        # Форматирование сообщений в промпт
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
    
    def _format_messages(self, messages: List[Dict]) -> str:
        """Форматирование сообщений в промпт"""
        
        formatted = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
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
        except:
            return False
    
    async def close(self):
        await self.client.aclose()
