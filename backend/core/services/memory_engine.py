from pathlib import Path
import uuid
from typing import List, Dict, Optional
import time

try:
    import chromadb
    from chromadb.config import Settings
except Exception:
    chromadb = None
    Settings = None


class MemoryEngine:
    """Roampal-inspired outcome-based memory engine"""

    def __init__(self):
        self.data_dir = Path.home() / "roampal-android" / "data" / "memory"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.client = None
        self.collection = None
        self.interactions = {}  # interaction_id -> metadata

        self.chroma_available = chromadb is not None
        self.in_memory_store: Dict[str, Dict] = {}

    def _switch_to_in_memory(self):
        """Отключить ChromaDB и продолжить работу на in-memory backend."""

        self.chroma_available = False
        self.client = None
        self.collection = None

    async def initialize(self):
        """Инициализация ChromaDB или fallback на in-memory store"""

        if self.chroma_available:
            try:
                self.client = chromadb.PersistentClient(
                    path=str(self.data_dir),
                    settings=Settings(anonymized_telemetry=False),
                )

                self.collection = self.client.get_or_create_collection(
                    name="roampal_memory",
                    metadata={"hnsw:space": "cosine"},
                )
                return
            except Exception:
                # fallback на in-memory, если Chroma не поднимается
                self._switch_to_in_memory()

        self.client = None
        self.collection = None

    async def add_memory(self, content: str, metadata: Optional[Dict] = None) -> str:
        """Добавить элемент в память"""

        memory_id = str(uuid.uuid4())
        meta = metadata or {}

        if self.chroma_available and self.collection is not None:
            try:
                self.collection.add(documents=[content], ids=[memory_id], metadatas=[meta])
                return memory_id
            except Exception:
                self._switch_to_in_memory()

        self.in_memory_store[memory_id] = {
            "id": memory_id,
            "content": content,
            "metadata": meta,
            "timestamp": time.time(),
            "outcome_score": meta.get("outcome_score", 0.0),
            "type": meta.get("type", "memory"),
        }
        return memory_id

    async def add_interaction(self, query: str, response: str, context_used: List[Dict]) -> str:
        """Сохранить взаимодействие для outcome learning"""

        interaction_id = str(uuid.uuid4())
        interaction_meta = {
            "type": "interaction",
            "timestamp": time.time(),
            "outcome_score": 0.0,
            "context_ids": [c.get("id") for c in context_used],
        }

        text = f"Q: {query}\nA: {response}"

        if self.chroma_available and self.collection is not None:
            try:
                self.collection.add(documents=[text], ids=[interaction_id], metadatas=[interaction_meta])
            except Exception:
                self._switch_to_in_memory()

        if not (self.chroma_available and self.collection is not None):
            self.in_memory_store[interaction_id] = {
                "id": interaction_id,
                "content": text,
                "metadata": interaction_meta,
                "timestamp": interaction_meta["timestamp"],
                "outcome_score": 0.0,
                "type": "interaction",
            }

        self.interactions[interaction_id] = {
            "query": query,
            "response": response,
            "context_used": context_used,
            "timestamp": time.time(),
        }

        return interaction_id

    async def record_outcome(self, interaction_id: str, helpful: bool):
        """Записать результат (outcome-based learning)"""

        if self.chroma_available and self.collection is not None:
            try:
                result = self.collection.get(ids=[interaction_id])
                if not result["ids"]:
                    raise ValueError("Interaction not found")

                metadata = result["metadatas"][0]
                current_score = metadata.get("outcome_score", 0.0)

                new_score = min(1.0, current_score + 0.2) if helpful else max(-1.0, current_score - 0.3)

                metadata["outcome_score"] = new_score
                metadata["last_feedback"] = time.time()

                self.collection.update(ids=[interaction_id], metadatas=[metadata])

                if new_score < -0.5:
                    await self.delete_memory(interaction_id)
                return
            except ValueError:
                raise
            except Exception:
                self._switch_to_in_memory()

        item = self.in_memory_store.get(interaction_id)
        if not item:
            raise ValueError("Interaction not found")

        current_score = item.get("outcome_score", 0.0)
        new_score = min(1.0, current_score + 0.2) if helpful else max(-1.0, current_score - 0.3)
        item["outcome_score"] = new_score
        item.setdefault("metadata", {})["outcome_score"] = new_score
        item["metadata"]["last_feedback"] = time.time()

        if new_score < -0.5:
            await self.delete_memory(interaction_id)

    async def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Поиск с учетом outcome scores"""

        if self.chroma_available and self.collection is not None:
            try:
                results = self.collection.query(query_texts=[query], n_results=limit * 3)
                if not results["ids"] or not results["ids"][0]:
                    return []

                scored_results = []
                for i, doc_id in enumerate(results["ids"][0]):
                    metadata = results["metadatas"][0][i]
                    document = results["documents"][0][i]
                    distance = results["distances"][0][i]

                    outcome_score = metadata.get("outcome_score", 0.0)
                    combined_score = (1 - distance) * 0.6 + (outcome_score + 1) * 0.4

                    scored_results.append(
                        {
                            "id": doc_id,
                            "content": document,
                            "score": combined_score,
                            "outcome_score": outcome_score,
                            "metadata": metadata,
                        }
                    )

                scored_results.sort(key=lambda x: x["score"], reverse=True)
                return scored_results[:limit]
            except Exception:
                self._switch_to_in_memory()

        q_tokens = set(query.lower().split())
        scored_results = []

        for memory_id, item in self.in_memory_store.items():
            content = item.get("content", "")
            content_tokens = set(content.lower().split())
            overlap = len(q_tokens & content_tokens)

            text_score = overlap / max(1, len(q_tokens))
            outcome_score = item.get("outcome_score", 0.0)
            combined_score = text_score * 0.6 + (outcome_score + 1) * 0.4

            scored_results.append(
                {
                    "id": memory_id,
                    "content": content,
                    "score": combined_score,
                    "outcome_score": outcome_score,
                    "metadata": item.get("metadata", {}),
                }
            )

        scored_results.sort(key=lambda x: x["score"], reverse=True)
        return scored_results[:limit]

    async def delete_memory(self, memory_id: str):
        """Удалить элемент из памяти"""

        if self.chroma_available and self.collection is not None:
            try:
                self.collection.delete(ids=[memory_id])
            except Exception:
                self._switch_to_in_memory()

        if not (self.chroma_available and self.collection is not None):
            self.in_memory_store.pop(memory_id, None)

        if memory_id in self.interactions:
            del self.interactions[memory_id]

    async def get_stats(self) -> Dict:
        """Статистика памяти"""

        if self.chroma_available and self.collection is not None:
            try:
                count = self.collection.count()
                all_items = self.collection.get()
                interactions = sum(1 for m in all_items["metadatas"] if m.get("type") == "interaction")
                return {
                    "total_items": count,
                    "interactions": interactions,
                    "permanent_memories": count - interactions,
                    "backend": "chromadb",
                }
            except Exception:
                self._switch_to_in_memory()

        count = len(self.in_memory_store)
        interactions = sum(1 for item in self.in_memory_store.values() if item.get("type") == "interaction")
        return {
            "total_items": count,
            "interactions": interactions,
            "permanent_memories": count - interactions,
            "backend": "in_memory",
        }

    async def close(self):
        """Закрытие соединения"""
        pass
