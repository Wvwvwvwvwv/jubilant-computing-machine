from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from sentence_transformers import SentenceTransformer
import uvicorn

app = FastAPI(
    title="Roampal Embeddings Service",
    description="Сервис генерации эмбеддингов",
    version="1.0.0"
)

# Загрузка модели при старте
model = None

@app.on_event("startup")
async def startup():
    global model
    # Легковесная модель для мобильных устройств
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print("✅ Embeddings model loaded")

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
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        embeddings = model.encode(
            request.texts,
            convert_to_numpy=True,
            show_progress_bar=False
        )
        
        return EmbedResponse(
            embeddings=embeddings.tolist(),
            model="all-MiniLM-L6-v2",
            dimension=embeddings.shape[1]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {
        "service": "Roampal Embeddings",
        "status": "running",
        "model": "all-MiniLM-L6-v2"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "model_loaded": model is not None
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
