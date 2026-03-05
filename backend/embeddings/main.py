from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import asyncio
import hashlib
import os
import random
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
FALLBACK_DIMENSION = int(os.getenv("EMBEDDINGS_FALLBACK_DIM", "384"))


def deterministic_fallback_embedding(text: str, dim: int = FALLBACK_DIMENSION) -> List[float]:
    """Deterministic pseudo-embedding for degraded mode."""

    normalized = (text or "").strip().lower()
    if not normalized:
        return [0.0] * dim

    seed = int(hashlib.sha256(normalized.encode("utf-8")).hexdigest(), 16) % (2**32)
    rng = random.Random(seed)
    vector = [rng.uniform(-1.0, 1.0) for _ in range(dim)]

    # L2 normalization for more stable cosine-like behavior.
    norm = sum(v * v for v in vector) ** 0.5
    if norm == 0:
        return [0.0] * dim
    return [v / norm for v in vector]


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
    fallback_active: bool = False


@app.post("/embed", response_model=EmbedResponse)
async def embed_texts(request: EmbedRequest):
    """Генерация эмбеддингов для текстов"""

    if model:
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
                fallback_active=False,
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # Degraded mode: deterministic fallback keeps API available for memory flows.
    fallback_vectors = [deterministic_fallback_embedding(text) for text in request.texts]
    return EmbedResponse(
        embeddings=fallback_vectors,
        model=f"{MODEL_NAME}::fallback",
        dimension=FALLBACK_DIMENSION,
        fallback_active=True,
    )


@app.get("/")
async def root():
    return {
        "service": "Roampal Embeddings",
        "status": "running",
        "model": MODEL_NAME,
    }


@app.get("/health")
async def health():
    fallback_active = model is None
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "model": MODEL_NAME,
        "error": model_error,
        "loading": model_loading,
        "sentence_transformers_available": SentenceTransformer is not None,
        "fallback_active": fallback_active,
        "fallback_dimension": FALLBACK_DIMENSION if fallback_active else None,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
