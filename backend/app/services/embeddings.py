"""Bailian / DashScope text-embedding-v4 via OpenAI-compatible API."""

from __future__ import annotations

from typing import Sequence

from langchain_core.embeddings import Embeddings
from openai import OpenAI

from app.config import get_settings

DASHSCOPE_MAX_BATCH_SIZE = 10


class BailianEmbeddings(Embeddings):
    """LangChain Embeddings wrapper for DashScope text-embedding-v4."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        dimensions: int | None = None,
        client: OpenAI | None = None,
    ) -> None:
        settings = get_settings()
        self.api_key = (api_key if api_key is not None else settings.dashscope_api_key).strip()
        self.base_url = (
            base_url if base_url is not None else settings.dashscope_embedding_base_url
        ).strip()
        self.model = (model if model is not None else settings.dashscope_embedding_model).strip()
        self.dimensions = (
            dimensions
            if dimensions is not None
            else settings.dashscope_embedding_dimensions
        )
        self._client = client
        self._embed_call_count = 0

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            if not self.api_key:
                raise ValueError("DASHSCOPE_API_KEY is required for embeddings")
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        cleaned = [t.strip() for t in texts]
        if any(not t for t in cleaned):
            raise ValueError("embed_documents rejects empty texts")
        vectors: list[list[float]] = []
        for start in range(0, len(cleaned), DASHSCOPE_MAX_BATCH_SIZE):
            batch = cleaned[start : start + DASHSCOPE_MAX_BATCH_SIZE]
            vectors.extend(self._embed_batch(batch))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        cleaned = text.strip()
        if not cleaned:
            raise ValueError("embed_query rejects empty text")
        return self._embed_batch([cleaned])[0]

    def _embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        self._embed_call_count += 1
        resp = self.client.embeddings.create(
            model=self.model,
            input=list(texts),
            dimensions=self.dimensions,
            encoding_format="float",
        )
        # OpenAI API returns data sorted by index
        ordered = sorted(resp.data, key=lambda item: item.index)
        return [list(item.embedding) for item in ordered]


def get_embeddings() -> BailianEmbeddings:
    return BailianEmbeddings()
