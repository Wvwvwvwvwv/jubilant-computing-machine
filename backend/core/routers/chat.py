from typing import List
import uuid

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.core.services.companion_memory import CompanionMemory
from backend.core.services.companion_state import CompanionState
from backend.core.services.kobold_client import KoboldClient
from backend.core.services.memory_engine import MemoryEngine
from backend.core.services.retrieval import LegacyMemoryRetriever, multimodal_rag_enabled

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


MAX_CHAT_HISTORY_MESSAGES = 14
MAX_MEMORY_CONTEXT_ITEMS = 3


def _normalize_text(text: str) -> str:
    return " ".join((text or "").split()).strip().lower()


def trim_chat_history(messages: List[ChatMessage], max_messages: int = MAX_CHAT_HISTORY_MESSAGES) -> List[ChatMessage]:
    """Keep recent history while preserving any system messages already injected."""
    if len(messages) <= max_messages:
        return messages

    system_msgs = [m for m in messages if m.role == "system"]
    non_system = [m for m in messages if m.role != "system"]
    keep_non_system = non_system[-max_messages:]
    return [*system_msgs, *keep_non_system]


def build_memory_context_block(items: list[dict], limit: int = MAX_MEMORY_CONTEXT_ITEMS) -> str:
    """Deduplicate noisy memory items and keep only compact relevant snippets."""
    filtered: list[str] = []
    seen: set[str] = set()
    for item in items:
        raw = str(item.get("content", "") or "").strip()
        if not raw:
            continue
        lowered = raw.lower()
        if "smoke memory item" in lowered or "system: answer to" in lowered:
            continue
        normalized = _normalize_text(raw)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        filtered.append(raw[:500])
        if len(filtered) >= limit:
            break

    return "\n\n".join([f"[Память {i + 1}]: {text}" for i, text in enumerate(filtered)])


def serialize_messages(messages: List[ChatMessage]) -> List[dict]:
    """Pydantic model -> plain dict для совместимости с KoboldClient."""
    serialized = []
    for m in messages:
        # pydantic v2
        if hasattr(m, "model_dump"):
            serialized.append(m.model_dump())
        else:
            # pydantic v1 (Termux legacy/runtime drift)
            serialized.append(m.dict())
    return serialized


def build_companion_behavior_message(session) -> ChatMessage:
    mode = session.reasoning_mode
    challenge = session.challenge_mode
    mode_clause = (
        "Режим STABLE: отвечай структурно, аккуратно, с явной маркировкой неопределённости."
        if mode == "stable"
        else "Режим WILD: предлагай смелые гипотезы, но маркируй их как требующие проверки."
    )

    if challenge == "strict":
        challenge_clause = "Обязательно приводи контрпозицию и проверяемые риски перед рекомендацией."
    elif challenge == "balanced":
        challenge_clause = "Если уместно, приводи краткую контрпозицию и ключевые риски."
    else:
        challenge_clause = "Не добавляй контрпозицию без явной необходимости."

    return ChatMessage(
        role="system",
        content=(
            "Политика поведения companion:\n"
            f"- {mode_clause}\n"
            f"- {challenge_clause}\n"
            "- Разделяй факты, гипотезы и неизвестное."
        ),
    )


def build_relationship_memory_message(facts: list[dict]) -> ChatMessage:
    lines = [f"[Fact {x['fact_id']}]: {x['fact']}" for x in facts]
    return ChatMessage(
        role="system",
        content=(
            "Память отношений (используй как персональные предпочтения пользователя, если релевантно):\n"
            + "\n".join(lines)
        ),
    )




async def search_memory_context(req: Request, memory_engine: MemoryEngine, query_text: str, limit: int = 8) -> tuple[list[dict], str]:
    """Resolve active retriever backend (legacy by default, multimodal by flag)."""
    if multimodal_rag_enabled():
        mm_retriever = getattr(req.app.state, "multimodal_retriever", None)
        if mm_retriever is not None and hasattr(mm_retriever, "search"):
            return await mm_retriever.search(query_text, limit=limit), "multimodal"

    legacy_retriever = LegacyMemoryRetriever(memory_engine)
    return await legacy_retriever.search(query_text, limit=limit), "legacy"

def infer_uncertainty_markers(text: str) -> list[str]:
    lowered = (text or "").lower()
    markers = []
    if any(x in lowered for x in ["не уверен", "недостаточно данных", "неизвестно", "uncertain"]):
        markers.append("insufficient_data")
    if any(x in lowered for x in ["гипотез", "предполож", "возможно", "likely"]):
        markers.append("hypothesis_present")
    return markers


@router.post("", response_model=ChatResponse)
@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, req: Request):
    """Чат с LLM через KoboldCpp с использованием памяти Roampal и companion-политик."""

    if not request.messages:
        raise HTTPException(status_code=400, detail="messages не может быть пустым")

    memory_engine: MemoryEngine = req.app.state.memory_engine
    companion_state: CompanionState | None = getattr(req.app.state, "companion_state", None)
    companion_memory: CompanionMemory | None = getattr(req.app.state, "companion_memory", None)

    context_items = 0
    memory_context = []
    retrieval_backend = "legacy"
    query_text = request.messages[-1].content
    working_messages = list(request.messages)
    used_relationship_ids: list[str] = []

    # Companion behavior policy injection (mode/challenge)
    if companion_state is not None:
        behavior_msg = build_companion_behavior_message(companion_state.get_session())
        working_messages.insert(0, behavior_msg)

    # Relationship memory injection (top active facts)
    if companion_memory is not None:
        relation_facts = companion_memory.list_facts(limit=3)
        if relation_facts:
            relation_payload = [{"fact_id": x.fact_id, "fact": x.fact} for x in relation_facts]
            used_relationship_ids = [x["fact_id"] for x in relation_payload]
            working_messages.insert(1 if companion_state is not None else 0, build_relationship_memory_message(relation_payload))

    # Получение релевантного контекста из памяти
    if request.use_memory:
        memory_context, retrieval_backend = await search_memory_context(req, memory_engine, query_text, limit=8)

        # Добавление контекста в промпт
        if memory_context:
            context_text = build_memory_context_block(memory_context, limit=MAX_MEMORY_CONTEXT_ITEMS)

            # Вставка контекста перед последним сообщением
            if context_text:
                system_msg = ChatMessage(
                    role="system",
                    content=f"Релевантный контекст из памяти ({retrieval_backend}):\n{context_text}",
                )
                working_messages.insert(-1, system_msg)
                context_items = context_text.count("[Память ")

    working_messages = trim_chat_history(working_messages)

    # Отправка в KoboldCpp
    try:
        response = await kobold.generate(
            messages=serialize_messages(working_messages),
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

        # Запись explainability trace в companion state
        if companion_state is not None:
            sess = companion_state.get_session()
            companion_state.set_last_trace(
                response_id=f"resp_{uuid.uuid4().hex[:12]}",
                retrieval_backend=retrieval_backend,
                relationship_used=used_relationship_ids,
                uncertainty_markers=infer_uncertainty_markers(response),
                counter_position_used=(sess.challenge_mode != "off"),
                confidence=0.72 if sess.reasoning_mode == "stable" else 0.64,
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
