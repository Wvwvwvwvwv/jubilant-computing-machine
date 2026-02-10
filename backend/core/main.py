from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from routers import chat, memory, books, sandbox
from services.memory_engine import MemoryEngine

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.memory_engine = MemoryEngine()
    await app.state.memory_engine.initialize()
    yield
    # Shutdown
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
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
