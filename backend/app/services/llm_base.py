from __future__ import annotations

from typing import Iterable, Optional, Protocol


class LLMStreamingProvider(Protocol):
    def stream_text(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        temperature: float = 0.3,
    ) -> Iterable[str]:
        """Stream text chunks for the given prompt."""
        ...
