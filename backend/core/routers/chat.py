from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List

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


def serialize_messages(messages: List[ChatMessage]) -> List[dict]:
    """Pydantic model -> plain dict для совместимости с KoboldClient."""
    serialized = []
    for m in messages:
        if hasattr(m, "model_dump"):
            serialized.append(m.model_dump())  # pydantic v2
        else:
            serialized.append(m.dict())  # pydantic v1 (Termux профиль)
    return serialized


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, req: Request):
    """Чат с LLM через KoboldCpp с использованием памяти Roampal"""

    if not request.messages:
        raise HTTPException(status_code=400, detail="messages не может быть пустым")

    memory_engine: MemoryEngine = req.app.state.memory_engine
    context_items = 0
    memory_context = []
    query_text = request.messages[-1].content

    # Получение релевантного контекста из памяти
    if request.use_memory:
        memory_context = await memory_engine.search(query_text, limit=5)
        context_items = len(memory_context)

        # Добавление контекста в промпт
        if memory_context:
            context_text = "\n\n".join([
                f"[Память {i + 1}]: {item['content']}"
                for i, item in enumerate(memory_context)
            ])

            # Вставка контекста перед последним сообщением
            system_msg = ChatMessage(
                role="system",
                content=f"Релевантный контекст из памяти:\n{context_text}",
            )
            request.messages.insert(-1, system_msg)

    # Отправка в KoboldCpp
    try:
        response = await kobold.generate(
            messages=serialize_messages(request.messages),
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )

        # Сохранение в память для будущего обучения
        if request.use_memory:
            await memory_engine.add_interaction(
                query=query_text,
                response=response,
                context_used=memory_context,
            )

        return ChatResponse(
            response=response,
            memory_used=request.use_memory,
            context_items=context_items,
        )

    except Exception as e:
        detail = str(e)
        status = 503 if "KoboldCpp error" in detail else 500
        raise HTTPException(status_code=status, detail=f"Ошибка генерации: {detail}")


@router.post("/feedback")
async def feedback(
    interaction_id: str,
    helpful: bool,
    req: Request,
):
    """Обратная связь для outcome-based learning"""

    memory_engine: MemoryEngine = req.app.state.memory_engine

    try:
        await memory_engine.record_outcome(
            interaction_id=interaction_id,
            helpful=helpful,
        )
        return {"status": "success", "message": "Обратная связь записана"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
