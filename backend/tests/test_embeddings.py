from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from app.services.embeddings import BailianEmbeddings, DASHSCOPE_MAX_BATCH_SIZE


class _FakeEmbeddingsAPI:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def create(self, *, model: str, input: list[str], dimensions: int, encoding_format: str):
        assert model
        assert dimensions == 1024
        assert encoding_format == "float"
        self.calls.append(list(input))
        data = [
            SimpleNamespace(index=i, embedding=[float(i), 0.1, 0.2])
            for i in range(len(input))
        ]
        return SimpleNamespace(data=data)


class _FakeOpenAI:
    def __init__(self) -> None:
        self.embeddings = _FakeEmbeddingsAPI()


def test_embed_documents_rejects_empty() -> None:
    emb = BailianEmbeddings(api_key="sk-test", client=_FakeOpenAI())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="empty"):
        emb.embed_documents(["ok", "  "])


def test_embed_query_rejects_empty() -> None:
    emb = BailianEmbeddings(api_key="sk-test", client=_FakeOpenAI())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="empty"):
        emb.embed_query("   ")


def test_embed_documents_batches_by_ten() -> None:
    fake = _FakeOpenAI()
    emb = BailianEmbeddings(api_key="sk-test", client=fake)  # type: ignore[arg-type]
    texts = [f"chunk-{i}" for i in range(DASHSCOPE_MAX_BATCH_SIZE + 3)]
    vectors = emb.embed_documents(texts)
    assert len(vectors) == len(texts)
    assert emb._embed_call_count == 2
    assert len(fake.embeddings.calls[0]) == DASHSCOPE_MAX_BATCH_SIZE
    assert len(fake.embeddings.calls[1]) == 3
