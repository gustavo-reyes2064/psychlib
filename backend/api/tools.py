import json, pathlib, os
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

DATA_DIR = pathlib.Path(os.getenv("UPLOAD_DIR", "./data/uploads")).parent
HISTORY_FILE = DATA_DIR / "search_history.json"

_history: list = []


def _load_history():
    global _history
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            _history = json.load(f)


def _save_history():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(_history[-200:], f, ensure_ascii=False)


_load_history()


def _vs(request: Request):
    return request.app.state.vs


# ── Drug Interactions ────────────────────────────────────────
class InteractionRequest(BaseModel):
    drugs: List[str]
    patient_context: Optional[str] = None


@router.post("/interactions")
def check_interactions(payload: InteractionRequest, request: Request):
    from services.claude_service import check_drug_interactions

    vs = _vs(request)
    query = "interacciones farmacológicas " + " ".join(payload.drugs)
    sources = vs.search(query=query, top_k=10)
    chunks_text = "\n\n".join(
        f"[{s['filename']} p.{s['page']}] {s['text']}" for s in sources
    )

    result = check_drug_interactions(payload.drugs, chunks_text, payload.patient_context)
    return {"drugs": payload.drugs, "analysis": result}


# ── Scale Interpretation ─────────────────────────────────────
class ScaleRequest(BaseModel):
    scale_name: str
    total_score: int
    item_scores: List[int] = []
    patient_context: Optional[str] = None


@router.post("/scales/interpret")
def interpret_scale(payload: ScaleRequest, request: Request):
    from services.claude_service import interpret_scale_result

    vs = _vs(request)
    query = f"escala {payload.scale_name} interpretación puntuación"
    sources = vs.search(query=query, top_k=8)
    chunks_text = "\n\n".join(
        f"[{s['filename']} p.{s['page']}] {s['text']}" for s in sources
    )

    result = interpret_scale_result(
        payload.scale_name, payload.total_score,
        payload.item_scores, chunks_text, payload.patient_context
    )
    return {
        "scale": payload.scale_name,
        "score": payload.total_score,
        "interpretation": result,
    }


# ── DSM-5 vs CIE-11 Comparator ──────────────────────────────
class CompareRequest(BaseModel):
    disorder: str


@router.post("/compare")
def compare_dsm_cie(payload: CompareRequest, request: Request):
    from services.claude_service import compare_classifications

    vs = _vs(request)
    sources = vs.search(
        query=f"{payload.disorder} criterios diagnósticos DSM-5 CIE-11",
        top_k=15
    )
    chunks_text = "\n\n".join(
        f"[{s['filename']} p.{s['page']}] {s['text']}" for s in sources
    )

    result = compare_classifications(payload.disorder, chunks_text)

    entry = {"type": "compare", "query": payload.disorder}
    _history.append(entry)
    _save_history()

    return {"disorder": payload.disorder, "comparison": result}


# ── Chapter Summaries ────────────────────────────────────────
class ChapterRequest(BaseModel):
    doc_id: str
    chapter_query: str


@router.post("/chapter-summary")
def chapter_summary(payload: ChapterRequest, request: Request):
    from services.claude_service import summarize_chapter

    vs = _vs(request)
    sources = vs.search(
        query=payload.chapter_query, top_k=20,
        doc_ids=[payload.doc_id]
    )
    if not sources:
        raise HTTPException(404, "No se encontraron fragmentos para ese capítulo")

    chunks_text = "\n\n".join(
        f"[p.{s['page']}] {s['text']}" for s in sources
    )
    filename = sources[0]["filename"] if sources else "documento"

    result = summarize_chapter(chunks_text, payload.chapter_query, filename)

    entry = {"type": "chapter", "query": payload.chapter_query, "doc_id": payload.doc_id}
    _history.append(entry)
    _save_history()

    return {
        "chapter": payload.chapter_query,
        "summary": result,
        "pages_covered": sorted(set(s["page"] for s in sources)),
    }


# ── Search History ───────────────────────────────────────────
@router.get("/history")
def get_history():
    return {"history": list(reversed(_history[-50:]))}


@router.delete("/history", status_code=204)
def clear_history():
    global _history
    _history = []
    _save_history()
