import chromadb, os
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
from typing import List, Dict, Any, Optional
import pathlib

CHROMA_DIR = os.getenv("CHROMA_DIR", "./data/chroma")
TOP_K      = int(os.getenv("TOP_K_RESULTS", 5))

pathlib.Path(CHROMA_DIR).mkdir(parents=True, exist_ok=True)


class VectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=CHROMA_DIR)
        self.ef = ONNXMiniLM_L6_V2()
        self.collection = self.client.get_or_create_collection(
            name="psychlib_docs",
            embedding_function=self.ef,
            metadata={"hnsw:space": "cosine"},
        )

    # ── Indexar ─────────────────────────────────────────────
    def add_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        if not chunks:
            return 0
        ids       = [c["id"]       for c in chunks]
        documents = [c["text"]     for c in chunks]
        metadatas = [{"doc_id":   c["doc_id"],
                      "filename": c["filename"],
                      "page":     c["page"],
                      "chunk":    c["chunk"]} for c in chunks]
        # Upsert en lotes de 100
        batch = 100
        for i in range(0, len(ids), batch):
            self.collection.upsert(
                ids=ids[i:i+batch],
                documents=documents[i:i+batch],
                metadatas=metadatas[i:i+batch],
            )
        return len(ids)

    # ── Buscar ──────────────────────────────────────────────
    def search(
        self,
        query: str,
        top_k: int = TOP_K,
        doc_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        where = {"doc_id": {"$in": doc_ids}} if doc_ids else None
        kwargs = dict(query_texts=[query], n_results=min(top_k, self.collection.count() or 1))
        if where:
            kwargs["where"] = where
        results = self.collection.query(**kwargs)
        out = []
        for i, doc in enumerate(results["documents"][0]):
            meta  = results["metadatas"][0][i]
            score = 1 - results["distances"][0][i]   # cosine → similitud
            out.append({
                "text":      doc,
                "doc_id":    meta["doc_id"],
                "filename":  meta["filename"],
                "page":      meta["page"],
                "score":     round(score, 3),
            })
        return out

    # ── Eliminar documento ──────────────────────────────────
    def delete_document(self, doc_id: str):
        ids = self.collection.get(where={"doc_id": doc_id})["ids"]
        if ids:
            self.collection.delete(ids=ids)

    # ── Stats ───────────────────────────────────────────────
    def count(self) -> int:
        return self.collection.count()

    def list_doc_ids(self) -> List[str]:
        if self.collection.count() == 0:
            return []
        all_meta = self.collection.get(include=["metadatas"])["metadatas"]
        return list({m["doc_id"] for m in all_meta})
