from __future__ import annotations

import io
from typing import Dict

import pandas as pd
import PyPDF2
from fastapi import APIRouter, File, HTTPException, UploadFile, Query

from app.services.context_store import context_store
from app.services.rag_store import rag_store

router = APIRouter(prefix="/api/files", tags=["files"])


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    session_id: str = Query("default", description="Session identifier for context scoping"),
) -> Dict[str, object]:
    """Upload a PDF/TXT/CSV and store parsed text in a basic context store."""
    try:
        fname = (file.filename or "").lower()
        if fname.endswith(".pdf"):
            reader = PyPDF2.PdfReader(file.file)
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            context_store.set_text(session_id, text)
            indexed = rag_store.upsert_text(session_id, text)
            return {"filename": file.filename, "pages": len(reader.pages), "rag_indexed": indexed}
        elif fname.endswith(".txt"):
            content = (await file.read()).decode("utf-8", errors="ignore")
            context_store.set_text(session_id, content)
            indexed = rag_store.upsert_text(session_id, content)
            return {"filename": file.filename, "tokens": len(content.split()), "rag_indexed": indexed}
        elif fname.endswith(".csv"):
            content = (await file.read()).decode("utf-8", errors="ignore")
            df = pd.read_csv(io.StringIO(content))
            csv_text = df.to_csv(index=False)
            context_store.set_text(session_id, csv_text)
            indexed = rag_store.upsert_text(session_id, csv_text)
            return {"filename": file.filename, "columns": list(df.columns), "rag_indexed": indexed}
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type. Use PDF/TXT/CSV.")
    finally:
        await file.close()


@router.delete("/clear")
def clear_file_context(session_id: str = Query("default")) -> Dict[str, str]:
    """Clear session-scoped raw context and vector index."""
    context_store.set_text(session_id, "")
    rag_store.clear(session_id)
    return {"status": "cleared", "session_id": session_id}
