from contextlib import asynccontextmanager, suppress
import asyncio
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from backend.core.routers import books, chat, companion, memory, retrieval, sandbox, tasks, voice
from backend.core.services.memory_engine import MemoryEngine
from backend.core.services.task_runner import TaskRunner
from backend.core.services.companion_state import CompanionState
from backend.core.services.companion_memory import CompanionMemory
from backend.core.services.voice_state import VoiceState
from backend.core.services.retrieval_jobs import RetrievalJobState


WORKER_INTERVAL_SECONDS = float(os.getenv("RETRIEVAL_WORKER_INTERVAL_SECONDS", "0.5"))
WORKER_BATCH_SIZE = int(os.getenv("RETRIEVAL_WORKER_BATCH_SIZE", "10"))


async def retrieval_worker_loop(job_state: RetrievalJobState, stop_event: asyncio.Event, pause_event: asyncio.Event):
    """Background worker that processes queued retrieval jobs."""
    while not stop_event.is_set():
        if not pause_event.is_set():
            job_state.process_pending_jobs(max_jobs=WORKER_BATCH_SIZE)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=WORKER_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            continue


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.memory_engine = MemoryEngine()
    app.state.task_runner = TaskRunner()
    app.state.task_runner.load_state()
    app.state.companion_state = CompanionState()
    app.state.companion_memory = CompanionMemory()
    app.state.voice_state = VoiceState()
    # Week-1 retrieval abstraction bootstrap: multimodal retriever can be injected later.
    app.state.multimodal_retriever = None
    app.state.retrieval_job_state = RetrievalJobState()
    app.state.retrieval_worker_stop = asyncio.Event()
    app.state.retrieval_worker_pause = asyncio.Event()
    app.state.retrieval_worker_interval_seconds = WORKER_INTERVAL_SECONDS
    app.state.retrieval_worker_batch_size = WORKER_BATCH_SIZE
    app.state.retrieval_worker_task = asyncio.create_task(
        retrieval_worker_loop(
            app.state.retrieval_job_state,
            app.state.retrieval_worker_stop,
            app.state.retrieval_worker_pause,
        )
    )
    await app.state.memory_engine.initialize()
    yield
    # Shutdown
    app.state.task_runner.save_state()
    app.state.retrieval_worker_stop.set()
    with suppress(asyncio.CancelledError):
        await app.state.retrieval_worker_task
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
app.include_router(retrieval.router, prefix="/api/retrieval", tags=["retrieval"])


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
            "retrieval": "/api/retrieval",
            "docs": "/docs",
        },
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
