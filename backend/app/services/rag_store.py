from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from langchain_community.vectorstores.faiss import FAISS
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.core.settings import settings


@dataclass
class SessionIndex:
    store: Optional[FAISS] = None


class RAGStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, SessionIndex] = {}

    def _embeddings(self) -> Optional[GoogleGenerativeAIEmbeddings]:
        api_key = settings.gemini_api_key
        if not api_key:
            return None
        try:
            return GoogleGenerativeAIEmbeddings(google_api_key=api_key, model="text-embedding-004")
        except Exception:
            return None

    def upsert_text(self, session_id: str, text: str) -> bool:
        """Index text into the session vector store.

        Returns True if indexing happened, False if skipped (e.g., no API key or empty text).
        """
        if not text.strip():
            return False
        embs = self._embeddings()
        if embs is None:
            # No embeddings capability; skip indexing
            return False
        docs = [Document(page_content=chunk) for chunk in self._chunk_text(text)]
        if not docs:
            return False
        if session_id not in self._sessions or self._sessions[session_id].store is None:
            self._sessions[session_id] = SessionIndex(store=FAISS.from_documents(docs, embs))
        else:
            self._sessions[session_id].store.add_documents(docs)
        return True

    def retrieve(self, session_id: str, query: str, k: int = 4) -> List[Tuple[str, float]]:
        index = self._sessions.get(session_id)
        if not index or not index.store or not query.strip():
            return []
        try:
            docs_with_scores = index.store.similarity_search_with_score(query, k=k)
            return [(doc.page_content, float(score)) for doc, score in docs_with_scores]
        except Exception:
            return []

    def clear(self, session_id: str) -> None:
        if session_id in self._sessions:
            del self._sessions[session_id]

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
        chunks: List[str] = []
        start = 0
        length = len(text)
        while start < length:
            end = min(start + chunk_size, length)
            chunks.append(text[start:end])
            if end == length:
                break
            start = max(end - overlap, start + 1)
        return chunks


rag_store = RAGStore()
