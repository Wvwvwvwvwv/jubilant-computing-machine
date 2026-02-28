from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from pathlib import Path
import aiofiles
import hashlib
import re
from html import unescape
import xml.etree.ElementTree as ET
from typing import Optional, Tuple

router = APIRouter()

BOOKS_DIR = Path.home() / "roampal-android" / "data" / "books"
BOOKS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".txt", ".md", ".html", ".htm", ".fb2", ".pdf"}
MAX_CHUNK_SIZE = 1800


def _split_text(text: str, chunk_size: int = MAX_CHUNK_SIZE):
    text = text.strip()
    if not text:
        return []
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


def _extract_text(content: bytes, suffix: str) -> Tuple[str, Optional[str]]:
    suffix = suffix.lower()

    if suffix in {".txt", ".md"}:
        return content.decode("utf-8", errors="ignore"), None

    if suffix in {".html", ".htm"}:
        raw = content.decode("utf-8", errors="ignore")
        raw = re.sub(r"<script[^>]*>.*?</script>", " ", raw, flags=re.IGNORECASE | re.DOTALL)
        raw = re.sub(r"<style[^>]*>.*?</style>", " ", raw, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", raw)
        return re.sub(r"\s+", " ", unescape(text)).strip(), None

    if suffix == ".fb2":
        xml_text = content.decode("utf-8", errors="ignore")
        root = ET.fromstring(xml_text)
        chunks = []
        for node in root.iter():
            if node.text and node.text.strip():
                chunks.append(node.text.strip())
        return "\n".join(chunks).strip(), None

    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except Exception:
            return "", "PDF parser unavailable (install pypdf==4.3.1)"

        from io import BytesIO
        try:
            reader = PdfReader(BytesIO(content))
            chunks = []
            for page in reader.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    chunks.append(page_text.strip())
            text = "\n\n".join(chunks).strip()
            if not text:
                return "", "PDF uploaded, but no extractable text found (possibly scanned/image PDF)"
            return text, None
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Некорректный PDF: {e}")

    raise HTTPException(status_code=400, detail=f"Неподдерживаемый формат: {suffix}")


@router.post("/upload")
async def upload_book(file: UploadFile = File(...), req: Request = None):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise HTTPException(status_code=400, detail=f"Поддерживаются форматы: {allowed}")

    content = await file.read()
    extracted, warning = _extract_text(content, suffix)

    file_hash = hashlib.md5(content).hexdigest()[:8]
    safe_filename = f"{file_hash}_{file.filename}"
    file_path = BOOKS_DIR / safe_filename

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    memory_items = 0
    if req is not None and hasattr(req.app.state, "memory_engine"):
        memory_engine = req.app.state.memory_engine
        for idx, chunk in enumerate(_split_text(extracted)):
            await memory_engine.add_memory(
                content=chunk,
                metadata={"type": "book", "book_id": file_hash, "filename": file.filename, "chunk_index": idx, "source_format": suffix},
            )
            memory_items += 1

    response = {
        "id": file_hash,
        "filename": file.filename,
        "size": len(content),
        "text_length": len(extracted),
        "memory_items": memory_items,
        "status": "uploaded",
    }
    if warning:
        response["warning"] = warning
    return response


@router.get("/list")
async def list_books():
    books = []
    for file_path in BOOKS_DIR.glob("*"):
        if file_path.is_file():
            stat = file_path.stat()
            books.append(
                {
                    "id": file_path.stem.split("_")[0],
                    "filename": "_".join(file_path.stem.split("_")[1:]) + file_path.suffix,
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                }
            )
    return {"books": books, "count": len(books)}


@router.delete("/{book_id}")
async def delete_book(book_id: str):
    for file_path in BOOKS_DIR.glob(f"{book_id}_*"):
        file_path.unlink()
        return {"status": "deleted", "id": book_id}
    raise HTTPException(status_code=404, detail="Книга не найдена")


@router.get("/{book_id}/content")
async def get_book_content(book_id: str):
    for file_path in BOOKS_DIR.glob(f"{book_id}_*"):
        async with aiofiles.open(file_path, "rb") as f:
            content = await f.read()
        text, warning = _extract_text(content, file_path.suffix)
        response = {"id": book_id, "filename": file_path.name, "content": text}
        if warning:
            response["warning"] = warning
        return response
    raise HTTPException(status_code=404, detail="Книга не найдена")
