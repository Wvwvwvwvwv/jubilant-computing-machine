from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import asyncio
import os
import uvicorn

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_IMPORT_ERROR = None
except Exception as e:
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_IMPORT_ERROR = str(e)

app = FastAPI(
    title="Roampal Embeddings Service",
    description="Сервис генерации эмбеддингов",
    version="1.0.0"
)

model = None
model_loading = False
model_error = None
MODEL_NAME = os.getenv("EMBEDDINGS_MODEL", "all-MiniLM-L6-v2")


async def _load_model():
    global model, model_loading, model_error

    if SentenceTransformer is None:
        model_error = f"sentence-transformers import failed: {SENTENCE_TRANSFORMERS_IMPORT_ERROR}"
        model_loading = False
        return

    try:
        model_loading = True
        model_error = None
        model = await asyncio.to_thread(SentenceTransformer, MODEL_NAME)
        print(f"✅ Embeddings model loaded: {MODEL_NAME}")
    except Exception as e:
        model = None
        model_error = str(e)
        print(f"⚠️ Failed to load embeddings model '{MODEL_NAME}': {e}")
    finally:
        model_loading = False


@app.on_event("startup")
async def startup():
    asyncio.create_task(_load_model())


class EmbedRequest(BaseModel):
    texts: List[str]


class EmbedResponse(BaseModel):
    embeddings: List[List[float]]
    model: str
    dimension: int


@app.post("/embed", response_model=EmbedResponse)
async def embed_texts(request: EmbedRequest):
    """Генерация эмбеддингов для текстов"""

    if not model:
        detail = "Model not loaded"
        if model_loading:
            detail = "Model is still loading"
        elif model_error:
            detail = f"Model unavailable: {model_error}"
        raise HTTPException(status_code=503, detail=detail)

    try:
        embeddings = model.encode(
            request.texts,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

        return EmbedResponse(
            embeddings=embeddings.tolist(),
            model=MODEL_NAME,
            dimension=embeddings.shape[1],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    return {
        "service": "Roampal Embeddings",
        "status": "running",
        "model": MODEL_NAME,
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "model": MODEL_NAME,
        "error": model_error,
        "loading": model_loading,
        "sentence_transformers_available": SentenceTransformer is not None,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
