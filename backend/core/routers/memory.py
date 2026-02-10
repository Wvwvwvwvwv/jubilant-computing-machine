from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

class MemoryItem(BaseModel):
    content: str
    metadata: Optional[dict] = None

class SearchRequest(BaseModel):
    query: str
    limit: int = 10

@router.post("/add")
async def add_memory(item: MemoryItem, req: Request):
    """Добавить элемент в память"""
    
    memory_engine = req.app.state.memory_engine
    
    try:
        memory_id = await memory_engine.add_memory(
            content=item.content,
            metadata=item.metadata
        )
        return {"id": memory_id, "status": "added"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search")
async def search_memory(search: SearchRequest, req: Request):
    """Поиск в памяти"""
    
    memory_engine = req.app.state.memory_engine
    
    try:
        results = await memory_engine.search(
            query=search.query,
            limit=search.limit
        )
        return {"results": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{memory_id}")
async def delete_memory(memory_id: str, req: Request):
    """Удалить элемент из памяти"""
    
    memory_engine = req.app.state.memory_engine
    
    try:
        await memory_engine.delete_memory(memory_id)
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=404, detail="Память не найдена")

@router.get("/stats")
async def memory_stats(req: Request):
    """Статистика памяти"""
    
    memory_engine = req.app.state.memory_engine
    
    try:
        stats = await memory_engine.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
