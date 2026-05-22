import uuid
from fastapi import APIRouter, HTTPException, Request
from models.schemas import CaseCreate, CaseResponse, CaseList

router = APIRouter()

# In-memory store (replace with SQLite/DB later)
_cases: dict[str, dict] = {}


def _vs(request: Request):
    return request.app.state.vs


# ── Crear caso ───────────────────────────────────────────────
@router.post("/", response_model=CaseResponse, status_code=201)
def create_case(payload: CaseCreate, request: Request):
    case_id = str(uuid.uuid4())

    # RAG: buscar fragmentos relevantes según síntomas + motivo
    query   = f"{payload.chief_complaint} {' '.join(payload.symptoms or [])}"
    sources = _vs(request).search(query=query, top_k=6)

    # Análisis con Claude
    from services.claude_service import analyze_case
    analysis = analyze_case(
        case_data={
            "age":             payload.age,
            "gender":          payload.gender,
            "chief_complaint": payload.chief_complaint,
            "history":         payload.history,
            "symptoms":        payload.symptoms or [],
            "mental_status":   payload.mental_status,
        },
        sources=sources,
    )

    case = {
        "id":              case_id,
        "age":             payload.age,
        "gender":          payload.gender,
        "chief_complaint": payload.chief_complaint,
        "history":         payload.history,
        "symptoms":        payload.symptoms or [],
        "mental_status":   payload.mental_status,
        "analysis":        analysis,
        "sources_used":    [
            {"filename": s["filename"], "page": s["page"], "score": s["score"]}
            for s in sources
        ],
    }
    _cases[case_id] = case
    return CaseResponse(**case)


# ── Listar casos ─────────────────────────────────────────────
@router.get("/", response_model=CaseList)
def list_cases():
    cases = list(_cases.values())
    return CaseList(cases=[CaseResponse(**c) for c in cases], total=len(cases))


# ── Obtener caso ─────────────────────────────────────────────
@router.get("/{case_id}", response_model=CaseResponse)
def get_case(case_id: str):
    case = _cases.get(case_id)
    if not case:
        raise HTTPException(404, "Caso no encontrado")
    return CaseResponse(**case)


# ── Actualizar caso ──────────────────────────────────────────
@router.put("/{case_id}", response_model=CaseResponse)
def update_case(case_id: str, payload: CaseCreate, request: Request):
    if case_id not in _cases:
        raise HTTPException(404, "Caso no encontrado")

    query   = f"{payload.chief_complaint} {' '.join(payload.symptoms or [])}"
    sources = _vs(request).search(query=query, top_k=6)

    from services.claude_service import analyze_case
    analysis = analyze_case(
        case_data={
            "age":             payload.age,
            "gender":          payload.gender,
            "chief_complaint": payload.chief_complaint,
            "history":         payload.history,
            "symptoms":        payload.symptoms or [],
            "mental_status":   payload.mental_status,
        },
        sources=sources,
    )

    updated = {
        "id":              case_id,
        "age":             payload.age,
        "gender":          payload.gender,
        "chief_complaint": payload.chief_complaint,
        "history":         payload.history,
        "symptoms":        payload.symptoms or [],
        "mental_status":   payload.mental_status,
        "analysis":        analysis,
        "sources_used":    [
            {"filename": s["filename"], "page": s["page"], "score": s["score"]}
            for s in sources
        ],
    }
    _cases[case_id] = updated
    return CaseResponse(**updated)


# ── Eliminar caso ────────────────────────────────────────────
@router.delete("/{case_id}", status_code=204)
def delete_case(case_id: str):
    if case_id not in _cases:
        raise HTTPException(404, "Caso no encontrado")
    del _cases[case_id]


# ── Re-analizar caso con más contexto ────────────────────────
@router.post("/{case_id}/analyze")
def reanalyze_case(case_id: str, request: Request):
    case = _cases.get(case_id)
    if not case:
        raise HTTPException(404, "Caso no encontrado")

    query   = f"{case['chief_complaint']} {' '.join(case['symptoms'])}"
    sources = _vs(request).search(query=query, top_k=10)

    from services.claude_service import analyze_case
    analysis = analyze_case(case_data=case, sources=sources)
    _cases[case_id]["analysis"] = analysis
    _cases[case_id]["sources_used"] = [
        {"filename": s["filename"], "page": s["page"], "score": s["score"]}
        for s in sources
    ]
    return {"case_id": case_id, "analysis": analysis}
