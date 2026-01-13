from __future__ import annotations

from typing import Dict, Iterable, Optional

from app.services.context_store import context_store
from app.services.rag_store import rag_store
from app.services.llm_base import LLMStreamingProvider
from app.services.providers_langchain import LangchainGeminiProvider, LangchainOllamaProvider
from app.services.providers_ollama import OllamaProvider
from app.services.providers_gemini import GeminiProvider
from app.core.db import SessionLocal
from app.models import Chat, Message


DEFAULT_CHAT_TITLE = "New chat"


class Orchestrator:
    def __init__(self) -> None:
        # Provider registry; can expand to ollama, hf, etc.
        self._providers: Dict[str, LLMStreamingProvider] = {
            "gemini": GeminiProvider(),
            "ollama": OllamaProvider(),
        }
        self._default_provider = "gemini"

    def _generate_title(self, user_prompt: str) -> str:
        """Generate a short, human-readable title from the first user prompt.

        Strategy: take the first sentence or first ~8-10 words, strip whitespace,
        and cap length to 80 chars. Fallback to 'New chat' if empty.
        """
        text = (user_prompt or "").strip().replace("\n", " ")
        if not text:
            return DEFAULT_CHAT_TITLE
        # Split on sentence enders first
        for sep in [". ", "? ", "! "]:
            if sep in text:
                text = text.split(sep, 1)[0]
                break
        # If still long, truncate by words
        words = text.split()
        if len(words) > 10:
            text = " ".join(words[:10])
        # Cap to 80 chars
        if len(text) > 80:
            text = text[:80].rstrip()
        # Add ellipsis if original was longer
        if len(words) > 10 or any(sym in (user_prompt or "") for sym in [". ", "? ", "! "]):
            if not text.endswith("...") and not text.endswith("..."):
                text = text + "..."
        return text or DEFAULT_CHAT_TITLE

    def _build_prompt(self, session_id: str, user_prompt: str, chat_id: Optional[int] = None) -> str:
        base_ctx = context_store.get(session_id).text
        # Pull the last N conversation turns to provide context (prefer DB chat when available)
        history_block = ""
        if chat_id is not None:
            with SessionLocal() as db:
                msgs = (
                    db.query(Message)
                    .filter(Message.chat_id == chat_id)
                    .order_by(Message.created_at.asc(), Message.id.asc())
                    .all()
                )
                history_block = "\n".join([f"{m.role.capitalize()}: {m.content}" for m in msgs[-10:]]) if msgs else ""
        else:
            turns = context_store.get_history(session_id, limit=10)
            history_block = "\n".join([f"{t.role.capitalize()}: {t.content}" for t in turns]) if turns else ""
        rag_hits = rag_store.retrieve(session_id, user_prompt, k=4)
        rag_block = "\n\n".join([f"[Doc {i+1} | score={score:.3f}]\n{content}" for i, (content, score) in enumerate(rag_hits)])

        context_sections = []
        if base_ctx:
            context_sections.append(f"Uploaded context (raw):\n{base_ctx}")
        if rag_block:
            context_sections.append(f"Top relevant snippets from uploaded files:\n{rag_block}")

        if history_block:
            context_sections.append(f"Recent conversation:\n{history_block}")

        if context_sections:
            joined = "\n\n".join(context_sections)
            return (
                "You are a helpful assistant. When answering, rely primarily on the provided context. "
                "If the answer cannot be found in the context, say you don't know.\n\n"
                f"Context:\n{joined}\n\nUser: {user_prompt}\nAssistant:"
            )
        return user_prompt

    def stream(
        self,
        *,
        session_id: str,
        prompt: str,
        chat_id: Optional[int] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.3,
    ) -> Iterable[str]:
        """Stream response from the selected provider."""
        # Merge session preferences if not explicitly provided
        session_provider, session_model = context_store.get_preferences(session_id)
        provider_key = provider or session_provider or self._default_provider
        model_name = model or session_model
        # Fallback to default if unknown provider key appears
        if provider_key not in self._providers:
            provider_key = self._default_provider
        llm = self._providers[provider_key]
        # Prepend a system prompt
        system_prompt = """
            You are a helpful, neutral AI assistant.

            Your role is to answer questions, analyze information, write and review code, and assist with technical, academic, and practical tasks.

            When documents, attachments, or retrieved context are provided:
            - Treat them as the primary source of truth
            - Base your answers strictly on that content
            - Do not add or assume information that is not present
            - If the context is insufficient, clearly state so

            Read and analyze all user-provided attachments carefully and respond accurately.

            Be clear, concise, and professional. Use structured responses when helpful.

            When writing code, prioritize clarity, correctness, and best practices.

            Do not fabricate information or claim access to private data.
        """
        # Ensure chat exists if chat_id is provided as None
        db_chat_id: Optional[int] = chat_id
        if db_chat_id is None:
            with SessionLocal() as db:
                chat = Chat(session_id=session_id, title=DEFAULT_CHAT_TITLE)
                db.add(chat)
                db.commit()
                db.refresh(chat)
                db_chat_id = chat.id

        # If this is the first message in the chat, set a dynamic title from user prompt
        with SessionLocal() as db:
            msg_count = db.query(Message).filter(Message.chat_id == db_chat_id).count()
            if msg_count == 0:
                chat_row = db.get(Chat, db_chat_id)
                if chat_row is not None:
                    chat_row.title = self._generate_title(prompt)
                    db.add(chat_row)
                    db.commit()

        composed = f"{system_prompt}\n\n{self._build_prompt(session_id, prompt, chat_id=db_chat_id)}"

        # Append the user's prompt to history immediately (both in-memory and DB)
        context_store.append_history(session_id, role="user", content=prompt)
        with SessionLocal() as db:
            db.add(Message(chat_id=db_chat_id, role="user", content=prompt))
            db.commit()

        # Stream the assistant response; buffer to append to history at the end and persist
        def iterator():
            assistant_full: list[str] = []
            for piece in llm.stream_text(composed, model=model_name, temperature=temperature):
                assistant_full.append(piece)
                yield piece
            full = "".join(assistant_full)
            context_store.append_history(session_id, role="assistant", content=full)
            with SessionLocal() as db:
                db.add(Message(chat_id=db_chat_id, role="assistant", content=full))
                db.commit()

        # Return an iterator but attach the resolved chat_id as an attribute for the caller to read if needed
        iterator.chat_id = db_chat_id
        return iterator()


orchestrator = Orchestrator()
