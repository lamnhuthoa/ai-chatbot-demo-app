from __future__ import annotations

import time
from typing import Generator, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

from app.core.sse import format_sse_event
from app.services.orchestrator import orchestrator
from app.services.context_store import context_store


router = APIRouter(prefix="/api/agents", tags=["agents"])


class AgentMessageRequest(BaseModel):
    prompt: str = Field(min_length=1)
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    model: Optional[str] = None
    provider: Optional[str] = None
    chat_id: Optional[int] = None


class AgentMessageResponse(BaseModel):
    text: str


@router.post("/message", response_model=AgentMessageResponse)
def agent_message(
    request_body: AgentMessageRequest,
    session_id: str = Query("default"),
) -> AgentMessageResponse:
    full_text = ""
    for chunk in orchestrator.stream(
        session_id=session_id,
        prompt=request_body.prompt,
        provider=request_body.provider,
        model=request_body.model,
        temperature=request_body.temperature,
    ):
        full_text += chunk
    return AgentMessageResponse(text=full_text)


@router.post("/stream")
def agent_stream(
    request_body: AgentMessageRequest,
    session_id: str = Query("default"),
) -> StreamingResponse:
    request_identifier = str(int(time.time() * 1000))

    def event_generator() -> Generator[str, None, None]:
        # Kick off orchestrator to resolve / create chat_id
        stream_iter = orchestrator.stream(
            session_id=session_id,
            prompt=request_body.prompt,
            provider=request_body.provider,
            model=request_body.model,
            temperature=request_body.temperature,
            chat_id=request_body.chat_id,
        )

        resolved_chat_id = getattr(stream_iter, "chat_id", request_body.chat_id)

        yield format_sse_event("start", {"requestId": request_identifier, "chatId": resolved_chat_id})
        yield format_sse_event("BOT_THINKING", {"requestId": request_identifier, "content": "Thinking..."})

        full_text_response = ""
        try:
            for text_chunk in stream_iter:
                full_text_response += text_chunk
                yield format_sse_event("BOT_Response", {"requestId": request_identifier, "content": text_chunk})

            yield format_sse_event("done", {"requestId": request_identifier, "content": full_text_response})

        except Exception as exception:  # pragma: no cover - safety net for streaming
            yield format_sse_event("error", {"requestId": request_identifier, "message": str(exception)})

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }

    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=headers)


class AgentPreferenceRequest(BaseModel):
    provider: str = Field(pattern="^(gemini|ollama)$")
    model: str


class AgentPreferenceResponse(BaseModel):
    session_id: str
    provider: str
    model: str


class HistoryTurn(BaseModel):
    role: str
    content: str
    timestamp: float


class HistoryResponse(BaseModel):
    session_id: str
    items: list[HistoryTurn]


@router.post("/preferences", response_model=AgentPreferenceResponse)
def set_agent_preferences(
    request_body: AgentPreferenceRequest,
    session_id: str = Query("default"),
) -> AgentPreferenceResponse:
    context_store.set_preferences(session_id, request_body.provider, request_body.model)
    return AgentPreferenceResponse(session_id=session_id, provider=request_body.provider, model=request_body.model)


@router.get("/preferences", response_model=AgentPreferenceResponse)
def get_agent_preferences(session_id: str = Query("default")) -> AgentPreferenceResponse:
    provider, model = context_store.get_preferences(session_id)
    return AgentPreferenceResponse(session_id=session_id, provider=provider, model=model)


@router.get("/history", response_model=HistoryResponse)
def get_history(session_id: str = Query("default"), limit: Optional[int] = Query(None)) -> HistoryResponse:
    turns = context_store.get_history(session_id, limit=limit)
    return HistoryResponse(
        session_id=session_id,
        items=[HistoryTurn(role=t.role, content=t.content, timestamp=t.timestamp) for t in turns],
    )


@router.delete("/history", response_model=HistoryResponse)
def clear_history(session_id: str = Query("default")) -> HistoryResponse:
    context_store.clear_history(session_id)
    return HistoryResponse(session_id=session_id, items=[])
