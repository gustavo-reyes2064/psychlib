from fastapi import APIRouter, HTTPException, Request
from models.schemas import ChatRequest, ChatResponse, SearchRequest, SearchResponse, SearchResult, Source

router = APIRouter()

# Historial en memoria por sesión (clave = session_id)
_sessions: dict[str, list] = {}


def _vs(request: Request):
    return request.app.state.vs


# ── Chat con RAG ─────────────────────────────────────────────
@router.post("/", response_model=ChatResponse)
def chat(payload: ChatRequest, request: Request):
    session_id = payload.session_id or "default"
    history    = _sessions.get(session_id, [])

    # RAG: recuperar fragmentos relevantes
    doc_ids = payload.doc_ids if payload.doc_ids else None
    sources_raw = _vs(request).search(
        query=payload.message,
        top_k=5,
        doc_ids=doc_ids,
    )

    # Importar aquí para evitar ciclos
    from services.claude_service import chat as claude_chat

    result = claude_chat(
        message=payload.message,
        history=history,
        sources=sources_raw,
        mode=payload.mode,
    )

    # Actualizar historial
    history.append({"role": "user",      "content": payload.message})
    history.append({"role": "assistant", "content": result["answer"]})
    _sessions[session_id] = history[-20:]   # Mantener últimos 20

    sources = [
        Source(
            doc_id=s["doc_id"],
            filename=s["filename"],
            page=s["page"],
            text=s["text"][:300],
            score=s["score"],
        )
        for s in sources_raw
    ]

    return ChatResponse(
        answer=result["answer"],
        sources=sources,
        tokens_used=result["tokens_used"],
        mode=payload.mode,
        session_id=session_id,
    )


# ── Búsqueda semántica pura ───────────────────────────────────
@router.post("/search", response_model=SearchResponse)
def semantic_search(payload: SearchRequest, request: Request):
    doc_ids = payload.doc_ids if payload.doc_ids else None
    raw = _vs(request).search(
        query=payload.query,
        top_k=payload.top_k or 5,
        doc_ids=doc_ids,
    )
    results = [
        SearchResult(
            doc_id=r["doc_id"],
            filename=r["filename"],
            page=r["page"],
            text=r["text"],
            score=r["score"],
        )
        for r in raw
    ]
    return SearchResponse(query=payload.query, results=results)


# ── Limpiar historial de sesión ───────────────────────────────
@router.delete("/session/{session_id}", status_code=204)
def clear_session(session_id: str):
    _sessions.pop(session_id, None)


# ── Listar modos disponibles ──────────────────────────────────
@router.get("/modes")
def list_modes():
    return {
        "modes": [
            {"id": "general",      "label": "General",           "description": "Asistente académico de psiquiatría"},
            {"id": "diagnostico",  "label": "Diagnóstico",       "description": "Diagnóstico diferencial educativo DSM-5"},
            {"id": "dsm5",         "label": "DSM-5 / CIE-11",    "description": "Criterios diagnósticos precisos"},
            {"id": "farmacologia", "label": "Farmacología",      "description": "Psicofarmacología y mecanismos"},
            {"id": "caso",         "label": "Caso Clínico",      "description": "Análisis de casos clínicos educativos"},
            {"id": "psicopatologia", "label": "Psicopatología",  "description": "Fenómenos psicopatológicos, semiología y psicopatología descriptiva"},
        ]
    }
