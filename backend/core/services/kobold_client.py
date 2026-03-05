import httpx
from typing import List, Dict, Any

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

        native_payload = {
            "prompt": prompt,
            "max_length": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "rep_pen": 1.1,
            "stop_sequence": ["</s>", "User:", "Assistant:"]
        }

        native_error = None
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/generate",
                json=native_payload,
            )
            response.raise_for_status()

            result = response.json()
            text = self._extract_text(result)
            if text:
                return text
            native_error = f"unexpected native response schema: {result}"

        except Exception as e:
            native_error = str(e)

        # Fallback: OpenAI-compatible completion endpoint.
        openai_payload = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stop": ["</s>", "User:", "Assistant:"],
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/v1/completions",
                json=openai_payload,
            )
            response.raise_for_status()
            result = response.json()
            text = self._extract_text(result)
            if text:
                return text
            raise Exception(f"unexpected OpenAI response schema: {result}")

        except Exception as e:
            raise Exception(
                "KoboldCpp generate failed on both endpoints: "
                f"native_error={native_error}; openai_error={e}"
            )

    def _extract_text(self, payload: Dict) -> str:
        """Извлечь текст из разных схем ответов Kobold/OpenAI-совместимых API."""

        if isinstance(payload, dict):
            results = payload.get("results")
            if isinstance(results, list) and results:
                text = results[0].get("text") if isinstance(results[0], dict) else None
                if isinstance(text, str):
                    return text.strip()

            choices = payload.get("choices")
            if isinstance(choices, list) and choices:
                first = choices[0]
                if isinstance(first, dict):
                    text = first.get("text")
                    if isinstance(text, str):
                        return text.strip()

                    message = first.get("message")
                    if isinstance(message, dict):
                        content = message.get("content")
                        if isinstance(content, str):
                            return content.strip()

        return ""
    
    def _format_messages(self, messages: List[Any]) -> str:
        """Форматирование сообщений в промпт"""
        
        formatted = []
        for msg in messages:
            if isinstance(msg, dict):
                role = msg.get("role", "user")
                content = msg.get("content", "")
            else:
                role = getattr(msg, "role", "user")
                content = getattr(msg, "content", "")
            
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
