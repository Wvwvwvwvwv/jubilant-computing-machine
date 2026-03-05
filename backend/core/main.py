from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from routers import chat, memory, books, sandbox, tasks
from services.memory_engine import MemoryEngine
from services.task_runner import TaskRunner
from services.state_db import StateDB

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.state_db = StateDB()
    app.state.state_db.initialize()
    app.state.memory_engine = MemoryEngine()
    app.state.task_runner = TaskRunner()
    app.state.task_runner.load_state()
    await app.state.memory_engine.initialize()
    yield
    # Shutdown
    app.state.task_runner.save_state()
    await app.state.memory_engine.close()

app = FastAPI(
    title="Roampal Core API",
    description="Оркестратор для локального AI ассистента",
    version="1.0.0",
    lifespan=lifespan
)

# CORS для frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Роутеры
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(memory.router, prefix="/api/memory", tags=["memory"])
app.include_router(books.router, prefix="/api/books", tags=["books"])
app.include_router(sandbox.router, prefix="/api/sandbox", tags=["sandbox"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])

@app.get("/")
async def root():
    return {
        "service": "Roampal Core API",
        "status": "running",
        "endpoints": {
            "chat": "/api/chat",
            "memory": "/api/memory",
            "books": "/api/books",
            "sandbox": "/api/sandbox",
            "tasks": "/api/tasks",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health():
    db_health = app.state.state_db.health() if hasattr(app.state, "state_db") else {"ok": False}
    return {
        "status": "healthy" if db_health.get("ok") else "degraded",
        "state_db": db_health,
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
