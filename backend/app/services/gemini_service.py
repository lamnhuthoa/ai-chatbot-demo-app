from __future__ import annotations

from typing import Iterable, Optional, Iterator, List
import re

from google import genai
from google.genai import types
import os

from app.core.settings import settings


class GeminiService:
    def __init__(self) -> None:
        # Best practice: pick up GEMINI_API_KEY from environment; allow missing for local/dev fallback
        api_key = os.getenv("GEMINI_API_KEY") or settings.gemini_api_key
        self.client = genai.Client(api_key=api_key) if api_key else None

    def stream_text_response(
        self,
        prompt: str,
        model_name: Optional[str] = None,
        temperature: float = 0.3,
    ) -> Iterable[str]:
        """
        Returns an iterator of text chunks produced by Gemini streaming.
        The google-genai SDK supports generate_content_stream(...). :contentReference[oaicite:3]{index=3}
        """
        # If no client (no API key), provide a simple echo fallback for development
        if self.client is None:
            yield f"[dev-fallback] You said: {prompt}"
            return

        selected_model_name = model_name or settings.gemini_model

        stream = self.client.models.generate_content_stream(
            model=selected_model_name,
            contents=types.Part.from_text(text=prompt),
            config=types.GenerateContentConfig(
                temperature=temperature,
            ),
        )

        for chunk in stream:
            yield from self._extract_text_chunks(chunk)

    def _extract_text_chunks(self, chunk: object) -> Iterator[str]:
        # Prefer direct text if available
        direct_text = getattr(chunk, "text", None)
        if isinstance(direct_text, str) and direct_text:
            # Word-level streaming (includes whitespace/punctuation tokens)
            yield from self._word_tokens(direct_text)
            return

        # Fallback: traverse candidates -> content -> parts to extract text
        try:
            for candidate in getattr(chunk, "candidates", []) or []:
                content = getattr(candidate, "content", None)
                parts: List = getattr(content, "parts", []) if content else []
                for part in parts:
                    part_text = getattr(part, "text", None)
                    if isinstance(part_text, str) and part_text:
                        yield from self._word_tokens(part_text)
        except Exception:
            # Best-effort extraction; ignore non-text structures
            return

    @staticmethod
    def _word_tokens(text: str) -> Iterator[str]:
        """Yield tokens roughly word-by-word, preserving whitespace and punctuation as separate tokens."""
        # Tokens: whitespace sequences | non-word non-space (punct/symbol) | word characters
        token_pattern = re.compile(r"\s+|[^\w\s]+|\w+", re.UNICODE)
        for match in token_pattern.finditer(text):
            token = match.group(0)
            if token:
                yield token
