from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import aiofiles
import hashlib
from typing import List

router = APIRouter()

BOOKS_DIR = Path.home() / "roampal-android" / "data" / "books"
BOOKS_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/upload")
async def upload_book(file: UploadFile = File(...)):
    """Загрузить книгу или текстовый файл"""
    
    if not file.filename.endswith(('.txt', '.md')):
        raise HTTPException(status_code=400, detail="Только .txt и .md файлы")
    
    try:
        # Генерация уникального ID
        content = await file.read()
        file_hash = hashlib.md5(content).hexdigest()[:8]
        
        # Сохранение файла
        safe_filename = f"{file_hash}_{file.filename}"
        file_path = BOOKS_DIR / safe_filename
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        return {
            "id": file_hash,
            "filename": file.filename,
            "size": len(content),
            "status": "uploaded"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list")
async def list_books():
    """Список всех книг"""
    
    books = []
    for file_path in BOOKS_DIR.glob("*"):
        if file_path.is_file():
            stat = file_path.stat()
            books.append({
                "id": file_path.stem.split("_")[0],
                "filename": "_".join(file_path.stem.split("_")[1:]) + file_path.suffix,
                "size": stat.st_size,
                "modified": stat.st_mtime
            })
    
    return {"books": books, "count": len(books)}

@router.delete("/{book_id}")
async def delete_book(book_id: str):
    """Удалить книгу"""
    
    # Поиск файла по ID
    for file_path in BOOKS_DIR.glob(f"{book_id}_*"):
        file_path.unlink()
        return {"status": "deleted", "id": book_id}
    
    raise HTTPException(status_code=404, detail="Книга не найдена")

@router.get("/{book_id}/content")
async def get_book_content(book_id: str):
    """Получить содержимое книги"""
    
    for file_path in BOOKS_DIR.glob(f"{book_id}_*"):
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()
        
        return {
            "id": book_id,
            "filename": file_path.name,
            "content": content
        }
    
    raise HTTPException(status_code=404, detail="Книга не найдена")
