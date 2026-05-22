import os, uuid, json, aiofiles, pathlib
from fastapi import APIRouter, UploadFile, File, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List

from models.schemas import DocumentResponse, DocumentList
from services.pdf_processor import process_pdf, get_pdf_metadata
from services.claude_service import summarize_document

router = APIRouter()

UPLOAD_DIR = pathlib.Path(os.getenv("UPLOAD_DIR", "./data/uploads"))
MAX_MB     = int(os.getenv("MAX_UPLOAD_MB", 50))
DOCS_INDEX = UPLOAD_DIR.parent / "docs_index.json"

_docs: dict[str, dict] = {}


def _save_index():
    DOCS_INDEX.parent.mkdir(parents=True, exist_ok=True)
    with open(DOCS_INDEX, "w", encoding="utf-8") as f:
        json.dump(_docs, f, ensure_ascii=False)


def _load_index():
    global _docs
    if DOCS_INDEX.exists():
        with open(DOCS_INDEX, "r", encoding="utf-8") as f:
            _docs = json.load(f)


_load_index()


def _vs(request: Request):
    return request.app.state.vs


# ── Subir PDF ────────────────────────────────────────────────
@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(request: Request, file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Solo se aceptan archivos PDF")

    content = await file.read()
    if len(content) > MAX_MB * 1024 * 1024:
        raise HTTPException(413, f"Archivo demasiado grande (máx {MAX_MB} MB)")

    doc_id   = str(uuid.uuid4())
    filename = file.filename
    dest     = UPLOAD_DIR / f"{doc_id}.pdf"

    async with aiofiles.open(dest, "wb") as f:
        await f.write(content)

    # Procesar PDF e indexar
    try:
        result = process_pdf(str(dest), doc_id, filename)
    except Exception as e:
        dest.unlink(missing_ok=True)
        raise HTTPException(422, f"No se pudo procesar el PDF: {str(e)}")

    if result["total_chunks"] == 0:
        dest.unlink(missing_ok=True)
        raise HTTPException(
            422,
            "El PDF no contiene texto extraíble. Puede ser un documento escaneado (solo imágenes). "
            "Intenta con un PDF que tenga texto seleccionable.",
        )

    vs = _vs(request)
    vs.add_chunks(result["chunks"])

    doc = {
        "id":           doc_id,
        "filename":     filename,
        "pages":        result["pages"],
        "size_kb":      result["size_kb"],
        "total_chunks": result["total_chunks"],
        "summary":      None,
    }
    _docs[doc_id] = doc
    _save_index()
    return DocumentResponse(**doc)


# ── Listar documentos ────────────────────────────────────────
@router.get("/", response_model=DocumentList)
def list_documents(request: Request):
    docs = list(_docs.values())
    return DocumentList(documents=[DocumentResponse(**d) for d in docs],
                        total=len(docs))


# ── Detalle de documento ─────────────────────────────────────
@router.get("/{doc_id}", response_model=DocumentResponse)
def get_document(doc_id: str):
    doc = _docs.get(doc_id)
    if not doc:
        raise HTTPException(404, "Documento no encontrado")
    return DocumentResponse(**doc)


# ── Eliminar documento ───────────────────────────────────────
@router.delete("/{doc_id}", status_code=204)
def delete_document(doc_id: str, request: Request):
    doc = _docs.get(doc_id)
    if not doc:
        raise HTTPException(404, "Documento no encontrado")

    # Eliminar de vectorstore
    _vs(request).delete_document(doc_id)

    # Eliminar archivo físico
    pdf_path = UPLOAD_DIR / f"{doc_id}.pdf"
    if pdf_path.exists():
        pdf_path.unlink()

    del _docs[doc_id]
    _save_index()


# ── Generar resumen ──────────────────────────────────────────
@router.post("/{doc_id}/summarize")
def summarize_doc(doc_id: str, request: Request):
    doc = _docs.get(doc_id)
    if not doc:
        raise HTTPException(404, "Documento no encontrado")

    vs      = _vs(request)
    results = vs.search(query="resumen contenido principal", top_k=20,
                        doc_ids=[doc_id])
    chunks_text = " ".join(r["text"] for r in results)
    summary     = summarize_document(chunks_text, doc["filename"])

    _docs[doc_id]["summary"] = summary
    _save_index()
    return {"doc_id": doc_id, "summary": summary}


# ── Buscar en documento específico ──────────────────────────
@router.get("/{doc_id}/search")
def search_in_document(doc_id: str, q: str, request: Request, top_k: int = 5):
    if not q:
        raise HTTPException(400, "Parámetro 'q' requerido")
    if doc_id not in _docs:
        raise HTTPException(404, "Documento no encontrado")

    results = _vs(request).search(q, top_k=top_k, doc_ids=[doc_id])
    return {"query": q, "results": results}
