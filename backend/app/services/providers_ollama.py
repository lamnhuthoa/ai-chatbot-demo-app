from __future__ import annotations

import os
import re
from typing import Iterable, Iterator, Optional

import ollama

from app.services.llm_base import LLMStreamingProvider


class OllamaProvider(LLMStreamingProvider):
    """LLM provider backed by a local Ollama server.

    Requires the Ollama daemon running locally (default http://localhost:11434)
    and the model (default: llama3.2) pulled via `ollama pull llama3.2`.
    """

    def __init__(self, host: Optional[str] = None, default_model: Optional[str] = None) -> None:
        self.host = host or os.getenv("OLLAMA_HOST") or "http://localhost:11434"
        self._default_model = default_model or os.getenv("OLLAMA_MODEL") or "llama3.2"
        self._client = ollama.Client(host=self.host)

    def stream_text(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        temperature: float = 0.3,
    ) -> Iterable[str]:
        selected_model = model or self._default_model
        try:
            # Stream incremental generation chunks
            stream = self._client.generate(
                model=selected_model,
                prompt=prompt,
                options={"temperature": temperature},
                stream=True,
            )
            for part in stream:
                text = part.get("response") or ""
                if text:
                    for token in self._word_tokens(text):
                        yield token
        except Exception as exc:
            yield f"[ollama-error] {exc}"

    @staticmethod
    def _word_tokens(text: str) -> Iterator[str]:
        # Tokens: whitespace sequences | non-word non-space | word characters
        token_pattern = re.compile(r"\s+|[^\w\s]+|\w+", re.UNICODE)
        for match in token_pattern.finditer(text):
            tok = match.group(0)
            if tok:
                yield tok
