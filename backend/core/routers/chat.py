from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
import httpx

from services.kobold_client import KoboldClient
from services.memory_engine import MemoryEngine

router = APIRouter()
kobold = KoboldClient()

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    use_memory: bool = True
    max_tokens: int = 512
    temperature: float = 0.7

class ChatResponse(BaseModel):
    response: str
    memory_used: bool
    context_items: int
    interaction_id: Optional[str] = None

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, req: Request):
    """Чат с LLM через KoboldCpp с использованием памяти Roampal"""
    
    memory_engine: MemoryEngine = req.app.state.memory_engine
    context_items = 0
    memory_context = []
    
    # Получение релевантного контекста из памяти
    if request.use_memory and len(request.messages) > 0:
        last_message = request.messages[-1].content
        memory_context = await memory_engine.search(last_message, limit=5)
        context_items = len(memory_context)
        
        # Добавление контекста в промпт
        if memory_context:
            context_text = "\n\n".join([
                f"[Память {i+1}]: {item['content']}"
                for i, item in enumerate(memory_context)
            ])
            
            # Вставка контекста перед последним сообщением
            system_msg = ChatMessage(
                role="system",
                content=f"Релевантный контекст из памяти:\n{context_text}"
            )
            request.messages.insert(-1, system_msg)
    
    # Отправка в KoboldCpp
    try:
        response = await kobold.generate(
            messages=request.messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )

        interaction_id = None

        # Сохранение в память для будущего обучения
        if request.use_memory and request.messages:
            interaction_id = await memory_engine.add_interaction(
                query=request.messages[-1].content,
                response=response,
                context_used=memory_context
            )

        return ChatResponse(
            response=response,
            memory_used=request.use_memory,
            context_items=context_items,
            interaction_id=interaction_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка генерации: {str(e)}")

@router.post("/feedback")
async def feedback(
    interaction_id: str,
    helpful: bool,
    req: Request
):
    """Обратная связь для outcome-based learning"""
    
    memory_engine: MemoryEngine = req.app.state.memory_engine
    
    try:
        await memory_engine.record_outcome(
            interaction_id=interaction_id,
            helpful=helpful
        )
        return {"status": "success", "message": "Обратная связь записана"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
