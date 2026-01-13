from __future__ import annotations

from typing import Iterable, Optional

from app.services.gemini_service import GeminiService
from app.services.llm_base import LLMStreamingProvider


class GeminiProvider(LLMStreamingProvider):
    def __init__(self) -> None:
        self._service = GeminiService()

    def stream_text(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        temperature: float = 0.3,
    ) -> Iterable[str]:
        return self._service.stream_text_response(
            prompt=prompt,
            model_name=model,
            temperature=temperature,
        )
