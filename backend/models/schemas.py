from pydantic import BaseModel, Field
from typing import Optional, List, Any


# ── Documentos ──────────────────────────────────────────────────────────────
class DocumentResponse(BaseModel):
    id: str
    filename: str
    pages: int
    size_kb: float
    total_chunks: int
    summary: Optional[str] = None


class DocumentList(BaseModel):
    documents: List[DocumentResponse]
    total: int


# ── Chat ─────────────────────────────────────────────────────────────────────
class ChatMessage(BaseModel):
    role: str       # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    doc_ids: Optional[List[str]] = None   # None = toda la biblioteca
    mode: str = "general"                 # general | diagnostico | dsm5 | farmacologia | caso


class Source(BaseModel):
    doc_id: str
    filename: str
    page: int
    text: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: List[Source] = []
    tokens_used: int = 0
    mode: str = "general"
    session_id: str = "default"


# ── Búsqueda semántica ────────────────────────────────────────────────────────
class SearchRequest(BaseModel):
    query: str
    doc_ids: Optional[List[str]] = None
    top_k: int = Field(default=5, ge=1, le=20)


class SearchResult(BaseModel):
    doc_id: str
    filename: str
    page: int
    text: str
    score: float


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]


# ── Casos Clínicos ────────────────────────────────────────────────────────────
class CaseCreate(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None        # M | F | NB
    chief_complaint: str
    history: str = ""
    symptoms: List[str] = []
    mental_status: Optional[str] = None


class SourceRef(BaseModel):
    filename: str
    page: int
    score: float


class CaseResponse(BaseModel):
    id: str
    age: Optional[int] = None
    gender: Optional[str] = None
    chief_complaint: str
    history: str = ""
    symptoms: List[str] = []
    mental_status: Optional[str] = None
    analysis: Optional[str] = None
    sources_used: List[SourceRef] = []


class CaseList(BaseModel):
    cases: List[CaseResponse]
    total: int


# ── Diagnóstico diferencial ───────────────────────────────────────────────────
class DiagnosticRequest(BaseModel):
    symptoms: List[str]
    history: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    duration: Optional[str] = None


class Criterion(BaseModel):
    code: str
    description: str
    met: Optional[bool] = None


class DiagnosticResult(BaseModel):
    diagnosis: str
    dsm5_code: str
    probability: str        # Alta | Media | Baja
    criteria_met: List[Criterion] = []
    differential: List[str] = []
    notes: str = ""


class DiagnosticResponse(BaseModel):
    results: List[DiagnosticResult]
    disclaimer: str = (
        "Este análisis es exclusivamente educativo. "
        "No reemplaza evaluación clínica profesional."
    )
