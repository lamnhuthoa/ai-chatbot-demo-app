from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ChatTurn:
    role: str  # "user" | "assistant"
    content: str
    timestamp: float


@dataclass
class SessionContext:
    text: str = ""
    provider: str = "ollama"
    model: str = "llama3.2"
    history: List[ChatTurn] = field(default_factory=list)


class ContextStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, SessionContext] = {}

    def get(self, session_id: str) -> SessionContext:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionContext()
        return self._sessions[session_id]

    def set_text(self, session_id: str, text: str) -> None:
        self.get(session_id).text = text

    def set_preferences(self, session_id: str, provider: str, model: str) -> None:
        ctx = self.get(session_id)
        ctx.provider = provider
        ctx.model = model

    def get_preferences(self, session_id: str) -> tuple[str, str]:
        ctx = self.get(session_id)
        return ctx.provider, ctx.model

    # Conversation history APIs
    def append_history(self, session_id: str, role: str, content: str, timestamp: Optional[float] = None) -> None:
        import time as _time
        ctx = self.get(session_id)
        ts = timestamp if timestamp is not None else _time.time()
        ctx.history.append(ChatTurn(role=role, content=content, timestamp=ts))
        # Trim to the most recent 50 turns to bound memory
        if len(ctx.history) > 50:
            ctx.history = ctx.history[-50:]

    def get_history(self, session_id: str, limit: Optional[int] = None) -> List[ChatTurn]:
        ctx = self.get(session_id)
        if limit is None or limit >= len(ctx.history):
            return list(ctx.history)
        return ctx.history[-limit:]

    def clear_history(self, session_id: str) -> None:
        self.get(session_id).history.clear()


context_store = ContextStore()
