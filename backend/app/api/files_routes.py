from __future__ import annotations

import io
import csv as _csv
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
            rag_store.clear(session_id)
            indexed = rag_store.upsert_text(session_id, text)
            return {"filename": file.filename, "pages": len(reader.pages), "rag_indexed": indexed}
        elif fname.endswith(".txt"):
            raw = await file.read()
            # Try multiple encodings commonly seen in exported text files
            content: str | None = None
            used = "utf-8"
            for enc in ("utf-8-sig", "utf-8", "utf-16", "latin-1"):
                try:
                    content = raw.decode(enc)
                    used = enc
                    break
                except UnicodeDecodeError:
                    continue
            if content is None:
                content = raw.decode("utf-8", errors="ignore")

            context_store.set_text(session_id, content)
            rag_store.clear(session_id)
            indexed = rag_store.upsert_text(session_id, content)
            return {"filename": file.filename, "encoding": used, "tokens": len(content.split()), "rag_indexed": indexed}
        elif fname.endswith(".csv"):
            # Read bytes and try multiple encodings commonly seen in exported expense CSVs
            raw = await file.read()
            encoding_used = "utf-8"
            content: str | None = None
            for enc in ("utf-8-sig", "utf-8", "utf-16", "latin-1"):
                try:
                    content = raw.decode(enc)
                    encoding_used = enc
                    break
                except UnicodeDecodeError:
                    continue
            if content is None:
                content = raw.decode("utf-8", errors="ignore")

            # Detect delimiter with csv.Sniffer; fallback by simple heuristics
            sample = content[:8192]
            sep = ","
            try:
                dialect = _csv.Sniffer().sniff(sample, delimiters=",;\t|")
                sep = dialect.delimiter  # type: ignore[attr-defined]
            except Exception:
                if sample.count(";") > sample.count(","):
                    sep = ";"
                elif "\t" in sample:
                    sep = "\t"
                elif "|" in sample:
                    sep = "|"
                else:
                    sep = ","

            # Try reading with pandas, then retry with fallbacks (decimal/thousands, alt sep)
            def _read_csv(text: str, **kwargs):
                return pd.read_csv(io.StringIO(text), **kwargs)

            df = None
            try:
                df = _read_csv(content, sep=sep, engine="python")
            except Exception:
                # Retry with common European decimal comma when using semicolon sep
                try:
                    if sep == ";":
                        df = _read_csv(content, sep=sep, engine="python", decimal=",")
                    else:
                        df = _read_csv(content, sep=sep, engine="python")
                except Exception:
                    # Final fallback: toggle sep between comma and semicolon
                    alt_sep = ";" if sep == "," else ","
                    df = _read_csv(content, sep=alt_sep, engine="python")

            # Normalize to CSV text for downstream context / RAG
            csv_text = df.to_csv(index=False)
            context_store.set_text(session_id, csv_text)
            rag_store.clear(session_id)
            indexed = rag_store.upsert_text(session_id, csv_text)
            return {
                "filename": file.filename,
                "columns": list(df.columns),
                "rows": int(len(df)),
                "encoding": encoding_used,
                "sep": sep,
                "rag_indexed": indexed,
            }
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
