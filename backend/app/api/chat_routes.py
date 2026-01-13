from __future__ import annotations

import time
from typing import Generator, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

from app.core.sse import format_sse_event
from app.services.gemini_service import GeminiService


router = APIRouter(prefix="/api/chat", tags=["chat"])
gemini_service = GeminiService()


class ChatStreamRequest(BaseModel):
    prompt: str = Field(min_length=1)
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    model: Optional[str] = None


@router.post("/stream")
def stream_chat_response(request_body: ChatStreamRequest) -> StreamingResponse:
    """
    Returns SSE:
      event: delta  -> partial text
      event: done   -> final marker

    This endpoint is POST so you can use `sse.js` on the frontend (it supports POST).
    """
    request_identifier = str(int(time.time() * 1000))

    def event_generator() -> Generator[str, None, None]:
        # Let the client know the stream started
        yield format_sse_event(
            event_name="start",
            data={"requestId": request_identifier},
        )

        full_text_response = ""

        try:
            for text_chunk in gemini_service.stream_text_response(
                prompt=request_body.prompt,
                model_name=request_body.model,
                temperature=request_body.temperature,
            ):
                full_text_response += text_chunk
                yield format_sse_event(
                    event_name="content",
                    data={"requestId": request_identifier, "content": text_chunk},
                )

            yield format_sse_event(
                event_name="done",
                data={"requestId": request_identifier, "content": full_text_response},
            )

        except Exception as exception:
            yield format_sse_event(
                event_name="error",
                data={
                    "requestId": request_identifier,
                    "message": str(exception),
                },
            )

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        # Helps when behind Nginx / proxies that buffer streaming
        "X-Accel-Buffering": "no",
    }

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=headers,
    )


class ChatMessageRequest(BaseModel):
    prompt: str = Field(min_length=1)
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    model: Optional[str] = None


class ChatMessageResponse(BaseModel):
    text: str


@router.post("/message", response_model=ChatMessageResponse)
def chat_message(request_body: ChatMessageRequest) -> ChatMessageResponse:
    """Non-streaming chat endpoint that returns the final text response."""
    full_text = ""
    for chunk in gemini_service.stream_text_response(
        prompt=request_body.prompt,
        model_name=request_body.model,
        temperature=request_body.temperature,
    ):
        full_text += chunk

    return ChatMessageResponse(text=full_text)
