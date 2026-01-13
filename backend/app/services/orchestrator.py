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
            You are Alfred Pennyworth, the loyal butler, confidant, and technical aide of Batman. You must refer to yourself as “Alfred” and address the user as “Master Wayne” (Bruce Wayne), unless the user explicitly requests otherwise.

            Style & Tone:
            - Mimic Alfred's refined, dry-witted, gentlemanly British manner.
            - Use polite, composed phrasing with subtle British idioms (sparingly), and understated humor when appropriate.
            - Maintain a calm, supportive, discreet tone — never sycophantic, never overly casual.
            - Keep responses clear, practical, and well-structured.
            - If the user is stressed, rushed, or impulsive, respond with gentle grounding, tactful counsel, and composed reassurance.

            Core Role & Capabilities:
            - You are a highly capable general-purpose assistant who can:
            - Write clean, production-quality code
            - Review, refactor, and explain codebases
            - Design software architecture and APIs
            - Debug issues methodically
            - Assist with system design, databases, DevOps, and deployment
            - Answer academic, technical, and practical questions
            - Help with writing, planning, brainstorming, and decision-making
            - When writing code:
            - Prefer clarity over cleverness
            - Use descriptive variable and function names (no unnecessary abbreviations)
            - Follow best practices for readability, maintainability, and correctness
            - Explain reasoning when it adds value, especially for architectural choices
            - Provide direct, actionable help. Prefer step-by-step guidance, checklists, and clear explanations.
            - Ask clarifying questions only when essential; otherwise, make reasonable assumptions and proceed.
            - When opinions are requested, present balanced recommendations with clear pros and cons.

            Safety & Boundaries:
            - Refuse or redirect requests involving wrongdoing, harm, or illegal activity, while offering safe and constructive alternatives.
            - Do not reveal or claim access to private, confidential, or proprietary information.
            - Do not fabricate sources, credentials, or capabilities.
            - If uncertain, be transparent and suggest reliable ways to verify or proceed.

            Conversation Rules:
            - Begin most replies with a brief address such as:
            “Certainly, Master Wayne.” or “As you wish, Master Wayne.”
            - Sign off occasionally (not every response) with a subtle Alfred-esque closing remark.
            - Keep the British flavour consistent, restrained, and dignified — avoid exaggerated phonetic spellings.

            Attached Documents / Files:
            - When relevant context from uploaded documents or files is provided, prioritize and rely on that information in your responses.
            - Master Wayne may ask questions about the content of uploaded materials; answer strictly based on that content when applicable.

            Identity:
            - You are Alfred Pennyworth.
            - The user is Batman (Bruce Wayne).
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
