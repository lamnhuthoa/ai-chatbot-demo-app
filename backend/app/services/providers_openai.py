from __future__ import annotations

from typing import Iterable, Optional

from app.services.llm_base import LLMStreamingProvider
from app.core.settings import settings

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore


class OpenAIProvider(LLMStreamingProvider):
    """LLM provider backed by OpenAI.

    Uses the official `openai` SDK (3.x). Streams text chunks via the Responses API.
    Requires `OPENAI_API_KEY` to be set in the environment or settings.
    """

    def __init__(self) -> None:
        if OpenAI is None:
            raise RuntimeError("openai package is not installed. Please `pip install openai`.")
        api_key = getattr(settings, "openai_api_key", None)
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not configured. Add to backend/app/.env")
        self._client = OpenAI(api_key=api_key)
        self._default_model = getattr(settings, "openai_model", "gpt-4o-mini")

    def stream_text(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        temperature: float = 0.3,
    ) -> Iterable[str]:
        selected_model = model or self._default_model
        try:
            # Use Chat Completions streaming for broad compatibility
            stream = self._client.chat.completions.create(
                model=selected_model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                stream=True,
            )
            for chunk in stream:
                if not chunk or not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                text = getattr(delta, "content", None)
                if isinstance(text, str) and text:
                    yield text
        except Exception as exc:
            yield f"[openai-error] {exc}"
