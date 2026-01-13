from __future__ import annotations

from typing import Iterable, Optional

from app.core.settings import settings
from app.services.llm_base import LLMStreamingProvider


class LangchainGeminiProvider(LLMStreamingProvider):
    """Stream with Google Gemini via LangChain."""

    def stream_text(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        temperature: float = 0.3,
    ) -> Iterable[str]:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except Exception as exc:  # pragma: no cover - import guard
            raise RuntimeError("LangChain Google Generative AI not available") from exc

        api_key = settings.gemini_api_key
        if not api_key:
            raise RuntimeError("Gemini API key is not configured")

        llm = ChatGoogleGenerativeAI(
            model=model or settings.gemini_model,
            google_api_key=api_key,
            temperature=temperature,
        )

        for chunk in llm.stream(prompt):
            # chunk is an AIMessageChunk; its .content is the delta string
            text = getattr(chunk, "content", None)
            if isinstance(text, str) and text:
                yield text


class LangchainOllamaProvider(LLMStreamingProvider):
    """Stream with Ollama via LangChain (requires local Ollama)."""

    def stream_text(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        temperature: float = 0.3,
    ) -> Iterable[str]:
        try:
            from langchain_community.chat_models import ChatOllama
        except Exception as exc:  # pragma: no cover - import guard
            raise RuntimeError("LangChain ChatOllama not available") from exc

        llm = ChatOllama(model=model or "llama3.2", temperature=temperature)
        for chunk in llm.stream(prompt):
            text = getattr(chunk, "content", None)
            if isinstance(text, str) and text:
                yield text
