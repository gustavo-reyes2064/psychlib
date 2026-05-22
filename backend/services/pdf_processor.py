import pdfplumber, pathlib, re
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os

CHUNK_SIZE    = int(os.getenv("CHUNK_SIZE", 1000))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 200))


def extract_text(pdf_path: str) -> List[Dict[str, Any]]:
    """Extrae texto página por página de un PDF."""
    pages = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                try:
                    text = page.extract_text() or ""
                except Exception:
                    text = ""
                text = re.sub(r'\s+', ' ', text).strip()
                if text:
                    pages.append({"page": i + 1, "text": text})
    except Exception as e:
        raise RuntimeError(f"No se pudo abrir el PDF. Puede estar dañado o protegido con contraseña. ({type(e).__name__})")
    return pages


def chunk_pages(pages: List[Dict[str, Any]], doc_id: str, filename: str) -> List[Dict[str, Any]]:
    """Divide páginas en chunks con metadata."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = []
    for pg in pages:
        parts = splitter.split_text(pg["text"])
        for j, part in enumerate(parts):
            chunks.append({
                "id":       f"{doc_id}_p{pg['page']}_c{j}",
                "text":     part,
                "doc_id":   doc_id,
                "filename": filename,
                "page":     pg["page"],
                "chunk":    j,
            })
    return chunks


def get_pdf_metadata(pdf_path: str) -> Dict[str, Any]:
    """Obtiene metadata básica del PDF."""
    path = pathlib.Path(pdf_path)
    pages = 0
    with pdfplumber.open(pdf_path) as pdf:
        pages = len(pdf.pages)
    return {
        "pages":   pages,
        "size_kb": round(path.stat().st_size / 1024, 1),
    }


def process_pdf(pdf_path: str, doc_id: str, filename: str) -> Dict[str, Any]:
    """Pipeline completo: extraer → chunkar → retornar todo."""
    pages  = extract_text(pdf_path)
    chunks = chunk_pages(pages, doc_id, filename)
    meta   = get_pdf_metadata(pdf_path)
    return {
        "pages":   meta["pages"],
        "size_kb": meta["size_kb"],
        "chunks":  chunks,
        "total_chunks": len(chunks),
    }
