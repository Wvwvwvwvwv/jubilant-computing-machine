from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from backend.core.routers import books, chat, companion, memory, sandbox, tasks, voice
from backend.core.services.memory_engine import MemoryEngine
from backend.core.services.task_runner import TaskRunner
from backend.core.services.companion_state import CompanionState
from backend.core.services.companion_memory import CompanionMemory
from backend.core.services.voice_state import VoiceState


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.memory_engine = MemoryEngine()
    app.state.task_runner = TaskRunner()
    app.state.task_runner.load_state()
    app.state.companion_state = CompanionState()
    app.state.companion_memory = CompanionMemory()
    app.state.voice_state = VoiceState()
    await app.state.memory_engine.initialize()
    yield
    # Shutdown
    app.state.task_runner.save_state()
    await app.state.memory_engine.close()


app = FastAPI(
    title="Roampal Core API",
    description="Оркестратор для локального AI ассистента",
    version="1.0.0",
    lifespan=lifespan,
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
app.include_router(companion.router, prefix="/api/companion", tags=["companion"])
app.include_router(voice.router, prefix="/api/voice", tags=["voice"])


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
            "companion": "/api/companion",
            "voice": "/api/voice",
            "docs": "/docs",
        },
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
