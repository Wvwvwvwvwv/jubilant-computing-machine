import chromadb
from chromadb.config import Settings
from pathlib import Path
import uuid
from typing import List, Dict, Optional
import time

class MemoryEngine:
    """Roampal-inspired outcome-based memory engine"""
    
    def __init__(self):
        self.data_dir = Path.home() / "roampal-android" / "data" / "memory"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.client = None
        self.collection = None
        self.interactions = {}  # interaction_id -> metadata
    
    async def initialize(self):
        """Инициализация ChromaDB"""
        
        self.client = chromadb.PersistentClient(
            path=str(self.data_dir),
            settings=Settings(anonymized_telemetry=False)
        )
        
        self.collection = self.client.get_or_create_collection(
            name="roampal_memory",
            metadata={"hnsw:space": "cosine"}
        )
    
    async def add_memory(
        self,
        content: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """Добавить элемент в память"""
        
        memory_id = str(uuid.uuid4())
        
        self.collection.add(
            documents=[content],
            ids=[memory_id],
            metadatas=[metadata or {}]
        )
        
        return memory_id
    
    async def add_interaction(
        self,
        query: str,
        response: str,
        context_used: List[Dict]
    ) -> str:
        """Сохранить взаимодействие для outcome learning"""
        
        interaction_id = str(uuid.uuid4())
        
        # Сохранение в ChromaDB
        self.collection.add(
            documents=[f"Q: {query}\nA: {response}"],
            ids=[interaction_id],
            metadatas=[{
                "type": "interaction",
                "timestamp": time.time(),
                "outcome_score": 0.0,  # Будет обновлено при feedback
                "context_ids": [c.get("id") for c in context_used]
            }]
        )
        
        # Кэширование для быстрого доступа
        self.interactions[interaction_id] = {
            "query": query,
            "response": response,
            "context_used": context_used,
            "timestamp": time.time()
        }
        
        return interaction_id
    
    async def record_outcome(
        self,
        interaction_id: str,
        helpful: bool
    ):
        """Записать результат (outcome-based learning)"""
        
        # Получение текущего документа
        result = self.collection.get(ids=[interaction_id])
        
        if not result["ids"]:
            raise ValueError("Interaction not found")
        
        metadata = result["metadatas"][0]
        
        # Обновление score по алгоритму Roampal
        current_score = metadata.get("outcome_score", 0.0)
        
        if helpful:
            new_score = min(1.0, current_score + 0.2)  # Boost
        else:
            new_score = max(-1.0, current_score - 0.3)  # Penalty
        
        # Обновление метаданных
        metadata["outcome_score"] = new_score
        metadata["last_feedback"] = time.time()
        
        self.collection.update(
            ids=[interaction_id],
            metadatas=[metadata]
        )
        
        # Автоудаление плохих результатов
        if new_score < -0.5:
            await self.delete_memory(interaction_id)
    
    async def search(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict]:
        """Поиск с учетом outcome scores"""
        
        # Поиск с большим лимитом для ре-ранжирования
        results = self.collection.query(
            query_texts=[query],
            n_results=limit * 3
        )
        
        if not results["ids"][0]:
            return []
        
        # Ре-ранжирование по outcome_score
        scored_results = []
        for i, doc_id in enumerate(results["ids"][0]):
            metadata = results["metadatas"][0][i]
            document = results["documents"][0][i]
            distance = results["distances"][0][i]
            
            outcome_score = metadata.get("outcome_score", 0.0)
            
            # Комбинированный score: similarity + outcome
            combined_score = (1 - distance) * 0.6 + (outcome_score + 1) * 0.4
            
            scored_results.append({
                "id": doc_id,
                "content": document,
                "score": combined_score,
                "outcome_score": outcome_score,
                "metadata": metadata
            })
        
        # Сортировка и возврат топ-N
        scored_results.sort(key=lambda x: x["score"], reverse=True)
        return scored_results[:limit]
    
    async def delete_memory(self, memory_id: str):
        """Удалить элемент из памяти"""
        
        self.collection.delete(ids=[memory_id])
        
        if memory_id in self.interactions:
            del self.interactions[memory_id]
    
    async def get_stats(self) -> Dict:
        """Статистика памяти"""
        
        count = self.collection.count()
        
        # Подсчет по типам
        all_items = self.collection.get()
        
        interactions = sum(
            1 for m in all_items["metadatas"]
            if m.get("type") == "interaction"
        )
        
        return {
            "total_items": count,
            "interactions": interactions,
            "permanent_memories": count - interactions
        }
    
    async def close(self):
        """Закрытие соединения"""
        pass  # ChromaDB автоматически сохраняет
