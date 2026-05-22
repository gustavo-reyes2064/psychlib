from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os, pathlib
from dotenv import load_dotenv

load_dotenv()

from api.documents  import router as docs_router
from api.chat       import router as chat_router
from api.cases      import router as cases_router
from api.flashcards import router as flash_router
from api.tools      import router as tools_router
from services.vector_store import VectorStore

UPLOAD_DIR = pathlib.Path(os.getenv("UPLOAD_DIR", "./data/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.vs = VectorStore()
    yield

app = FastAPI(
    title="PsychLib API",
    description="Biblioteca psiquiátrica con IA — RAG sobre PDFs médicos",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(docs_router,  prefix="/api/documents",  tags=["Documentos"])
app.include_router(chat_router,  prefix="/api/chat",       tags=["Chat IA"])
app.include_router(cases_router, prefix="/api/cases",      tags=["Casos Clínicos"])
app.include_router(flash_router, prefix="/api/flashcards", tags=["Flashcards y Exámenes"])
app.include_router(tools_router, prefix="/api/tools",      tags=["Herramientas Clínicas"])

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "PsychLib API v1.0"}

FRONTEND_DIR = pathlib.Path(__file__).parent.parent / "frontend" / "dist"
if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = FRONTEND_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIR / "index.html")
