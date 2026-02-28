from pathlib import Path
import uuid
from typing import List, Dict, Optional
import time
import os
import json

try:
    import chromadb
    from chromadb.config import Settings
except Exception:
    chromadb = None
    Settings = None


class MemoryEngine:
    """Roampal-inspired outcome-based memory engine"""

    def __init__(self):
        data_dir_env = os.getenv("ROAMPAL_MEMORY_DIR")
        self.data_dir = Path(data_dir_env) if data_dir_env else Path.home() / "roampal-android" / "data" / "memory"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.client = None
        self.collection = None
        self.interactions = {}  # interaction_id -> metadata

        self.chroma_available = chromadb is not None
        self.in_memory_store: Dict[str, Dict] = {}
        self.fallback_store_path = self.data_dir / "in_memory_store.json"

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
                self.chroma_available = False

        self.client = None
        self.collection = None

        self._load_fallback_store()

    def _load_fallback_store(self):
        """Загрузить in-memory fallback из файла при старте."""

        if not self.fallback_store_path.exists():
            return

        try:
            payload = json.loads(self.fallback_store_path.read_text(encoding="utf-8"))
            store = payload.get("in_memory_store", {})
            if isinstance(store, dict):
                self.in_memory_store = store
        except Exception:
            # Не ломаем startup из-за поврежденного fallback файла
            self.in_memory_store = {}

    def _save_fallback_store(self):
        """Сохранить fallback память на диск (для переживания рестартов)."""

        if self.chroma_available and self.collection is not None:
            return

        try:
            self.fallback_store_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"in_memory_store": self.in_memory_store}
            self.fallback_store_path.write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8"
            )
        except Exception:
            # Fallback persistence best-effort
            pass

    async def add_memory(self, content: str, metadata: Optional[Dict] = None) -> str:
        """Добавить элемент в память"""

        memory_id = str(uuid.uuid4())
        meta = metadata or {}

        if self.chroma_available and self.collection is not None:
            self.collection.add(documents=[content], ids=[memory_id], metadatas=[meta])
            return memory_id

        self.in_memory_store[memory_id] = {
            "id": memory_id,
            "content": content,
            "metadata": meta,
            "timestamp": time.time(),
            "outcome_score": meta.get("outcome_score", 0.0),
            "type": meta.get("type", "memory"),
        }
        self._save_fallback_store()
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
            self.collection.add(documents=[text], ids=[interaction_id], metadatas=[interaction_meta])
        else:
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

        self._save_fallback_store()
        return interaction_id

    async def record_outcome(self, interaction_id: str, helpful: bool):
        """Записать результат (outcome-based learning)"""

        if self.chroma_available and self.collection is not None:
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

        self._save_fallback_store()

    async def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Поиск с учетом outcome scores"""

        if self.chroma_available and self.collection is not None:
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
            self.collection.delete(ids=[memory_id])
        else:
            self.in_memory_store.pop(memory_id, None)

        if memory_id in self.interactions:
            del self.interactions[memory_id]

        self._save_fallback_store()

    async def get_stats(self) -> Dict:
        """Статистика памяти"""

        if self.chroma_available and self.collection is not None:
            count = self.collection.count()
            all_items = self.collection.get()
            metadatas = all_items.get("metadatas") or []
            interactions = sum(1 for m in metadatas if isinstance(m, dict) and m.get("type") == "interaction")
            return {
                "total_items": count,
                "interactions": interactions,
                "permanent_memories": count - interactions,
                "backend": "chromadb",
            }

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
