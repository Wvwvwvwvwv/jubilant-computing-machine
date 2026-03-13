from pathlib import Path
import hashlib
import subprocess
import tempfile
from typing import List

import aiofiles
from fastapi import APIRouter, File, HTTPException, UploadFile

router = APIRouter()

BOOKS_DIR = Path.home() / "roampal-android" / "data" / "books"
BOOKS_DIR.mkdir(parents=True, exist_ok=True)


def _extract_pdf_text(content: bytes) -> str:
    try:
        from pypdf import PdfReader
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"PDF support недоступен: {exc}")

    import io

    reader = PdfReader(io.BytesIO(content))
    chunks = [(page.extract_text() or "") for page in reader.pages]
    extracted = "\n".join(chunks).strip()
    if extracted:
        return extracted

    # OCR fallback (best-effort) if text layer is missing.
    pdftoppm = shutil_which("pdftoppm")
    if not pdftoppm:
        raise HTTPException(
            status_code=400,
            detail="PDF не содержит текстовый слой, OCR недоступен (нужен pdftoppm)",
        )

    with tempfile.TemporaryDirectory() as td:
        pdf_path = Path(td) / "input.pdf"
        pdf_path.write_bytes(content)
        img_prefix = Path(td) / "page"

        proc = subprocess.run(
            [pdftoppm, "-png", str(pdf_path), str(img_prefix)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if proc.returncode != 0:
            raise HTTPException(status_code=500, detail=f"OCR conversion error: {proc.stderr.strip()}")

        texts: List[str] = []
        pytesseract = _try_import_pytesseract()
        for img in sorted(Path(td).glob("page-*.png")):
            text = _ocr_image(img, pytesseract)
            if text:
                texts.append(text)

        merged = "\n".join(texts).strip()
        if not merged:
            raise HTTPException(status_code=500, detail="OCR не смог извлечь текст из PDF")
        return merged


def shutil_which(name: str):
    import shutil

    return shutil.which(name)


def _try_import_pytesseract():
    try:
        import pytesseract  # type: ignore

        return pytesseract
    except Exception:
        return None


def _ocr_image(image_path: Path, pytesseract_mod) -> str:
    if pytesseract_mod is not None:
        try:
            from PIL import Image

            return pytesseract_mod.image_to_string(Image.open(image_path), lang="eng+rus").strip()
        except Exception:
            pass

    tesseract = shutil_which("tesseract")
    if not tesseract:
        return ""
    ocr = subprocess.run(
        [tesseract, str(image_path), "stdout", "-l", "eng+rus"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if ocr.returncode == 0:
        return ocr.stdout.strip()
    return ""


@router.post("/upload")
async def upload_book(file: UploadFile = File(...)):
    """Загрузить книгу или текстовый файл"""

    if not file.filename.lower().endswith((".txt", ".md", ".pdf")):
        raise HTTPException(status_code=400, detail="Только .txt, .md и .pdf файлы")

    try:
        content = await file.read()
        file_hash = hashlib.md5(content).hexdigest()[:8]

        incoming_name = file.filename
        if incoming_name.lower().endswith(".pdf"):
            extracted = _extract_pdf_text(content)
            content = extracted.encode("utf-8")
            incoming_name = incoming_name.rsplit(".", 1)[0] + ".txt"

        safe_filename = f"{file_hash}_{incoming_name}"
        file_path = BOOKS_DIR / safe_filename

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        return {
            "id": file_hash,
            "filename": incoming_name,
            "size": len(content),
            "status": "uploaded",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_books():
    """Список всех книг"""

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
    """Удалить книгу"""

    for file_path in BOOKS_DIR.glob(f"{book_id}_*"):
        file_path.unlink()
        return {"status": "deleted", "id": book_id}

    raise HTTPException(status_code=404, detail="Книга не найдена")


@router.get("/{book_id}/content")
async def get_book_content(book_id: str):
    """Получить содержимое книги"""

    for file_path in BOOKS_DIR.glob(f"{book_id}_*"):
        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
            content = await f.read()

        return {"id": book_id, "filename": file_path.name, "content": content}

    raise HTTPException(status_code=404, detail="Книга не найдена")
