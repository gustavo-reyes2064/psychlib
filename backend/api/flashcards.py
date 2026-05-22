import json, uuid, pathlib, os
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List

router = APIRouter()

DATA_DIR = pathlib.Path(os.getenv("UPLOAD_DIR", "./data/uploads")).parent
CARDS_FILE = DATA_DIR / "flashcards.json"
EXAMS_FILE = DATA_DIR / "exams.json"

_cards: dict[str, dict] = {}
_exams: dict[str, dict] = {}


def _load():
    global _cards, _exams
    if CARDS_FILE.exists():
        with open(CARDS_FILE, "r", encoding="utf-8") as f:
            _cards = json.load(f)
    if EXAMS_FILE.exists():
        with open(EXAMS_FILE, "r", encoding="utf-8") as f:
            _exams = json.load(f)


def _save_cards():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(CARDS_FILE, "w", encoding="utf-8") as f:
        json.dump(_cards, f, ensure_ascii=False)


def _save_exams():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(EXAMS_FILE, "w", encoding="utf-8") as f:
        json.dump(_exams, f, ensure_ascii=False)


_load()


def _vs(request: Request):
    return request.app.state.vs


# ── Schemas ──────────────────────────────────────────────────
class GenerateRequest(BaseModel):
    topic: str
    count: int = Field(default=10, ge=3, le=30)
    doc_ids: Optional[List[str]] = None


class ExamRequest(BaseModel):
    topic: str
    count: int = Field(default=10, ge=3, le=30)
    doc_ids: Optional[List[str]] = None


# ── Generate Flashcards ─────────────────────────────────────
@router.post("/generate")
def generate_flashcards(payload: GenerateRequest, request: Request):
    from services.claude_service import generate_flashcards as gen_cards

    vs = _vs(request)
    sources = vs.search(query=payload.topic, top_k=15, doc_ids=payload.doc_ids)
    chunks_text = "\n\n".join(
        f"[{s['filename']} p.{s['page']}] {s['text']}" for s in sources
    )

    cards = gen_cards(chunks_text, payload.topic, payload.count)
    cards = cards[:payload.count]

    deck_id = str(uuid.uuid4())
    deck = {
        "id": deck_id,
        "topic": payload.topic,
        "cards": cards,
        "total": len(cards),
    }
    _cards[deck_id] = deck
    _save_cards()
    return deck


# ── Generate Exam ────────────────────────────────────────────
@router.post("/exam/generate")
def generate_exam(payload: ExamRequest, request: Request):
    from services.claude_service import generate_exam as gen_exam

    vs = _vs(request)
    sources = vs.search(query=payload.topic, top_k=15, doc_ids=payload.doc_ids)
    chunks_text = "\n\n".join(
        f"[{s['filename']} p.{s['page']}] {s['text']}" for s in sources
    )

    questions = gen_exam(chunks_text, payload.topic, payload.count)
    questions = questions[:payload.count]

    exam_id = str(uuid.uuid4())
    exam = {
        "id": exam_id,
        "topic": payload.topic,
        "questions": questions,
        "total": len(questions),
    }
    _exams[exam_id] = exam
    _save_exams()
    return exam


# ── List saved decks ─────────────────────────────────────────
@router.get("/decks")
def list_decks():
    decks = [
        {"id": d["id"], "topic": d["topic"], "total": d["total"]}
        for d in _cards.values()
    ]
    return {"decks": decks}


# ── Get deck ─────────────────────────────────────────────────
@router.get("/decks/{deck_id}")
def get_deck(deck_id: str):
    deck = _cards.get(deck_id)
    if not deck:
        raise HTTPException(404, "Mazo no encontrado")
    return deck


# ── Delete deck ──────────────────────────────────────────────
@router.delete("/decks/{deck_id}", status_code=204)
def delete_deck(deck_id: str):
    if deck_id not in _cards:
        raise HTTPException(404, "Mazo no encontrado")
    del _cards[deck_id]
    _save_cards()


# ── List saved exams ─────────────────────────────────────────
@router.get("/exams")
def list_exams():
    exams = [
        {"id": e["id"], "topic": e["topic"], "total": e["total"]}
        for e in _exams.values()
    ]
    return {"exams": exams}


# ── Get exam ─────────────────────────────────────────────────
@router.get("/exams/{exam_id}")
def get_exam(exam_id: str):
    exam = _exams.get(exam_id)
    if not exam:
        raise HTTPException(404, "Examen no encontrado")
    return exam


# ── Delete exam ──────────────────────────────────────────────
@router.delete("/exams/{exam_id}", status_code=204)
def delete_exam(exam_id: str):
    if exam_id not in _exams:
        raise HTTPException(404, "Examen no encontrado")
    del _exams[exam_id]
    _save_exams()
